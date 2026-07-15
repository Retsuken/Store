from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import uuid


class User(AbstractUser):
    """Custom User model with additional fields"""
    
    USER_TYPES = (
        ('customer', 'Customer'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Social links
    telegram = models.URLField(max_length=200, blank=True)
    instagram = models.URLField(max_length=200, blank=True)
    facebook = models.URLField(max_length=200, blank=True)
    
    # Timestamps
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_verification_sent = models.DateTimeField(blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['is_email_verified']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.get_user_type_display()}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def is_seller(self):
        return self.user_type in ['seller', 'admin']
    
    @property
    def is_admin(self):
        return self.user_type == 'admin'


class UserProfile(models.Model):
    """Extended user profile for additional data"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    newsletter_subscribed = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=10, default='ru')
    preferred_currency = models.CharField(max_length=3, default='RUB')
    
    # Address fields
    shipping_address = models.TextField(blank=True)
    billing_address = models.TextField(blank=True)
    
    # Preferences
    receive_promotions = models.BooleanField(default=True)
    receive_order_updates = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')


class Device(models.Model):
    """User devices for security and session management"""
    
    DEVICE_TYPES = (
        ('web', 'Web Browser'),
        ('mobile', 'Mobile App'),
        ('tablet', 'Tablet'),
        ('desktop', 'Desktop App'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='web')
    device_id = models.CharField(max_length=200, unique=True)
    device_name = models.CharField(max_length=200, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    last_login = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_devices'
        ordering = ['-last_login']
    
    def __str__(self):
        return f"{self.user.email} - {self.device_name or self.device_type}"