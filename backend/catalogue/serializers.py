from rest_framework import serializers
from .models import FoodCategory, FoodItem

class OptionalDecimalField(serializers.DecimalField):
    def to_internal_value(self, data):
        if data == '':
            return None
        return super().to_internal_value(data)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = '__all__'

class FoodItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    effective_price = serializers.SerializerMethodField()
    discounted_price = OptionalDecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    class Meta:
        model = FoodItem
        fields = '__all__'
    def validate_image(self, image):
        if image and image.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Food images must be 5 MB or smaller.')
        return image
    def get_effective_price(self, obj):
        return obj.effective_price()
