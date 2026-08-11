import random
import string
import requests
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    AuthValidateSerializer,
    ConfirmationSerializer,
    CustomTokenObtainPairSerializer,
    RegisterValidateSerializer,
)
from .tasks import send_welcome_email_task  # Импортируем нашу Celery-задачу

User = get_user_model()


class AuthorizationAPIView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = AuthValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(**serializer.validated_data)

        if user:
            if not user.is_active:
                return Response(
                    status=status.HTTP_401_UNAUTHORIZED,
                    data={'error': 'User account is not activated yet!'}
                )
            
            refresh = CustomTokenObtainPairSerializer.get_token(user)
            return Response(data={
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })

        return Response(
            status=status.HTTP_401_UNAUTHORIZED,
            data={'error': 'User credentials are wrong!'}
        )


class RegistrationAPIView(CreateAPIView):
    serializer_class = RegisterValidateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        birthdate = serializer.validated_data.get('birthdate')

        with transaction.atomic():
            try:
                user = User.objects.create_user(
                    email=email,
                    password=password
                )
            except TypeError:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )

            user.birthdate = birthdate
            user.is_active = False
            user.save()

        code = ''.join(random.choices(string.digits, k=6))
        cache.set(f"confirm_code:{user.id}", code, timeout=300)

        # Вызов Celery-задачи через .delay() для отправки письма с кодом/приветствием
        send_welcome_email_task.delay(user_email=user.email, username=email)

        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'user_id': user.id,
                'confirmation_code': code
            }
        )


class ConfirmUserAPIView(CreateAPIView):
    serializer_class = ConfirmationSerializer

    def post(self, request, *args, **kwargs):
        serializer = ConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        input_code = serializer.validated_data.get('code')
        key = f"confirm_code:{user_id}"
        saved_code = cache.get(key)

        if saved_code is None:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'error': 'Срок действия кода истек или код не найден.'}
            )

        if saved_code != str(input_code):
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'error': 'Неверный код подтверждения.'}
            )

        with transaction.atomic():
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            refresh = CustomTokenObtainPairSerializer.get_token(user)
        
        cache.delete(key)

        return Response(
            status=status.HTTP_200_OK,
            data={
                'message': 'User аккаунт успешно активирован',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        )


class GoogleLoginRedirectAPIView(APIView):
    def get(self, request):
        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
            "response_type=code&"
            "scope=openid%20email%20profile"
        )
        return redirect(google_auth_url)


class GoogleCallbackAPIView(APIView):
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({'error': 'Code not provided'}, status=status.HTTP_400_BAD_REQUEST)

        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }

        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            return Response({'error': 'Failed to obtain access token from Google'}, status=token_response.status_code)

        google_access_token = token_response.json().get('access_token')

        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        user_info_response = requests.get(
            user_info_url,
            headers={'Authorization': f'Bearer {google_access_token}'}
        )

        if user_info_response.status_code != 200:
            return Response({'error': 'Failed to obtain user info from Google'}, status=user_info_response.status_code)

        user_data = user_info_response.json()

        email = user_data.get('email')
        given_name = user_data.get('given_name')
        family_name = user_data.get('family_name')

        if not email:
            return Response({'error': 'Email not provided by Google'}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': given_name,
                'last_name': family_name,
                'registration_source': 'google',
                'is_active': True,
            }
        )

        if not created:
            if given_name and not user.first_name:
                user.first_name = given_name
            if family_name and not user.last_name:
                user.last_name = family_name

        user.is_active = True
        user.last_login = timezone.now()
        user.save()

        refresh = CustomTokenObtainPairSerializer.get_token(user)

        return Response({
            'message': 'Google authentication successful',
            'user_id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'registration_source': user.registration_source,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_200_OK)