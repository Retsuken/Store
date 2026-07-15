# ==================== ИМПОРТЫ ====================
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect
from django.views import View
import requests

from core.apps.users.models import User
from core.apps.users.permissions import IsOwnerOrAdmin
from core.apps.users.utils import generate_verification_token, verify_token, create_device, get_client_ip
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer,
    ResetPasswordSerializer, EmailVerificationSerializer,
    UpdateProfileSerializer, LogoutSerializer
)


# ==================== API ВЬЮХИ (JSON) ====================

class RegisterAPIView(APIView):
    """User registration API view"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        # Send verification email
        token = generate_verification_token(user)
        verification_url = f"{settings.FRONTEND_URL}/verify-email/?token={token}"
        
        context = {
            'user': user,
            'verification_url': verification_url,
            'expiry_hours': 24
        }
        
        html_message = render_to_string('emails/verify_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Verify Your Email Address',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Create device record
        device = create_device(user, request)
        
        # Сохраняем токены в сессии для редиректа
        request.session['access_token'] = str(refresh.access_token)
        request.session['refresh_token'] = str(refresh)
        
        return Response({
            'message': 'Registration successful. Please verify your email.',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'redirect_url': '/'
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    """User login API view"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        user.last_login_ip = get_client_ip(request)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login_ip', 'last_login'])
        
        device = create_device(user, request)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'device': {
                'id': device.device_id,
                'name': device.device_name,
                'type': device.device_type
            }
        })


class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh API view"""
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response({
            'access': serializer.validated_data['access'],
            'refresh': serializer.validated_data.get('refresh')
        })


class LogoutAPIView(APIView):
    """User logout API view"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        refresh_token = serializer.validated_data.get('refresh')
        all_devices = serializer.validated_data.get('all_devices', False)
        
        try:
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            if all_devices:
                tokens = OutstandingToken.objects.filter(user=request.user)
                for token in tokens:
                    BlacklistedToken.objects.get_or_create(token=token)
                
                request.user.devices.update(is_active=False)
                
                return Response({
                    'message': 'Logged out from all devices successfully'
                })
            
            return Response({'message': 'Logged out successfully'})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileAPIView(APIView):
    """User profile API view"""
    
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    def patch(self, request):
        user = request.user
        serializer = UpdateProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        user_serializer = UserSerializer(user)
        return Response({
            'message': 'Profile updated successfully',
            'user': user_serializer.data
        })


class ChangePasswordAPIView(APIView):
    """Change password API view"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Wrong password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        
        return Response({'message': 'Password changed successfully'})


class ForgotPasswordAPIView(APIView):
    """Forgot password API view - sends reset link"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            token = generate_verification_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password/?token={token}"
            
            context = {
                'user': user,
                'reset_url': reset_url,
                'expiry_hours': 24
            }
            
            html_message = render_to_string('emails/reset_password.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject='Reset Your Password',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            return Response({
                'message': 'Password reset link sent to your email'
            })
            
        except User.DoesNotExist:
            return Response({
                'message': 'If an account exists with this email, a reset link has been sent.'
            })


class ResetPasswordAPIView(APIView):
    """Reset password API view"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        user_id = verify_token(token)
        if not user_id:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            
            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)
            
            return Response({'message': 'Password reset successfully'})
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class VerifyEmailAPIView(APIView):
    """Email verification API view"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        user_id = verify_token(token)
        if not user_id:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
            
            return Response({
                'message': 'Email verified successfully'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ResendVerificationEmailAPIView(APIView):
    """Resend verification email API view"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.is_email_verified:
            return Response(
                {'error': 'Email already verified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        last_verification = getattr(user, 'last_verification_sent', None)
        if last_verification and (timezone.now() - last_verification) < timedelta(minutes=5):
            return Response(
                {'error': 'Please wait 5 minutes before requesting another verification email'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        token = generate_verification_token(user)
        verification_url = f"{settings.FRONTEND_URL}/verify-email/?token={token}"
        
        context = {
            'user': user,
            'verification_url': verification_url,
            'expiry_hours': 24
        }
        
        html_message = render_to_string('emails/verify_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Verify Your Email Address',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        user.last_verification_sent = timezone.now()
        user.save(update_fields=['last_verification_sent'])
        
        return Response({
            'message': 'Verification email sent successfully'
        })


class DeleteAccountAPIView(APIView):
    """Delete user account API view"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request):
        user = request.user
        
        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
        
        user.delete()
        
        return Response({
            'message': 'Account deleted successfully'
        })


# ==================== ВЬЮХИ ДЛЯ РЕНДЕРА СТРАНИЦ (HTML) ====================

class LoginPageView(View):
    """Login page view"""
    
    def get(self, request):
        if request.session.get('access_token'):
            return redirect('home')
        return render(request, 'users/login.html', {
            'api_base_url': settings.API_BASE_URL
        })
    
    def post(self, request):
        """Handle login form submission"""
        # Получаем данные из формы
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember', False)
        
        # Валидация
        if not email or not password:
            return render(request, 'users/login.html', {
                'error': 'Пожалуйста, заполните все поля',
                'api_base_url': settings.API_BASE_URL,
                'form_data': {'email': email}
            })
        
        try:
            # Отправляем запрос к API
            response = requests.post(
                f"{settings.API_BASE_URL}/api/v1/auth/login/",
                json={'email': email, 'password': password},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Сохраняем токены
                if result.get('tokens'):
                    access_token = result['tokens']['access']
                    refresh_token = result['tokens']['refresh']
                    
                    # Сохраняем в сессии
                    request.session['access_token'] = access_token
                    request.session['refresh_token'] = refresh_token
                    
                    # Если "Запомнить меня" - сохраняем в cookies
                    if remember:
                        request.session.set_expiry(604800)  # 7 дней
                    else:
                        request.session.set_expiry(1800)  # 30 минут
                
                # Сохраняем данные пользователя
                if result.get('user'):
                    request.session['user_data'] = result['user']
                
                # Редирект на профиль
                return redirect('home')
            else:
                error_data = response.json()
                error_message = error_data.get('error') or 'Неверный email или пароль'
                
                return render(request, 'users/login.html', {
                    'error': error_message,
                    'api_base_url': settings.API_BASE_URL,
                    'form_data': {'email': email}
                })
                
        except requests.exceptions.Timeout:
            return render(request, 'users/login.html', {
                'error': 'Превышено время ожидания ответа от сервера',
                'api_base_url': settings.API_BASE_URL,
                'form_data': {'email': email}
            })
        except requests.exceptions.ConnectionError:
            return render(request, 'users/login.html', {
                'error': 'Не удалось подключиться к серверу',
                'api_base_url': settings.API_BASE_URL,
                'form_data': {'email': email}
            })
        except Exception as e:
            print(f"Login error: {e}")
            return render(request, 'users/login.html', {
                'error': 'Произошла ошибка при входе. Попробуйте позже.',
                'api_base_url': settings.API_BASE_URL,
                'form_data': {'email': email}
            })


class RegisterPageView(View):
    """Registration page view"""
    
    def get(self, request):
        if request.session.get('access_token'):
            return redirect('home')
        return render(request, 'users/register.html', {
            'api_base_url': settings.API_BASE_URL
        })
    
    def post(self, request):
        """Handle registration form submission"""
        # Получаем данные из формы
        data = {
            'email': request.POST.get('email'),
            'username': request.POST.get('username'),
            'password': request.POST.get('password'),
            'password2': request.POST.get('password2'),
            'first_name': request.POST.get('first_name', ''),
            'last_name': request.POST.get('last_name', ''),
            'phone_number': request.POST.get('phone_number', ''),
            'user_type': request.POST.get('user_type', 'customer'),
            'date_of_birth': request.POST.get('date_of_birth', None)
        }
        
        # Валидация
        if not data['email'] or not data['username'] or not data['password'] or not data['password2']:
            return render(request, 'users/register.html', {
                'error': 'Пожалуйста, заполните все обязательные поля',
                'api_base_url': settings.API_BASE_URL,
                'form_data': data
            })
        
        if data['password'] != data['password2']:
            return render(request, 'users/register.html', {
                'error': 'Пароли не совпадают',
                'api_base_url': settings.API_BASE_URL,
                'form_data': data
            })
        
        if len(data['password']) < 8:
            return render(request, 'users/register.html', {
                'error': 'Пароль должен содержать минимум 8 символов',
                'api_base_url': settings.API_BASE_URL,
                'form_data': data
            })
        
        try:
            # Отправляем запрос к API
            response = requests.post(
                f"{settings.API_BASE_URL}/api/v1/auth/register/",
                json=data,
                timeout=10
            )
            
            if response.status_code == 201:
                result = response.json()
                # Сохраняем токены в сессии
                if result.get('tokens'):
                    request.session['access_token'] = result['tokens']['access']
                    request.session['refresh_token'] = result['tokens']['refresh']
                
                # Редирект на главную
                return redirect('home')
            else:
                error_data = response.json()
                error_message = error_data.get('error') or error_data.get('detail') or 'Ошибка регистрации'
                
                # Если есть конкретные ошибки полей
                if 'email' in error_data:
                    error_message = f"Email: {error_data['email'][0]}"
                elif 'password' in error_data:
                    error_message = f"Пароль: {error_data['password'][0]}"
                elif 'username' in error_data:
                    error_message = f"Имя пользователя: {error_data['username'][0]}"
                
                return render(request, 'users/register.html', {
                    'error': error_message,
                    'api_base_url': settings.API_BASE_URL,
                    'form_data': data
                })
        except requests.exceptions.Timeout:
            return render(request, 'users/register.html', {
                'error': 'Превышено время ожидания ответа от сервера',
                'api_base_url': settings.API_BASE_URL,
                'form_data': data
            })
        except requests.exceptions.ConnectionError:
            return render(request, 'users/register.html', {
                'error': 'Не удалось подключиться к серверу',
                'api_base_url': settings.API_BASE_URL,
                'form_data': data
            })
        except Exception as e:
            print(f"Registration error: {e}")
            return render(request, 'users/register.html', {
                'error': 'Произошла ошибка при регистрации. Попробуйте позже.',
                'api_base_url': settings.API_BASE_URL,
                'form_data': data
            })

class ProfilePageView(View):
    """User profile page view"""
    
    def get(self, request):
        access_token = request.session.get('access_token')
        if not access_token:
            return redirect('login_page')
        
        try:
            response = requests.get(
                f"{settings.API_BASE_URL}/api/v1/profile/",
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if response.status_code == 200:
                user_data = response.json()
                return render(request, 'users/profile.html', {
                    'user': user_data,
                    'api_base_url': settings.API_BASE_URL
                })
            else:
                return redirect('login_page')
        except requests.RequestException:
            return redirect('login_page')


class VerifyEmailPageView(View):
    """Email verification page view"""
    
    def get(self, request):
        token = request.GET.get('token')
        if not token:
            return render(request, 'users/verify_email.html', {
                'error': 'No verification token provided'
            })
        
        try:
            response = requests.post(
                f"{settings.API_BASE_URL}/api/v1/auth/verify-email/",
                json={'token': token}
            )
            
            if response.status_code == 200:
                return render(request, 'users/verify_email.html', {'success': True})
            else:
                error_data = response.json()
                return render(request, 'users/verify_email.html', {
                    'error': error_data.get('error', 'Verification failed')
                })
        except requests.RequestException:
            return render(request, 'users/verify_email.html', {
                'error': 'Unable to connect to server'
            })


class PasswordResetPageView(View):
    """Password reset page view"""
    
    def get(self, request):
        token = request.GET.get('token')
        return render(request, 'users/password_reset.html', {
            'token': token,
            'api_base_url': settings.API_BASE_URL
        })


class LogoutPageView(View):
    """Logout page view - clears session and blacklists token"""
    
    def get(self, request):
        access_token = request.session.get('access_token')
        refresh_token = request.session.get('refresh_token')
        
        if access_token and refresh_token:
            try:
                requests.post(
                    f"{settings.API_BASE_URL}/api/v1/auth/logout/",
                    headers={'Authorization': f'Bearer {access_token}'},
                    json={'refresh': refresh_token}
                )
            except:
                pass
        
        request.session.flush()
        return redirect('login_page')