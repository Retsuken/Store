from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from core.apps.users.models import User, UserProfile
import re


class UserSerializer(serializers.ModelSerializer):
    """Base User serializer"""
    
    full_name = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 
            'full_name', 'user_type', 'avatar', 'phone_number',
            'is_email_verified', 'is_phone_verified', 'date_of_birth',
            'bio', 'telegram', 'instagram', 'facebook', 'profile',
            'date_joined', 'last_activity', 'created_at'
        )
        read_only_fields = ('id', 'is_email_verified', 'is_phone_verified', 
                           'date_joined', 'last_activity', 'created_at')
    
    def get_full_name(self, obj):
        return obj.full_name
    
    def get_profile(self, obj):
        try:
            return UserProfileSerializer(obj.profile).data
        except UserProfile.DoesNotExist:
            return None


class UserProfileSerializer(serializers.ModelSerializer):
    """User Profile serializer"""
    
    class Meta:
        model = UserProfile
        fields = (
            'newsletter_subscribed', 'preferred_language', 
            'preferred_currency', 'shipping_address', 
            'billing_address', 'receive_promotions', 
            'receive_order_updates'
        )


class RegisterSerializer(serializers.ModelSerializer):
    """Registration serializer"""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label=_('Confirm Password')
    )
    email = serializers.EmailField(
        required=True,
        validators=[EmailValidator()]
    )
    
    class Meta:
        model = User
        fields = (
            'email', 'username', 'password', 'password2',
            'first_name', 'last_name', 'phone_number',
            'user_type', 'date_of_birth'
        )
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone_number': {'required': False},
            'user_type': {'required': False},
            'date_of_birth': {'required': False}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password': _("Password fields didn't match.")
            })
        
        if 'phone_number' in attrs and attrs['phone_number']:
            phone = attrs['phone_number']
            if not re.match(r'^\+?1?\d{9,15}$', phone):
                raise serializers.ValidationError({
                    'phone_number': _('Enter a valid phone number.')
                })
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data.get('username', validated_data['email'].split('@')[0]),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            user_type=validated_data.get('user_type', 'customer'),
            date_of_birth=validated_data.get('date_of_birth', None)
        )
        
        UserProfile.objects.create(user=user)
        
        return user


class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        write_only=True
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        user = authenticate(request=self.context.get('request'), 
                           username=email, password=password)
        
        if not user:
            try:
                user_obj = User.objects.get(username=email)
                user = authenticate(request=self.context.get('request'),
                                   username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if not user:
            raise serializers.ValidationError({
                'error': _('Invalid email or password.')
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'error': _('User account is disabled.')
            })
        
        attrs['user'] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    """Logout serializer"""
    
    refresh = serializers.CharField(required=False)
    all_devices = serializers.BooleanField(required=False, default=False)


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""
    
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        write_only=True
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        write_only=True
    )
    new_password2 = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        write_only=True
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                'new_password2': _("Password fields didn't match.")
            })
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Forgot password serializer"""
    
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Reset password serializer"""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        write_only=True
    )
    new_password2 = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        write_only=True
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                'new_password2': _("Password fields didn't match.")
            })
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Email verification serializer"""
    
    token = serializers.CharField(required=True)


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Update profile serializer"""
    
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'phone_number',
            'avatar', 'date_of_birth', 'bio',
            'telegram', 'instagram', 'facebook', 'profile'
        )
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance