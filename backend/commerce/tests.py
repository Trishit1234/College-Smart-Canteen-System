from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from catalogue.models import FoodCategory,FoodItem
from commerce.models import Order,PickupSlot
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from decimal import Decimal
from io import StringIO
from django.core.management import call_command
from hashlib import sha256
from django.utils.text import slugify

class CanteenWorkflowTests(TestCase):
    def setUp(self):
        self.client=APIClient()
        self.student=get_user_model().objects.create_user('teststudent',password='Test@1234',role='STUDENT')
        self.staff=get_user_model().objects.create_user('teststaff',password='Test@1234',role='STAFF')
        cat=FoodCategory.objects.create(name='Test Meals')
        self.item=FoodItem.objects.create(category=cat,name='Test Thali',price='80.00',stock=10,available=True)
        PickupSlot.objects.create(name='Lunch',start_time='12:30',end_time='14:30')

    def test_registration_and_login(self):
        response=self.client.post('/api/auth/register/',{'username':'newstudent','password':'Strong@123','role':'STUDENT','college_id':'NEW-1'})
        self.assertEqual(response.status_code,201)
        login=self.client.post('/api/auth/login/',{'username':'newstudent','password':'Strong@123'})
        self.assertEqual(login.status_code,200)
        self.assertIn('access',login.data)

    def test_checkout_status_and_stock_workflow(self):
        self.client.force_authenticate(user=self.student)
        self.assertEqual(self.client.post('/api/cart/add/',{'item':self.item.id,'quantity':2}).status_code,200)
        checkout=self.client.post('/api/checkout/',{'pickup_slot':1,'payment_method':'CASH'})
        self.assertEqual(checkout.status_code,201)
        order_id=checkout.data['id']
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock,8)
        self.client.force_authenticate(user=self.staff)
        self.assertEqual(self.client.post(f'/api/orders/{order_id}/accept/').status_code,200)
        self.assertEqual(self.client.post(f'/api/orders/{order_id}/status/',{'status':'PREPARING'}).status_code,200)
        self.assertEqual(self.client.post(f'/api/orders/{order_id}/status/',{'status':'READY FOR PICKUP'}).status_code,200)
        completed=self.client.post(f'/api/orders/{order_id}/complete/')
        self.assertEqual(completed.status_code,200)
        self.assertEqual(completed.data['status'],'COMPLETED')
        payment=Order.objects.get(pk=order_id).payment
        self.assertEqual(payment.status,'PAID')
        self.assertEqual(payment.transaction_id,f'CASH-{payment.order.number}')
        self.assertIsNotNone(payment.paid_at)
        admin=get_user_model().objects.create_superuser('workflowadmin','workflow@test.local','Test@1234',role='ADMIN')
        self.client.force_authenticate(user=admin)
        analytics=self.client.get('/api/analytics/')
        self.assertEqual(analytics.status_code,200)
        self.assertEqual(Decimal(str(analytics.data['total_revenue'])),Decimal('168'))
        self.assertEqual(Decimal(str(analytics.data['today_revenue'])),Decimal('168'))
        self.client.force_authenticate(user=self.student)
        receipt=self.client.get(f"/api/payments/{payment.id}/receipt/")
        self.assertEqual(receipt.status_code,200)
        self.assertIn('CASH PAYMENT RECEIPT',receipt.content.decode())

    def test_upi_test_payment_stays_pending_until_explicit_confirmation(self):
        self.client.force_authenticate(user=self.student)
        self.client.post('/api/cart/add/',{'item':self.item.id,'quantity':1})
        checkout=self.client.post('/api/checkout/',{'pickup_slot':1,'payment_method':'UPI'})
        self.assertEqual(checkout.status_code,201)
        payment=checkout.data['payment']
        self.assertEqual(payment['status'],'PENDING')
        self.assertTrue(payment['test_mode'])
        confirmed=self.client.post(f"/api/payments/{payment['id']}/confirm-test/")
        self.assertEqual(confirmed.status_code,200)
        self.assertEqual(confirmed.data['status'],'PAID')
        self.assertIn('TEST-',confirmed.data['transaction_id'])
        admin=get_user_model().objects.create_superuser('paymentadmin','payments@test.local','Test@1234',role='ADMIN')
        self.client.force_authenticate(user=admin)
        analytics=self.client.get('/api/analytics/')
        self.assertEqual(analytics.status_code,200)
        self.assertEqual(Decimal(str(analytics.data['total_revenue'])),Decimal('0'))

    def test_demo_payment_uses_database_total_and_is_idempotently_verified(self):
        self.client.force_authenticate(user=self.student)
        self.client.post('/api/cart/add/',{'item':self.item.id,'quantity':1})
        checkout=self.client.post('/api/checkout/',{
            'pickup_slot':1,'payment_method':'UPI','idempotency_key':'checkout-success-1',
        })
        self.assertEqual(checkout.status_code,201)
        order_id=checkout.data['id']
        self.assertEqual(checkout.data['status'],'AWAITING PAYMENT')
        self.assertEqual(Decimal(checkout.data['total']),Decimal('84.00'))

        duplicate_checkout=self.client.post('/api/checkout/',{
            'pickup_slot':1,'payment_method':'UPI','idempotency_key':'checkout-success-1',
        })
        self.assertEqual(duplicate_checkout.status_code,200)
        self.assertEqual(duplicate_checkout.data['id'],order_id)
        self.assertEqual(Order.objects.filter(user=self.student).count(),1)

        started=self.client.post('/api/payments/create-demo-payment/',{
            'order_id':order_id,'method':'CARD','idempotency_key':'payment-success-1',
            'amount':'0.01','card_number':'4242424242424242','cvv':'123',
        })
        self.assertEqual(started.status_code,201,started.data)
        attempt_id=started.data['id']
        self.assertEqual(Decimal(started.data['amount']),Decimal('84.00'))
        self.assertTrue(started.data['transaction_id'].startswith('GCLET-TEST-'))
        self.assertNotIn('card_number',started.data)

        staff=get_user_model().objects.create_user('paymentstaff',password='Test@1234',role='STAFF')
        self.client.force_authenticate(user=staff)
        staff_orders=self.client.get('/api/orders/').data['results']
        self.assertFalse(any(order['id']==order_id for order in staff_orders))

        other_student=get_user_model().objects.create_user('otherstudent',password='Test@1234',role='STUDENT')
        self.client.force_authenticate(user=other_student)
        denied=self.client.post('/api/payments/verify-demo-payment/',{
            'attempt_id':attempt_id,'simulated_result':'SUCCESS',
        })
        self.assertEqual(denied.status_code,404)

        self.client.force_authenticate(user=self.student)
        verified=self.client.post('/api/payments/verify-demo-payment/',{
            'attempt_id':attempt_id,'simulated_result':'SUCCESS',
        })
        self.assertEqual(verified.status_code,200,verified.data)
        self.assertEqual(verified.data['attempt']['status'],'SUCCESS')
        self.assertEqual(verified.data['order_status'],'PENDING')
        self.assertTrue(verified.data['test_mode'])
        self.assertIn('No money was charged',verified.data['attempt']['result_message'])
        self.assertEqual(self.client.post('/api/payments/verify-demo-payment/',{
            'attempt_id':attempt_id,'simulated_result':'FAILED',
        }).data['attempt']['status'],'SUCCESS')

        order=Order.objects.get(pk=order_id)
        self.assertEqual(order.payment.status,'PAID')
        self.assertEqual(order.payment.transaction_id,started.data['transaction_id'])
        self.assertEqual(order.payment.attempts.count(),1)
        retry_started=self.client.post('/api/payments/create-demo-payment/',{
            'order_id':order_id,'method':'UPI','idempotency_key':'payment-success-2',
        })
        self.assertEqual(retry_started.status_code,409)

        staff_orders=self.client.get('/api/orders/').data['results']
        self.assertTrue(any(order['id']==order_id for order in staff_orders))
        admin=get_user_model().objects.create_superuser('paymentsadmin','admin@test.local','Test@1234',role='ADMIN')
        self.client.force_authenticate(user=admin)
        history=self.client.get('/api/payments/history/')
        self.assertEqual(history.status_code,200)
        self.assertEqual(history.data['results'][0]['attempts'][0]['status'],'SUCCESS')

        self.client.force_authenticate(user=self.student)
        receipt=self.client.get(f"/api/payments/{order.payment.id}/receipt/")
        self.assertEqual(receipt.status_code,200)
        self.assertIn('SIMULATED PAYMENT - TEST MODE',receipt.content.decode())

    def test_demo_payment_failure_keeps_order_for_retry_without_duplicate_order(self):
        self.client.force_authenticate(user=self.student)
        self.client.post('/api/cart/add/',{'item':self.item.id,'quantity':1})
        checkout=self.client.post('/api/checkout/',{
            'pickup_slot':1,'payment_method':'UPI','idempotency_key':'checkout-failure-1',
        })
        order_id=checkout.data['id']
        started=self.client.post('/api/payments/create-demo-payment/',{
            'order_id':order_id,'method':'UPI','idempotency_key':'payment-failure-1',
        })
        failed=self.client.post('/api/payments/verify-demo-payment/',{
            'attempt_id':started.data['id'],'simulated_result':'FAILED',
        })
        self.assertEqual(failed.status_code,200)
        self.assertEqual(failed.data['attempt']['status'],'FAILED')
        self.assertEqual(Order.objects.get(pk=order_id).status,'AWAITING PAYMENT')
        self.assertEqual(Order.objects.get(pk=order_id).payment.status,'FAILED')
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock,9)
        self.assertEqual(Order.objects.filter(user=self.student).count(),1)

        retry=self.client.post('/api/payments/create-demo-payment/',{
            'order_id':order_id,'method':'WALLET','idempotency_key':'payment-retry-1',
        })
        self.assertEqual(retry.status_code,201,retry.data)
        succeeded=self.client.post('/api/payments/verify-demo-payment/',{
            'attempt_id':retry.data['id'],'simulated_result':'SUCCESS',
        })
        self.assertEqual(succeeded.status_code,200)
        payment=Order.objects.get(pk=order_id).payment
        self.assertEqual(payment.status,'PAID')
        self.assertEqual(payment.attempts.count(),2)
        self.assertEqual(list(payment.attempts.order_by('created_at').values_list('status',flat=True)),['FAILED','SUCCESS'])
        self.assertEqual(Order.objects.filter(user=self.student).count(),1)

    def test_admin_can_create_food_with_uploaded_image_and_students_cannot(self):
        output=BytesIO()
        Image.new('RGB',(16,16),color='orange').save(output,format='JPEG')
        image=SimpleUploadedFile('new-food.jpg',output.getvalue(),content_type='image/jpeg')
        self.client.force_authenticate(user=self.student)
        denied=self.client.post('/api/food/',{'name':'Denied item','category':self.item.category_id,'price':'20','image':image})
        self.assertEqual(denied.status_code,403)
        admin=get_user_model().objects.create_superuser('catalogadmin','admin@test.local','Test@1234',role='ADMIN')
        self.client.force_authenticate(user=admin)
        output.seek(0)
        image=SimpleUploadedFile('new-food.jpg',output.getvalue(),content_type='image/jpeg')
        def cleanup_uploaded_image():
            item=FoodItem.objects.filter(name='Uploaded item').first()
            if item and item.image:
                item.image.delete(save=False)
        self.addCleanup(cleanup_uploaded_image)
        created=self.client.post('/api/food/',{'name':'Uploaded item','description':'Freshly uploaded','category':self.item.category_id,'price':'20.00','discounted_price':'','stock':'3','image':image},format='multipart')
        self.assertEqual(created.status_code,201,created.data)
        self.assertIn('food/',created.data['image'])

    def test_seed_demo_loads_the_complete_categorized_menu_with_images(self):
        call_command('seed_demo',stdout=StringIO())
        expected={
            'Steamed Rice','Veg Fried Rice','Egg Fried Rice','Chicken Fried Rice','Chicken Biryani','Veg Thali','Egg Thali','Chicken Thali',
            'Veg Chowmein','Egg Chowmein','Chicken Chowmein','Chilli Chicken','Veg Manchurian',
            'Veg Burger','Chicken Burger','Veg Sandwich','Chicken Sandwich','French Fries','Veg Pizza',
            'Veg Roll','Egg Roll','Chicken Roll','Veg Momos','Chicken Momos',
            'Samosa','Bread Omelette','Boiled Eggs','Maggi','Aloo Paratha',
            'Milk Tea','Masala Tea','Black Coffee','Milk Coffee',
            'Cold Coffee','Mango Juice','Lemon Soda','Packaged Water','Soft Drinks',
            'Chocolate Pastry','Gulab Jamun','Vanilla Ice Cream',
        }
        seeded=FoodItem.objects.filter(category__name__in=[
            'Rice & Meals','Noodles & Chinese','Fast Food','Rolls & Momos',
            'Breakfast & Snacks','Hot Beverages','Cold Beverages','Desserts',
        ],available=True).select_related('category')
        self.assertEqual(set(seeded.values_list('name',flat=True)),expected)
        self.assertEqual(seeded.count(),41)
        self.assertTrue(all(item.image and item.image.storage.exists(item.image.name) for item in seeded))
        self.assertTrue(all(item.image.name == f'food/items/{slugify(item.name)}.jpg' for item in seeded))
        self.assertEqual(len({item.image.name for item in seeded}),41)
        image_hashes=[]
        for item in seeded:
            with item.image.open('rb') as image_file:
                image_hashes.append(sha256(image_file.read()).hexdigest())
        self.assertEqual(len(set(image_hashes)),41)
        self.assertEqual(set(seeded.values_list('category__name',flat=True)),{
            'Rice & Meals','Noodles & Chinese','Fast Food','Rolls & Momos',
            'Breakfast & Snacks','Hot Beverages','Cold Beverages','Desserts',
        })
        self.assertFalse(FoodItem.objects.filter(name__in=['Paneer Wrap','Idli Sambar','Masala Dosa'],available=True).exists())
