from rest_framework import generics, filters, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import render
from django.views import View
from django.conf import settings
from django.db import models
from django.db.models import Q, Avg
from django_filters.rest_framework import DjangoFilterBackend
from core.apps.products.models import Product, Category
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    CategorySerializer, AddToCartSerializer,
    UpdateCartSerializer, CartItemSerializer
)


class ProductListView(generics.ListAPIView):
    """API view for product list with filters"""
    
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'color', 'size', 'is_featured']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'created_at', 'name', 'stock']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Price range filter
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    """API view for product detail"""
    
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class CategoryListView(generics.ListAPIView):
    """API view for categories"""
    
    queryset = Category.objects.filter(is_active=True, parent__isnull=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class FeaturedProductsView(generics.ListAPIView):
    """API view for featured products"""
    
    queryset = Product.objects.filter(is_active=True, is_featured=True)
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = None


# ==================== CART VIEWS ====================

class AddToCartView(APIView):
    """API view for adding product to cart"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check stock
        if quantity > product.stock:
            return Response(
                {'error': f'Only {product.stock} items available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create cart
        cart = request.session.get('cart', {})
        
        if str(product_id) in cart:
            cart[str(product_id)] += quantity
        else:
            cart[str(product_id)] = quantity
        
        # Save cart to session
        request.session['cart'] = cart
        request.session.modified = True
        
        # Get cart items details
        cart_items = get_cart_items(request)
        
        return Response({
            'message': 'Product added to cart successfully',
            'cart': cart,
            'cart_count': sum(cart.values()),
            'items': cart_items
        }, status=status.HTTP_200_OK)


class GetCartView(APIView):
    """API view for getting cart"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        cart_items = get_cart_items(request)
        total = sum(item['total'] for item in cart_items)
        
        return Response({
            'items': cart_items,
            'total': total,
            'count': sum(item['quantity'] for item in cart_items)
        })


class UpdateCartView(APIView):
    """API view for updating cart item"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = UpdateCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = str(serializer.validated_data['product_id'])
        quantity = serializer.validated_data['quantity']
        
        cart = request.session.get('cart', {})
        
        if quantity <= 0:
            # Remove item
            if product_id in cart:
                del cart[product_id]
        else:
            # Update quantity
            cart[product_id] = quantity
        
        # Save cart to session
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_items = get_cart_items(request)
        
        return Response({
            'message': 'Cart updated successfully',
            'cart': cart,
            'cart_count': sum(cart.values()),
            'items': cart_items
        })


class ClearCartView(APIView):
    """API view for clearing cart"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        request.session['cart'] = {}
        request.session.modified = True
        
        return Response({
            'message': 'Cart cleared successfully',
            'cart_count': 0
        })


# ==================== HELPER FUNCTIONS ====================

def get_cart_items(request):
    """Get cart items with product details"""
    cart = request.session.get('cart', {})
    items = []
    
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            
            # Check if product still in stock
            if quantity > product.stock:
                quantity = product.stock
            
            items.append({
                'product_id': str(product.id),
                'name': product.name,
                'price': float(product.price),
                'quantity': quantity,
                'total': float(product.price * quantity),
                'image_url': product.main_image.url if product.main_image else None,
                'slug': product.slug,
                'in_stock': product.is_in_stock
            })
        except Product.DoesNotExist:
            # Remove non-existent product from cart
            if product_id in cart:
                del cart[product_id]
            request.session['cart'] = cart
            request.session.modified = True
    
    return items


class ProductsPageView(View):
    """Products page view"""
    
    def get(self, request):
        return render(request, 'product/products.html', {
            'api_base_url': settings.API_BASE_URL
        })


class ProductDetailPageView(View):
    """Product detail page view"""
    
    def get(self, request, slug):
        return render(request, 'product/product_detail.html', {
            'slug': slug,
            'api_base_url': settings.API_BASE_URL
        })