from django.core.management.base import BaseCommand
from accounts.models import User
from catalogue.models import FoodCategory, FoodItem
from commerce.models import PickupSlot, Coupon, Order
from inventory.models import Supplier, Ingredient
from datetime import time
from decimal import Decimal
from django.db import transaction
from django.utils.text import slugify

class Command(BaseCommand):
    help='Creates development users and realistic canteen demo data'

    @transaction.atomic
    def handle(self,*args,**options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin','admin@gclet.local','Admin@123',role='ADMIN',college_id='GCLET-ADMIN')
        for username,role in [('student','STUDENT'),('faculty','FACULTY'),('staff','STAFF')]:
            if not User.objects.filter(username=username).exists():
                user=User.objects.create_user(username=username,password='Demo@1234',role=role,
                    email=f'{username}@gclet.local',college_id=f'GCLET-{username.upper()}')
        categories=[
            ('Rice & Meals','Rice bowls, biryani and complete meals'),
            ('Noodles & Chinese','Noodles and Chinese-style favourites'),
            ('Fast Food','Burgers, sandwiches, fries and pizza'),
            ('Rolls & Momos','Freshly prepared rolls and dumplings'),
            ('Breakfast & Snacks','Breakfast plates and quick snacks'),
            ('Hot Beverages','Tea and coffee served hot'),
            ('Cold Beverages','Chilled drinks, juices and water'),
            ('Desserts','Cakes, Indian sweets and ice cream'),
        ]
        cat_objs={}
        for name,desc in categories:
            cat_objs[name],_=FoodCategory.objects.update_or_create(
                name=name,defaults={'description':desc,'is_active':True})
        foods=[
            ('Steamed Rice','Freshly steamed rice served hot','Rice & Meals',35,True),
            ('Veg Fried Rice','Wok-tossed rice with mixed vegetables','Rice & Meals',90,True),
            ('Egg Fried Rice','Wok-fried rice with egg and spring onion','Rice & Meals',100,False),
            ('Chicken Fried Rice','Wok-fried rice with chicken and vegetables','Rice & Meals',130,False),
            ('Chicken Biryani','Aromatic basmati rice layered with spiced chicken','Rice & Meals',150,False),
            ('Veg Thali','Balanced meal with rice, roti, dal and vegetables','Rice & Meals',85,True),
            ('Egg Thali','Rice, dal, vegetables and seasoned eggs','Rice & Meals',100,False),
            ('Chicken Thali','Rice, chicken curry, dal and seasonal vegetables','Rice & Meals',145,False),
            ('Veg Chowmein','Stir-fried noodles with crisp vegetables','Noodles & Chinese',85,True),
            ('Egg Chowmein','Stir-fried noodles with egg and vegetables','Noodles & Chinese',95,False),
            ('Chicken Chowmein','Noodles wok-tossed with chicken and vegetables','Noodles & Chinese',125,False),
            ('Chilli Chicken','Crispy chicken tossed in a spicy chilli sauce','Noodles & Chinese',150,False),
            ('Veg Manchurian','Vegetable dumplings in a savoury Manchurian sauce','Noodles & Chinese',120,True),
            ('Veg Burger','Vegetable patty with lettuce and house sauce','Fast Food',85,True),
            ('Chicken Burger','Chicken patty burger with fresh salad','Fast Food',120,False),
            ('Veg Sandwich','Grilled sandwich with vegetables and cheese','Fast Food',70,True),
            ('Chicken Sandwich','Grilled chicken sandwich with fresh vegetables','Fast Food',100,False),
            ('French Fries','Golden, seasoned crispy potato fries','Fast Food',65,True),
            ('Veg Pizza','Vegetable pizza topped with cheese','Fast Food',140,True),
            ('Veg Roll','Spiced vegetables wrapped in a soft flatbread','Rolls & Momos',70,True),
            ('Egg Roll','Egg and salad wrapped in a flaky flatbread','Rolls & Momos',80,False),
            ('Chicken Roll','Seasoned chicken wrapped with fresh salad','Rolls & Momos',110,False),
            ('Veg Momos','Steamed vegetable dumplings with chutney','Rolls & Momos',80,True),
            ('Chicken Momos','Steamed chicken dumplings with chutney','Rolls & Momos',100,False),
            ('Samosa','Two crispy potato samosas','Breakfast & Snacks',35,True),
            ('Bread Omelette','Fluffy masala omelette served with toasted bread','Breakfast & Snacks',55,False),
            ('Boiled Eggs','Two boiled eggs lightly seasoned','Breakfast & Snacks',35,False),
            ('Maggi','Hot masala noodles prepared to order','Breakfast & Snacks',45,True),
            ('Aloo Paratha','Stuffed potato paratha served with curd','Breakfast & Snacks',65,True),
            ('Milk Tea','Freshly brewed tea with milk','Hot Beverages',20,True),
            ('Masala Tea','Fresh Indian masala tea','Hot Beverages',25,True),
            ('Black Coffee','Freshly brewed black coffee','Hot Beverages',30,True),
            ('Milk Coffee','Hot coffee prepared with milk','Hot Beverages',35,True),
            ('Cold Coffee','Chilled coffee blended with milk','Cold Beverages',65,True),
            ('Mango Juice','Chilled mango juice','Cold Beverages',50,True),
            ('Lemon Soda','Refreshing lemon soda, sweet or salted','Cold Beverages',30,True),
            ('Packaged Water','Sealed packaged drinking water','Cold Beverages',20,True),
            ('Soft Drinks','Chilled assorted bottled soft drinks','Cold Beverages',35,True),
            ('Chocolate Pastry','Chocolate pastry slice with rich frosting','Desserts',60,True),
            ('Gulab Jamun','Two soft gulab jamun in light syrup','Desserts',40,True),
            ('Vanilla Ice Cream','Chilled vanilla ice cream scoop','Desserts',45,True),
        ]
        for name,description,category,price,vegetarian in foods:
            image=f'food/items/{slugify(name)}.jpg'
            item,created=FoodItem.objects.get_or_create(name=name,defaults={
                'category':cat_objs[category],'description':description,'price':Decimal(price),
                'stock':25,'preparation_time':15,'is_vegetarian':vegetarian,
                'available':True,'featured':name in ('Veg Thali','Chicken Biryani','Veg Burger','Veg Momos'),
                'image':image
            })
            if not created:
                item.category=cat_objs[category]
                item.description=description
                item.is_vegetarian=vegetarian
                item.available=True
                item.image=image
                item.save(update_fields=['category','description','is_vegetarian','available','image','updated_at'])
        FoodItem.objects.filter(name__in=['Paneer Wrap','Idli Sambar','Masala Dosa']).update(available=False)
        FoodCategory.objects.filter(name__in=['Meals','Snacks','Beverages','South Indian']).update(is_active=False)
        for name,start,end in [('Morning',time(9,0),time(10,30)),('Lunch',time(12,30),time(14,30)),('Evening',time(16,0),time(17,30))]:
            PickupSlot.objects.get_or_create(name=name,defaults={'start_time':start,'end_time':end,'capacity':30})
        supplier,_=Supplier.objects.get_or_create(name='Campus Foods Supplier',defaults={'phone':'9876543210','email':'supply@example.com'})
        for name,unit,qty,minimum in [('Rice','kg',50,10),('Flour','kg',30,5),('Milk','litre',40,8),('Vegetables','kg',25,8),('Chicken','kg',15,3)]:
            Ingredient.objects.get_or_create(name=name,defaults={'unit':unit,'quantity':Decimal(str(qty)),'minimum_stock':Decimal(str(minimum)),'supplier':supplier})
        Coupon.objects.get_or_create(code='WELCOME10',defaults={'discount_percent':Decimal('10'),'max_discount':Decimal('100'),'minimum_amount':Decimal('100'),'active':True})
        self.stdout.write(self.style.SUCCESS(
            f'Demo data ready: {FoodCategory.objects.filter(is_active=True).count()} menu categories, '
            f'{FoodItem.objects.filter(available=True).count()} available food items. '
            'Admin: admin / Admin@123; student/faculty/staff: Demo@1234'))
