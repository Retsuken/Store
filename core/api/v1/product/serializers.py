from rest_framework import serializers
from django.db import models
from core.apps.products.models import Category, Product, ProductImage, ProductReview


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer"""
    
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = (
            'id', 'name', 'slug', 'description', 
            'image', 'parent', 'children', 'is_active'
        )
    
    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer"""
    
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'is_main', 'order')


class ProductReviewSerializer(serializers.ModelSerializer):
    """Product review serializer"""
    
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductReview
        fields = (
            'id', 'user', 'user_name', 'rating', 
            'title', 'comment', 'created_at'
        )
        read_only_fields = ('user', 'created_at')
    
    def get_user_name(self, obj):
        return obj.user.full_name or obj.user.username


class ProductListSerializer(serializers.ModelSerializer):
    """Product list serializer (lightweight)"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    main_image_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'sku', 'price', 'compare_price',
            'discount_percentage', 'stock', 'is_in_stock', 'is_featured',
            'category', 'category_name', 'brand', 'color', 'size',
            'main_image', 'main_image_url', 'average_rating', 'reviews_count'
        )
    
    def get_main_image_url(self, obj):
        if obj.main_image:
            return obj.main_image.url
        return None
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(reviews.aggregate(avg=models.Avg('rating'))['avg'], 1)
        return 0
    
    def get_reviews_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product detail serializer (full)"""
    
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'sku', 'description', 'short_description',
            'price', 'compare_price', 'discount_percentage', 'cost',
            'stock', 'is_in_stock', 'is_featured', 'is_active',
            'category', 'brand', 'color', 'size', 'material',
            'main_image', 'images', 'weight', 'dimensions',
            'average_rating', 'reviews_count', 'reviews',
            'related_products', 'created_at', 'updated_at'
        )
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(reviews.aggregate(avg=models.Avg('rating'))['avg'], 1)
        return 0
    
    def get_reviews_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()
    
    def get_related_products(self, obj):
        # Get products from same category
        related = Product.objects.filter(
            category=obj.category,
            is_active=True
        ).exclude(id=obj.id)[:4]
        return ProductListSerializer(related, many=True).data


class AddToCartSerializer(serializers.Serializer):
    """Add to cart serializer"""
    
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartSerializer(serializers.Serializer):
    """Update cart serializer"""
    
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=0)


class CartItemSerializer(serializers.Serializer):
    """Cart item serializer"""
    
    product_id = serializers.UUIDField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    image_url = serializers.CharField(allow_null=True)