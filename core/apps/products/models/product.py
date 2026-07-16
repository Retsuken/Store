from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Category(models.Model):
    """Product category model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='children'
    )
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_price = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Inventory
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_in_stock = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Relationships
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='products'
    )
    
    # Attributes
    brand = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=50, blank=True)
    size = models.CharField(max_length=20, blank=True)
    material = models.CharField(max_length=100, blank=True)
    
    # Images
    main_image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # Metadata
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['sku']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_featured']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.is_in_stock = self.stock > 0
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.sku}"
    
    @property
    def discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0


class ProductImage(models.Model):
    """Additional product images"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_main = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.product.name}"


class ProductReview(models.Model):
    """Product review model"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_verified = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_reviews'
        ordering = ['-created_at']
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name} - {self.rating}★"