from django.contrib import admin



from .models import User, UserProfile, Device

@admin.register(User)
class User(admin.ModelAdmin):
    list_display = ('id', 'email', 'phone_number', 'user_type', 'is_email_verified', 'is_phone_verified', 'avatar', 'date_of_birth', 'bio', 'telegram', 'instagram', 'facebook', 'last_login_ip', 'last_activity', 'created_at', 'updated_at', 'last_verification_sent')


@admin.register(UserProfile)
class UserProfile(admin.ModelAdmin):
    list_display = ('user', 'newsletter_subscribed', 'preferred_language', 'preferred_currency', 'shipping_address', 'billing_address', 'receive_promotions', 'receive_order_updates', 'created_at', 'updated_at')