from django.shortcuts import render
import uuid

# Create your views here.
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse
from accounts.views import IsAdmin, IsStaffOrAdmin
from catalogue.models import FoodItem
from .models import Cart, CartItem, Coupon, Order, OrderItem, OrderStatusHistory, Payment, PaymentAttempt, Review, PickupSlot
from .serializers import CartSerializer, CartItemSerializer, CouponSerializer, OrderSerializer, PaymentSerializer, PaymentAttemptSerializer, ReviewSerializer, PickupSlotSerializer
from notifications.models import Notification

class CartViewSet(viewsets.ViewSet):
    def list(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)
    @action(detail=False, methods=['post'])
    def add(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item = FoodItem.objects.filter(id=request.data.get('item'), available=True).first()
        try:
            quantity = int(request.data.get('quantity',1))
        except (TypeError,ValueError):
            return Response({'detail':'Quantity must be a whole number.'},status=400)
        if not item or quantity < 1:
            return Response({'detail':'Invalid item or quantity.'},status=400)
        cart_item, created = CartItem.objects.get_or_create(cart=cart,item=item)
        if cart_item.quantity + quantity > item.stock and not created:
            return Response({'detail':'Requested quantity exceeds available stock.'},status=400)
        cart_item.quantity = quantity if created else cart_item.quantity + quantity
        cart_item.save()
        return Response(CartSerializer(cart).data)
    @action(detail=False, methods=['post'])
    def set_quantity(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        try:
            ci = CartItem.objects.get(cart=cart,id=request.data.get('cart_item'))
        except CartItem.DoesNotExist:
            return Response({'detail':'Cart item not found.'},status=404)
        try:
            quantity = int(request.data.get('quantity',1))
        except (TypeError,ValueError):
            return Response({'detail':'Quantity must be a whole number.'},status=400)
        if quantity < 1:
            ci.delete()
        elif quantity <= ci.item.stock:
            ci.quantity = quantity; ci.save()
        else:
            return Response({'detail':'Insufficient stock.'},status=400)
        return Response(CartSerializer(cart).data)
    @action(detail=False, methods=['post'])
    def clear(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart).data)

class CheckoutView(APIView):
    @transaction.atomic
    def post(self, request):
        idempotency_key = request.headers.get('Idempotency-Key') or request.data.get('idempotency_key')
        if idempotency_key is not None:
            if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 64:
                return Response({'detail':'A valid checkout idempotency key is required.'},status=400)
            idempotency_key = idempotency_key.strip()
            existing = Order.objects.select_related('user','pickup_slot','payment').prefetch_related('items','history').filter(
                idempotency_key=idempotency_key
            ).first()
            if existing:
                if existing.user_id != request.user.id:
                    return Response({'detail':'This checkout key is already in use.'},status=409)
                return Response(OrderSerializer(existing).data,status=200)
        cart = Cart.objects.select_for_update().filter(user=request.user).first()
        if not cart or not cart.items.exists():
            return Response({'detail':'Cart is empty.'},status=400)
        slot_id = request.data.get('pickup_slot')
        coupon_code = (request.data.get('coupon_code') or '').strip().upper()
        method = request.data.get('payment_method',Payment.Method.CASH)
        allowed_methods = {Payment.Method.CASH,Payment.Method.UPI,Payment.Method.CARD,Payment.Method.NETBANKING,Payment.Method.WALLET}
        if not isinstance(method,str) or method not in allowed_methods:
            return Response({'detail':'Choose cash at counter or a clearly labelled simulated payment method.'},status=400)
        if not slot_id:
            return Response({'detail':'Select a pickup slot before checkout.'},status=400)
        slot = PickupSlot.objects.filter(id=slot_id,active=True).first()
        if not slot:
            return Response({'detail':'Choose an available pickup slot.'},status=400)
        subtotal = Decimal('0')
        lines = []
        for ci in cart.items.select_related('item').order_by('pk').select_for_update():
            item = FoodItem.objects.select_for_update().get(pk=ci.item_id)
            if not item.available or item.stock < ci.quantity:
                return Response({'detail':f'{item.name} is unavailable or out of stock.'},status=400)
            price = item.effective_price()
            subtotal += price * ci.quantity
            lines.append((item,ci.quantity,price))
        coupon = Coupon.objects.filter(code=coupon_code,active=True).first() if coupon_code else None
        discount = Decimal('0')
        if coupon_code and not coupon:
            return Response({'detail':'Coupon is invalid or inactive.'},status=400)
        if coupon and coupon.valid_until and coupon.valid_until < timezone.now():
            return Response({'detail':'Coupon has expired.'},status=400)
        if coupon and subtotal < coupon.minimum_amount:
            return Response({'detail':f'Coupon requires a minimum order of ₹{coupon.minimum_amount}.'},status=400)
        if coupon:
            discount = min(subtotal * coupon.discount_percent / 100, coupon.max_discount or subtotal)
        tax = (subtotal - discount) * Decimal('0.05')
        total = subtotal - discount + tax
        order_status = Order.Status.PENDING if method == Payment.Method.CASH else Order.Status.AWAITING_PAYMENT
        order = Order.objects.create(user=request.user,pickup_slot=slot,status=order_status,
            idempotency_key=idempotency_key,
            subtotal=subtotal,discount=discount,tax=tax,total=total,coupon_code=coupon_code if coupon else '')
        for item,quantity,price in lines:
            item.stock -= quantity
            item.save(update_fields=['stock'])
            OrderItem.objects.create(order=order,item=item,name=item.name,unit_price=price,
                quantity=quantity,line_total=price*quantity)
        test_mode = method != Payment.Method.CASH
        Payment.objects.create(order=order,method=method,status=Payment.Status.PENDING,amount=total,
            test_mode=test_mode)
        OrderStatusHistory.objects.create(
            order=order,status=order_status,
            note='Order placed; pay at the counter.' if method == Payment.Method.CASH else 'Order awaiting simulated payment.',
        )
        cart.items.all().delete()
        Notification.objects.create(
            user=request.user,
            title='Order placed' if method == Payment.Method.CASH else 'Payment required',
            message=(
                f'Your order {order.number} was placed successfully.'
                if method == Payment.Method.CASH
                else f'Order {order.number} is reserved while simulated payment is pending. No money will be charged.'
            ),
            kind='ORDER',
        )
        return Response(OrderSerializer(order).data,status=201)

class DemoPaymentCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=[
        (Payment.Method.UPI,'UPI'),
        (Payment.Method.CARD,'Card'),
        (Payment.Method.NETBANKING,'Net banking'),
        (Payment.Method.WALLET,'Wallet'),
    ])
    idempotency_key = serializers.CharField(max_length=64)

class DemoPaymentVerifySerializer(serializers.Serializer):
    attempt_id = serializers.IntegerField(min_value=1)
    simulated_result = serializers.ChoiceField(choices=[
        (PaymentAttempt.Status.SUCCESS,'Success'),
        (PaymentAttempt.Status.FAILED,'Failure'),
    ])

class CreateDemoPaymentView(APIView):
    permission_classes=[permissions.IsAuthenticated]

    @transaction.atomic
    def post(self,request):
        serializer=DemoPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data=serializer.validated_data
        order=Order.objects.select_for_update().filter(
            id=data['order_id'],user=request.user,
        ).first()
        if not order:
            return Response({'detail':'Order not found.'},status=404)
        try:
            payment=Payment.objects.select_for_update().get(order=order)
        except Payment.DoesNotExist:
            return Response({'detail':'This order has no payment record.'},status=404)

        existing=PaymentAttempt.objects.filter(idempotency_key=data['idempotency_key']).first()
        if existing:
            if existing.payment_id != payment.id:
                return Response({'detail':'This payment request key is already in use.'},status=409)
            return Response(PaymentAttemptSerializer(existing).data,status=200)
        if order.status != Order.Status.AWAITING_PAYMENT:
            return Response({'detail':'This order is not awaiting simulated payment.'},status=409)
        if payment.status == Payment.Status.PAID:
            return Response({'detail':'This order is already paid.'},status=409)
        if payment.status == Payment.Status.CANCELLED:
            return Response({'detail':'This order payment was cancelled.'},status=409)
        if payment.attempts.filter(status=PaymentAttempt.Status.PROCESSING).exists():
            return Response({'detail':'A payment attempt is already processing.'},status=409)

        amount=order.total
        attempt=PaymentAttempt.objects.create(
            payment=payment,
            idempotency_key=data['idempotency_key'],
            transaction_id=f'GCLET-TEST-{uuid.uuid4().hex[:16].upper()}',
            method=data['method'],
            status=PaymentAttempt.Status.PROCESSING,
            amount=amount,
            result_message='Simulated payment is processing. No money will be charged.',
        )
        payment.method=data['method']
        payment.status=Payment.Status.PROCESSING
        payment.transaction_id=''
        payment.amount=amount
        payment.test_mode=True
        payment.save(update_fields=['method','status','transaction_id','amount','test_mode'])
        return Response(PaymentAttemptSerializer(attempt).data,status=201)

class VerifyDemoPaymentView(APIView):
    permission_classes=[permissions.IsAuthenticated]

    @transaction.atomic
    def post(self,request):
        serializer=DemoPaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data=serializer.validated_data
        attempt_ref=PaymentAttempt.objects.filter(
            id=data['attempt_id'],payment__order__user=request.user,
        ).values('id','payment_id','payment__order_id').first()
        if not attempt_ref:
            return Response({'detail':'Payment attempt not found.'},status=404)

        order=Order.objects.select_for_update().get(id=attempt_ref['payment__order_id'])
        payment=Payment.objects.select_for_update().get(id=attempt_ref['payment_id'])
        attempt=PaymentAttempt.objects.select_for_update().get(id=attempt_ref['id'])
        result=data['simulated_result']

        if attempt.status in (PaymentAttempt.Status.SUCCESS,PaymentAttempt.Status.FAILED,PaymentAttempt.Status.CANCELLED):
            return Response(self._result_payload(attempt,payment,order),status=200)
        if attempt.status != PaymentAttempt.Status.PROCESSING:
            return Response({'detail':'This payment attempt is not processing.'},status=409)
        if order.status != Order.Status.AWAITING_PAYMENT or payment.status != Payment.Status.PROCESSING:
            return Response({'detail':'The order is no longer awaiting payment.'},status=409)
        if attempt.amount != order.total or payment.amount != order.total:
            return Response({'detail':'The stored payment amount does not match the order total.'},status=409)

        self._apply_result(attempt,payment,order,result)
        return Response(self._result_payload(attempt,payment,order),status=200)

    @staticmethod
    def _apply_result(attempt,payment,order,result):
        if result == PaymentAttempt.Status.SUCCESS:
            attempt.status=PaymentAttempt.Status.SUCCESS
            attempt.result_message='Demo verification succeeded. No money was charged.'
            payment.status=Payment.Status.PAID
            payment.transaction_id=attempt.transaction_id
            order.status=Order.Status.PENDING
            payment.paid_at=timezone.now()
            order.save(update_fields=['status','updated_at'])
            OrderStatusHistory.objects.create(
                order=order,status=Order.Status.PENDING,
                note='Simulated payment verified successfully.',
            )
            Notification.objects.create(
                user=order.user,title='Simulated payment successful',
                message=f'Payment for order {order.number} was verified in test mode. No money was charged.',
                kind='PAYMENT',
            )
        else:
            attempt.status=PaymentAttempt.Status.FAILED
            attempt.result_message='Simulated payment declined. Your order is saved for retry; no money was charged.'
            payment.status=Payment.Status.FAILED
            Notification.objects.create(
                user=order.user,title='Simulated payment failed',
                message=f'Payment for order {order.number} failed in test mode. Retry using the same order.',
                kind='PAYMENT',
            )
        attempt.save(update_fields=['status','result_message','updated_at'])
        payment.save(update_fields=['status','transaction_id','paid_at'])

    @staticmethod
    def _result_payload(attempt,payment,order):
        return {
            'attempt':PaymentAttemptSerializer(attempt).data,
            'payment_id':payment.id,
            'order_id':order.id,
            'order_number':order.number,
            'order_status':order.status,
            'test_mode':True,
        }

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('user','pickup_slot','payment').prefetch_related('items','history').order_by('-created_at')
    serializer_class = OrderSerializer
    filterset_fields = ['status','user']
    search_fields = ['number','user__username']
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role in ('STAFF','ADMIN') or user.is_superuser:
            qs = qs.exclude(status=Order.Status.AWAITING_PAYMENT)
        else:
            qs = qs.filter(user=user)
        return qs
    def get_permissions(self):
        if self.action in ('destroy','create'):
            return [permissions.IsAuthenticated()]
        if self.action in ('update','partial_update','status','accept','reject','complete'):
            return [IsStaffOrAdmin()]
        return [permissions.IsAuthenticated()]
    @action(detail=True,methods=['post'])
    def accept(self,request,pk=None):
        return self._set_status(self.get_object(),'CONFIRMED','Accepted by canteen')
    @action(detail=True,methods=['post'])
    def status(self,request,pk=None):
        status_value=request.data.get('status')
        allowed={'CONFIRMED','PREPARING','READY FOR PICKUP','COMPLETED','REJECTED','CANCELLED'}
        if status_value not in allowed:
            return Response({'detail':'Invalid status.'},status=400)
        note=request.data.get('note','')
        if status_value=='REJECTED':
            return self._reject(self.get_object(),request.data.get('reason','Not available'))
        return self._set_status(self.get_object(),status_value,note)
    def _set_status(self,order,status_value,note):
        order.status=status_value; order.save(update_fields=['status','updated_at'])
        OrderStatusHistory.objects.create(order=order,status=status_value,note=note,changed_by=None)
        Notification.objects.create(user=order.user,title=f'Order {status_value.lower()}',
            message=f'Order {order.number}: {note or status_value}',kind='ORDER')
        return Response(OrderSerializer(order).data)
    def _reject(self,order,reason):
        with transaction.atomic():
            order.status='REJECTED'; order.rejection_reason=reason; order.save()
            for oi in order.items.select_related('item').select_for_update():
                oi.item.stock += oi.quantity; oi.item.save(update_fields=['stock'])
            OrderStatusHistory.objects.create(order=order,status='REJECTED',note=reason)
        return Response(OrderSerializer(order).data)
    @action(detail=True,methods=['post'])
    def reject(self,request,pk=None):
        return self._reject(self.get_object(),request.data.get('reason','Not available'))
    @action(detail=True,methods=['post'])
    @transaction.atomic
    def complete(self,request,pk=None):
        order=Order.objects.select_for_update().get(pk=self.get_object().pk)
        if hasattr(order,'payment') and order.payment.method==Payment.Method.CASH and order.payment.status==Payment.Status.PENDING:
            payment=Payment.objects.select_for_update().get(pk=order.payment.pk)
            payment.status=Payment.Status.PAID
            payment.transaction_id=f'CASH-{order.number}'
            payment.paid_at=timezone.now()
            payment.save(update_fields=['status','transaction_id','paid_at'])
        return self._set_status(order,'COMPLETED','Collected and completed')
    @action(detail=True,methods=['post'])
    @transaction.atomic
    def cancel(self,request,pk=None):
        order=Order.objects.select_for_update().get(pk=self.get_object().pk)
        if order.user_id != request.user.id:
            return Response({'detail':'You cannot cancel this order.'},status=403)
        if order.status not in ('PENDING','CONFIRMED',Order.Status.AWAITING_PAYMENT):
            return Response({'detail':'This order can no longer be cancelled.'},status=400)
        if hasattr(order,'payment'):
            payment=Payment.objects.select_for_update().get(pk=order.payment.pk)
            if payment.status == Payment.Status.PAID:
                return Response({'detail':'A paid order cannot be cancelled from here.'},status=400)
            payment.status=Payment.Status.CANCELLED
            payment.save(update_fields=['status'])
            payment.attempts.filter(status__in=[
                PaymentAttempt.Status.PENDING,PaymentAttempt.Status.PROCESSING,
            ]).update(
                status=PaymentAttempt.Status.CANCELLED,
                result_message='Order cancelled by customer.',
                updated_at=timezone.now(),
            )
        order.status='CANCELLED'; order.save(update_fields=['status','updated_at'])
        for oi in order.items.select_related('item').select_for_update():
            oi.item.stock += oi.quantity; oi.item.save(update_fields=['stock'])
        OrderStatusHistory.objects.create(order=order,status='CANCELLED',note='Cancelled by customer')
        return Response(OrderSerializer(order).data)

class CouponViewSet(viewsets.ModelViewSet):
    queryset=Coupon.objects.all()
    serializer_class=CouponSerializer
    permission_classes=[IsAdmin]
    def get_permissions(self):
        return [permissions.AllowAny()] if self.action=='list' else [IsAdmin()]

class ReviewViewSet(viewsets.ModelViewSet):
    queryset=Review.objects.select_related('user','item').all()
    serializer_class=ReviewSerializer
    def get_queryset(self):
        qs=super().get_queryset()
        return qs if self.request.user.is_authenticated and self.request.user.role in ('ADMIN','STAFF') else qs.filter(user=self.request.user)
    def perform_create(self,serializer):
        serializer.save(user=self.request.user)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=Payment.objects.select_related('order','order__user').prefetch_related('attempts').order_by('-created_at')
    serializer_class=PaymentSerializer
    def get_queryset(self):
        qs=super().get_queryset()
        if self.request.user.role not in ('STAFF','ADMIN') and not self.request.user.is_superuser:
            qs=qs.filter(order__user=self.request.user)
        return qs

    @action(detail=False,methods=['get'])
    def history(self,request):
        return self.list(request)

    @action(detail=True,methods=['get'])
    def receipt(self,request,pk=None):
        payment=self.get_object()
        if payment.status != Payment.Status.PAID:
            return Response({'detail':'A receipt is available after successful payment.'},status=400)
        cash_payment=payment.method == Payment.Method.CASH
        receipt_type='CASH PAYMENT RECEIPT' if cash_payment else 'SIMULATED PAYMENT - TEST MODE'
        paid_at=payment.paid_at or payment.created_at
        response=HttpResponse(
            '\n'.join([
                'GCLET SMART CANTEEN PAYMENT RECEIPT',
                receipt_type,
                f'Order: {payment.order.number}',
                f'Transaction: {payment.transaction_id}',
                f'Method: {payment.get_method_display()}',
                f'Amount: INR {payment.amount}',
                f'Paid at: {paid_at.isoformat()}',
                'Payment received at the canteen counter.' if cash_payment else 'No money was charged.',
            ]),
            content_type='text/plain; charset=utf-8',
        )
        response['Content-Disposition']=f'attachment; filename="GCLET-{payment.order.number}-receipt.txt"'
        return response

    @action(detail=True,methods=['post'],url_path='confirm-test')
    @transaction.atomic
    def confirm_test(self,request,pk=None):
        payment=self.get_object()
        if not payment.test_mode or payment.method not in (
            Payment.Method.UPI,Payment.Method.CARD,Payment.Method.NETBANKING,Payment.Method.WALLET,
        ):
            return Response({'detail':'Only simulated payment methods can be confirmed here.'},status=400)
        if payment.status == Payment.Status.PAID:
            return Response(PaymentSerializer(payment).data)
        order=Order.objects.select_for_update().get(pk=payment.order_id)
        if order.status != Order.Status.AWAITING_PAYMENT:
            return Response({'detail':'This order is not awaiting simulated payment.'},status=409)
        attempt=payment.attempts.filter(status=PaymentAttempt.Status.PROCESSING).first()
        if not attempt:
            attempt=PaymentAttempt.objects.create(
                payment=payment,
                idempotency_key=f'legacy-confirm-{uuid.uuid4().hex}',
                transaction_id=f'GCLET-TEST-{uuid.uuid4().hex[:16].upper()}',
                method=payment.method,
                status=PaymentAttempt.Status.PROCESSING,
                amount=order.total,
                result_message='Legacy test confirmation is processing.',
            )
        VerifyDemoPaymentView._apply_result(attempt,payment,order,PaymentAttempt.Status.SUCCESS)
        return Response(PaymentSerializer(payment).data)

class PickupSlotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=PickupSlot.objects.filter(active=True).order_by('start_time')
    serializer_class=PickupSlotSerializer
    permission_classes=[permissions.AllowAny]
