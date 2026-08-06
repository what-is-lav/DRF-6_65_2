import random
import string
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import ConfirmationCode
from .serializers import (
    AuthValidateSerializer,
    ConfirmationSerializer,
    CustomTokenObtainPairSerializer,
    RegisterValidateSerializer,
)

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
                # Пытаемся создать пользователя только с email и password (для кастомных моделей)
                user = User.objects.create_user(
                    email=email,
                    password=password
                )
            except TypeError:
                # Если модель требует обязательное поле username (например, стандартная модель),
                # то дублируем email в поле username
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )

            # Добавляем кастомные поля и сохраняем изменения
            user.birthdate = birthdate
            user.is_active = False
            user.save()

            code = ''.join(random.choices(string.digits, k=6))

            ConfirmationCode.objects.create(
                user=user,
                code=code
            )

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

        with transaction.atomic():
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            refresh = CustomTokenObtainPairSerializer.get_token(user)
            ConfirmationCode.objects.filter(user=user).delete()

        return Response(
            status=status.HTTP_200_OK,
            data={
                'message': 'User аккаунт успешно активирован',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        )