"""
URL configuration for store project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from django.urls import path, include

from django.conf import settings

from django.conf.urls.static import static

from django.views.generic import TemplateView

from rest_framework import permissions

from drf_yasg.views import get_schema_view

from drf_yasg import openapi


from core.api.v1.users.views import (
    
    # Page Views (HTML)
    LoginPageView,
    RegisterPageView,
    ProfilePageView,
    VerifyEmailPageView,
    PasswordResetPageView,
    LogoutPageView,
)

from core.api.v1.product.views import ProductsPageView, ProductDetailPageView

schema_view = get_schema_view(
    openapi.Info(
        title="FashionStore API",
        default_version='v1',
        description="API for FashionStore E-Commerce Platform",
        contact=openapi.Contact(email="support@fashionstore.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api', include('core.api.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('home', TemplateView.as_view(template_name='index.html'), name='home'),
    path('products', TemplateView.as_view(template_name='products.html'), name='product'),
    
        # Auth pages

    path('', LoginPageView.as_view(), name='home'),
    path('login/', LoginPageView.as_view(), name='login_page'),
    path('register/', RegisterPageView.as_view(), name='register_page'),
    path('profile/', ProfilePageView.as_view(), name='profile_page'),
    path('verify-email/', VerifyEmailPageView.as_view(), name='verify_email_page'),
    path('reset-password/', PasswordResetPageView.as_view(), name='reset_password_page'),
    path('logout/', LogoutPageView.as_view(), name='logout_page'),

        #Products

    path('products', ProductsPageView.as_view(), name='products'),
    path('products/<slug:slug>/', ProductDetailPageView.as_view(), name='product_detail'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)




