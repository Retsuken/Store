from django.contrib import admin
from .models import User, EmailVerification, Order, ProductCategory, Product, Basket


admin.site.register(Basket)
admin.site.register(ProductCategory)
admin.site.register(Product)


@admin.register(User)
class Useradmin(admin.ModelAdmin):
    list_display = ['first_name', 'username']


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['code', 'user', 'expiration']


admin.site.register(Order)