from django.urls import path
from .v1.users.views import (
    # API Views (JSON)
    RegisterAPIView,
    LoginAPIView,
    CustomTokenRefreshView,
    LogoutAPIView,
    ProfileAPIView,
    ChangePasswordAPIView,
    ForgotPasswordAPIView,
    ResetPasswordAPIView,
    VerifyEmailAPIView,
    ResendVerificationEmailAPIView,
    DeleteAccountAPIView,
    
)

app_name = 'api_v1'

urlpatterns = [
    # ==================== API ENDPOINTS (JSON) ====================
    
    # Authentication
    path('api/v1/auth/register/', RegisterAPIView.as_view(), name='api_register'),
    path('api/v1/auth/login/', LoginAPIView.as_view(), name='api_login'),
    path('api/v1/auth/refresh/', CustomTokenRefreshView.as_view(), name='api_token_refresh'),
    path('api/v1/auth/logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('api/v1/auth/verify-email/', VerifyEmailAPIView.as_view(), name='api_verify_email'),
    path('api/v1/auth/resend-verification/', ResendVerificationEmailAPIView.as_view(), name='api_resend_verification'),
    
    # Password management
    path('api/v1/auth/forgot-password/', ForgotPasswordAPIView.as_view(), name='api_forgot_password'),
    path('api/v1/auth/reset-password/', ResetPasswordAPIView.as_view(), name='api_reset_password'),
    path('api/v1/auth/change-password/', ChangePasswordAPIView.as_view(), name='api_change_password'),
    
    # User profile
    path('api/v1/profile/', ProfileAPIView.as_view(), name='api_profile'),
    path('api/v1/profile/delete/', DeleteAccountAPIView.as_view(), name='api_delete_account'),
    
    # ==================== PAGE ENDPOINTS (HTML) ====================
    
]