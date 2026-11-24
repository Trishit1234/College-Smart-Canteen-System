from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from accounts.views import IsAdmin, IsStaffOrAdmin
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import Ingredient,Recipe,PurchaseRecord,InventoryTransaction
from rest_framework import serializers

class IngredientSerializer(serializers.ModelSerializer):
    low_stock=serializers.SerializerMethodField()
    class Meta:
        model=Ingredient
        fields='__all__'
    def get_low_stock(self,obj): return obj.quantity <= obj.minimum_stock

class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model=Recipe
        fields='__all__'

class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model=PurchaseRecord
        fields='__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model=InventoryTransaction
        fields='__all__'

class IngredientViewSet(viewsets.ModelViewSet):
    queryset=Ingredient.objects.select_related('supplier').all()
    serializer_class=IngredientSerializer
    permission_classes=[IsStaffOrAdmin]
    search_fields=['name']

    @action(detail=True,methods=['post'])
    def adjust(self,request,pk=None):
        ingredient=self.get_object()
        delta=request.data.get('quantity')
        kind=request.data.get('kind','ADJUSTMENT')
        try: delta=ingredient.quantity.__class__(delta)
        except Exception: return Response({'detail':'Quantity must be numeric.'},status=400)
        if ingredient.quantity + delta < 0:
            return Response({'detail':'Stock cannot be negative.'},status=400)
        with transaction.atomic():
            ingredient.quantity += delta
            ingredient.save(update_fields=['quantity','updated_at'])
            InventoryTransaction.objects.create(ingredient=ingredient,kind=kind,quantity=delta,note=request.data.get('note',''),created_by=request.user)
        return Response(IngredientSerializer(ingredient).data)

class RecipeViewSet(viewsets.ModelViewSet):
    queryset=Recipe.objects.select_related('item','ingredient').all()
    serializer_class=RecipeSerializer
    permission_classes=[IsAdmin]

class PurchaseViewSet(viewsets.ModelViewSet):
    queryset=PurchaseRecord.objects.select_related('supplier','ingredient').all()
    serializer_class=PurchaseSerializer
    permission_classes=[IsStaffOrAdmin]
    def perform_create(self,serializer):
        purchase=serializer.save()
        purchase.ingredient.quantity += purchase.quantity
        purchase.ingredient.save(update_fields=['quantity','updated_at'])
        InventoryTransaction.objects.create(ingredient=purchase.ingredient,kind='PURCHASE',quantity=purchase.quantity,note='Purchase recorded',created_by=self.request.user)

class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=InventoryTransaction.objects.select_related('ingredient','created_by').all()
    serializer_class=TransactionSerializer
    permission_classes=[IsStaffOrAdmin]
