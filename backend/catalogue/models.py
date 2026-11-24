from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator

class FoodCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class FoodItem(models.Model):
    category = models.ForeignKey(FoodCategory, related_name='items', on_delete=models.PROTECT)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='food/uploads/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    preparation_time = models.PositiveIntegerField(default=15)
    is_vegetarian = models.BooleanField(default=True)
    allergens = models.CharField(max_length=255, blank=True)
    available = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def effective_price(self):
        return self.discounted_price if self.discounted_price is not None else self.price
