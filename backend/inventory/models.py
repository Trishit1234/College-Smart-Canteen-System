from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from catalogue.models import FoodItem

class Supplier(models.Model):
    name=models.CharField(max_length=150)
    phone=models.CharField(max_length=15,blank=True)
    email=models.EmailField(blank=True)
    active=models.BooleanField(default=True)

class Ingredient(models.Model):
    name=models.CharField(max_length=150,unique=True)
    unit=models.CharField(max_length=20,default='kg')
    quantity=models.DecimalField(max_digits=12,decimal_places=3,default=0)
    minimum_stock=models.DecimalField(max_digits=12,decimal_places=3,default=0)
    supplier=models.ForeignKey(Supplier,on_delete=models.SET_NULL,null=True,blank=True)
    updated_at=models.DateTimeField(auto_now=True)

class Recipe(models.Model):
    item=models.ForeignKey(FoodItem,related_name='recipes',on_delete=models.CASCADE)
    ingredient=models.ForeignKey(Ingredient,related_name='recipes',on_delete=models.CASCADE)
    quantity=models.DecimalField(max_digits=12,decimal_places=3)
    class Meta:
        unique_together=('item','ingredient')

class InventoryTransaction(models.Model):
    ingredient=models.ForeignKey(Ingredient,related_name='transactions',on_delete=models.PROTECT)
    kind=models.CharField(max_length=20)
    quantity=models.DecimalField(max_digits=12,decimal_places=3)
    note=models.CharField(max_length=255,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    created_at=models.DateTimeField(auto_now_add=True)

class PurchaseRecord(models.Model):
    supplier=models.ForeignKey(Supplier,on_delete=models.PROTECT)
    ingredient=models.ForeignKey(Ingredient,on_delete=models.PROTECT)
    quantity=models.DecimalField(max_digits=12,decimal_places=3)
    unit_cost=models.DecimalField(max_digits=10,decimal_places=2)
    purchase_date=models.DateField(auto_now_add=True)
