from typing import Any
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponse as HttpResponse
from django.shortcuts import render, HttpResponseRedirect
from .models import User, EmailVerification, Product, ProductCategory, Basket, Order
from .forms import UserLoginForm, UserRegistrationForm, UserProfileForm, OrderForm
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView, DetailView, FormView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
import stripe
from django.conf import settings
stripe.api_key = settings.STRIPE_SECRET_KEY
from http import HTTPStatus
from django.views.decorators.csrf import csrf_exempt





class IndexView(TemplateView):
    template_name = 'index.html'


def Order(request):
    return render(request, 'orders/order.html')


class SuccessView(TemplateView):
    template_name = 'orders/success.html'

class CancelView(TemplateView):
    template_name = 'orders/cancel.html'

def products(request, category_id=None):
    products = Product.objects.filter(category_id=category_id) if category_id else Product.objects.all()
    context = {'categories': ProductCategory.objects.all(), 'products': products}
    return render(request, 'products.html', context)




class UserLoginView(LoginView):
    template_name = 'login.html'
    form_class = UserLoginForm




class UserRegistrationView(SuccessMessageMixin, CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'register.html'
    success_url = reverse_lazy('login')
    success_message = 'Вы успешно зарегистрированы'





class UserProfileView(UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'profile.html'

    def get_success_url(self):
        return reverse_lazy('profile', args=(self.object.id,))




def basket_add(request, product_id):
    product = Product.objects.get(id=product_id)
    baskets = Basket.objects.filter(user=request.user, product=product)
    if not baskets.exists():
        Basket.objects.create(user=request.user, product=product, quantity=1)
    else:
        basket = baskets.first()
        basket.quantity += 1
        basket.save()

    return HttpResponseRedirect(request.META['HTTP_REFERER'])

def basket_remove(request, basket_id):
    basket = Basket.objects.get(id=basket_id)
    basket.delete()
    return HttpResponseRedirect(request.META['HTTP_REFERER'])





class EmailVerificationView(TemplateView):
    template_name = 'email_verification.html'

    def get(self, request, *args, **kwargs):
        code = kwargs['code']
        user = User.objects.get(email=kwargs['email'])
        email_verifications = EmailVerification.objects.filter(user=user, code=code)
        if email_verifications.exists() and not email_verifications.first().is_expired():
            user.is_verified_email = True
            user.save()
            return super(EmailVerificationView, self).get(request, *args, **kwargs)
        else:
            return HttpResponseRedirect('/')




class OrderView(CreateView):
    template_name = 'orders/order-create.html'
    form_class = OrderForm
    success_url = reverse_lazy('order')

    def post(self, request, *args, **kwargs):
        super(OrderView, self).post(request, *args, **kwargs)
        baskets = Basket.objects.filter(user=self.request.user)
        checkout_session = stripe.checkout.Session.create(
            line_items=baskets.stripe_products(),
            metadata={'order_id': self.object.id},
            mode='payment',
            success_url='{}{}'.format(settings.DOMAIN_NAME, reverse('order_success')),
            cancel_url='{}{}'.format(settings.DOMAIN_NAME, reverse('order_cancel')),
        )
        return HttpResponseRedirect(checkout_session.url, status=HTTPStatus.SEE_OTHER)

    def form_valid(self, form):
        form.instance.initiator = self.request.user
        return super(OrderView, self).form_valid(form)


@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Fulfill the purchase...
        fulfill_order(session)

    return HttpResponse(status=200)

def fulfill_order(session):
    order_id = int(session.metadata.order_id)
    order = Order.objects.get(id=order_id)
    order.update_after_payment()





















