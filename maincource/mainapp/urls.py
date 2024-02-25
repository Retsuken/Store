from . import views
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.views.decorators.cache import cache_page
urlpatterns = [
    path('', views.IndexView.as_view(), name='home'),
    path('products/', views.products, name='products'),
    path('category/<int:category_id>/', views.products, name='category'),
    path('baskets/add/<int:product_id>/', login_required(views.basket_add), name='basket_add'),
    path('baskets/remove/<int:basket_id>/', views.basket_remove, name ='basket_remove'),
    # Корзина и продукты 

    path('login.html/', views.UserLoginView.as_view(), name='login'),
    path('profile/<int:pk>/', login_required(views.UserProfileView.as_view()), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('reg', views.UserRegistrationView.as_view(), name='registration'),
    # Все с профилем

    path('verify/<str:email>/<uuid:code>/', views.EmailVerificationView.as_view(), name='email_verification'),
    # Email

    path('accounts/', include('allauth.urls')),
    path("__debug__/", include("debug_toolbar.urls")),
    # Прочее

    path('orders/order-create.html', views.OrderView.as_view(), name='order'),
    path('orders/orders.html', views.Order, name='order-orders'),
    path('order-success', views.SuccessView.as_view(), name='order_success'),
    path('order-cancel', views.CancelView.as_view(), name='order_cancel'),
    path('webhook/stripe/', views.stripe_webhook_view, name='stripe_webhook'),
    # Оплата 
] 
