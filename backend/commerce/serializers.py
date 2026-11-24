from rest_framework import serializers
from .models import Cart, CartItem, Coupon, Order, OrderItem, Payment, PaymentAttempt, Review, PickupSlot
from catalogue.serializers import FoodItemSerializer

class CartItemSerializer(serializers.ModelSerializer):
    item_detail = FoodItemSerializer(source='item', read_only=True)
    class Meta:
        model = CartItem
        fields = ['id','item','item_detail','quantity']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    class Meta:
        model = Cart
        fields = ['id','items','updated_at']

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id','name','unit_price','quantity','line_total']

class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.number', read_only=True)
    attempts = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ['id','order','order_number','method','status','transaction_id','test_mode','amount','created_at','paid_at','attempts']

    def get_attempts(self, payment):
        return PaymentAttemptSerializer(payment.attempts.all(), many=True).data

class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = ['id','transaction_id','method','status','amount','result_message','created_at','updated_at']

class PickupSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupSlot
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)
    customer_name = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Order
        fields = ['id','number','status','pickup_slot','subtotal','discount','tax','total','coupon_code','rejection_reason','customer_name','items','payment','created_at','updated_at','history']
        read_only_fields = ['number','subtotal','discount','tax','total','created_at','updated_at']

class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Review
        fields = ['id','item','username','rating','comment','created_at']
