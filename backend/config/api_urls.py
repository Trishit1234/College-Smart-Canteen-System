from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.views import RegisterView, LoginView, MeView, UserViewSet
from catalogue.views import CategoryViewSet, FoodItemViewSet
from commerce.views import CartViewSet, CheckoutView, CreateDemoPaymentView, VerifyDemoPaymentView, OrderViewSet, CouponViewSet, ReviewViewSet, PaymentViewSet, PickupSlotViewSet
from inventory.views import IngredientViewSet, RecipeViewSet, PurchaseViewSet, InventoryTransactionViewSet
from notifications.views import NotificationViewSet
from analytics.views import AnalyticsView, ReportView

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('categories', CategoryViewSet, basename='categories')
router.register('food', FoodItemViewSet, basename='food')
router.register('cart', CartViewSet, basename='cart')
router.register('orders', OrderViewSet, basename='orders')
router.register('coupons', CouponViewSet, basename='coupons')
router.register('reviews', ReviewViewSet, basename='reviews')
router.register('payments', PaymentViewSet, basename='payments')
router.register('pickup-slots', PickupSlotViewSet, basename='pickup-slots')
router.register('inventory/ingredients', IngredientViewSet, basename='ingredients')
router.register('inventory/recipes', RecipeViewSet, basename='recipes')
router.register('inventory/purchases', PurchaseViewSet, basename='purchases')
router.register('inventory/transactions', InventoryTransactionViewSet, basename='inventory-transactions')
router.register('notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),
    path('auth/me/', MeView.as_view()),
    path('checkout/', CheckoutView.as_view()),
    path('payments/create-demo-payment/', CreateDemoPaymentView.as_view()),
    path('payments/verify-demo-payment/', VerifyDemoPaymentView.as_view()),
    path('analytics/', AnalyticsView.as_view()),
    path('reports/<str:kind>/', ReportView.as_view()),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    *router.urls,
]
