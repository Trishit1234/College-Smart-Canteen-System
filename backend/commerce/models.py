from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from catalogue.models import FoodItem

class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(blank=True, null=True)

class PickupSlot(models.Model):
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=20)
    active = models.BooleanField(default=True)

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='cart', on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(FoodItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    class Meta:
        unique_together = ('cart','item')

class Order(models.Model):
    class Status(models.TextChoices):
        AWAITING_PAYMENT='AWAITING PAYMENT','Awaiting payment'; PENDING='PENDING','Pending'
        CONFIRMED='CONFIRMED','Confirmed'; PREPARING='PREPARING','Preparing'
        READY='READY FOR PICKUP','Ready for pickup'; COMPLETED='COMPLETED','Completed'
        REJECTED='REJECTED','Rejected'; CANCELLED='CANCELLED','Cancelled'
        REFUND_PENDING='REFUND PENDING','Refund pending'; REFUNDED='REFUNDED','Refunded'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', on_delete=models.PROTECT)
    number = models.CharField(max_length=30, unique=True, editable=False)
    idempotency_key = models.CharField(max_length=64, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    pickup_slot = models.ForeignKey(PickupSlot, on_delete=models.PROTECT, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=30, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self,*args,**kwargs):
        if not self.number:
            self.number = f'GCLET-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args,**kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(FoodItem, on_delete=models.PROTECT)
    name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, related_name='history', on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    class Method(models.TextChoices):
        CASH='CASH','Cash at counter'; UPI='UPI','UPI Test'; CARD='CARD','Card Test'
        NETBANKING='NETBANKING','Net banking Test'; WALLET='WALLET','Wallet Test'
        GATEWAY='GATEWAY','Online gateway'
    class Status(models.TextChoices):
        PENDING='PENDING','Pending'; PROCESSING='PROCESSING','Processing'; PAID='PAID','Paid'
        FAILED='FAILED','Failed'; CANCELLED='CANCELLED','Cancelled'; REFUNDED='REFUNDED','Refunded'
    order = models.OneToOneField(Order, related_name='payment', on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=100, blank=True)
    test_mode = models.BooleanField(default=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        PENDING='PENDING','Pending'; PROCESSING='PROCESSING','Processing'
        SUCCESS='SUCCESS','Success'; FAILED='FAILED','Failed'; CANCELLED='CANCELLED','Cancelled'

    payment = models.ForeignKey(Payment, related_name='attempts', on_delete=models.CASCADE)
    idempotency_key = models.CharField(max_length=64, unique=True)
    transaction_id = models.CharField(max_length=100, unique=True)
    method = models.CharField(max_length=20, choices=Payment.Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    result_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

class Refund(models.Model):
    payment = models.ForeignKey(Payment, related_name='refunds', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reviews', on_delete=models.CASCADE)
    item = models.ForeignKey(FoodItem, related_name='reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
