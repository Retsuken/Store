from django.contrib import admin

from django.utils.html import format_html

from .models import Product

@admin.register(Product)
class Product(admin.ModelAdmin):
    list_display = ('title', 'description', 'cost', 'photo')

    def photo(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width: 50px; height: auto;" />', obj.photo.url)
        return "Нет изображения"

    photo.short_description = 'Фотография'  
