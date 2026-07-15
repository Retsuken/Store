from django.db import models



class Product(models.Model):
    title = models.CharField(
        verbose_name='Название продукта',
        max_length=128,
    )

    description = models.TextField(
        verbose_name='Описание продукта'
    )

    cost = models.IntegerField(
        verbose_name='Цена'
    )

    photo = models.ImageField(
        upload_to='image/product',  # Папка, куда будут загружаться изображения
        verbose_name="Фотография",
    )

    def __str__(self) -> str:
        return self.title
    
    class Meta:
        verbose_name = 'Продукты'
        verbose_name_plural = 'Продукты'