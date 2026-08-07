from django.urls import path
from .views import (AuthorizationAPIView,RegistrationAPIView,ConfirmUserAPIView, 
                    GoogleLoginRedirectAPIView,GoogleCallbackAPIView,)

urlpatterns = [
    path('authorization/', AuthorizationAPIView.as_view(), name='authorization'),
    path('registration/', RegistrationAPIView.as_view(), name='registration'),
    path('confirm/', ConfirmUserAPIView.as_view(), name='confirm'),
    path('google/login/', GoogleLoginRedirectAPIView.as_view(), name='google_login'),
    path('google/callback/', GoogleCallbackAPIView.as_view(), name='google_callback'),
]