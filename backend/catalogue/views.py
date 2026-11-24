from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from accounts.views import IsAdmin
from .models import FoodCategory, FoodItem
from .serializers import CategorySerializer, FoodItemSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = FoodCategory.objects.all()
    serializer_class = CategorySerializer
    filterset_fields = ['is_active']
    search_fields = ['name']
    def get_permissions(self):
        return [IsAdmin()] if self.action in ('create','update','partial_update','destroy') else [permissions.AllowAny()]
    def get_queryset(self):
        queryset=super().get_queryset()
        user=self.request.user
        if not user.is_authenticated or (user.role!='ADMIN' and not user.is_superuser):
            queryset=queryset.filter(is_active=True)
        return queryset

class FoodItemViewSet(viewsets.ModelViewSet):
    queryset = FoodItem.objects.select_related('category').all()
    serializer_class = FoodItemSerializer
    filterset_fields = ['category','available','featured','is_vegetarian']
    search_fields = ['name','description','allergens']
    ordering_fields = ['price','stock','created_at']
    def get_permissions(self):
        return [IsAdmin()] if self.action in ('create','update','partial_update','destroy') else [permissions.AllowAny()]
    def get_queryset(self):
        queryset=super().get_queryset()
        user=self.request.user
        if not user.is_authenticated or (user.role!='ADMIN' and not user.is_superuser):
            queryset=queryset.filter(available=True,category__is_active=True)
        return queryset
