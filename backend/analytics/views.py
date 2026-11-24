from django.shortcuts import render

# Create your views here.
from django.db.models import Sum,Count,Q,F
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncHour,TruncDate
from django.utils import timezone
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.views import IsAdmin
from commerce.models import Order,Payment
from accounts.models import User
from catalogue.models import FoodItem,FoodCategory
from inventory.models import Ingredient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import csv

class AnalyticsView(APIView):
    permission_classes=[IsAdmin]
    def get(self,request):
        today=timezone.localdate()
        paid=Payment.objects.filter(status='PAID').filter(
            Q(method='CASH') | Q(method='UPI',test_mode=False)
        )
        orders=Order.objects.exclude(status=Order.Status.AWAITING_PAYMENT)
        total_revenue=paid.aggregate(v=Sum('amount'))['v'] or 0
        today_revenue=paid.annotate(paid_on=Coalesce('paid_at','created_at')).filter(paid_on__date=today).aggregate(v=Sum('amount'))['v'] or 0
        popular=list(orders.filter(status='COMPLETED').values('items__name').annotate(count=Count('items')).order_by('-count')[:5])
        hourly=list(orders.annotate(hour=TruncHour('created_at')).values('hour').annotate(count=Count('id')).order_by('hour')[:24])
        return Response({
            'total_revenue':total_revenue,
            'today_revenue':today_revenue,
            'total_orders':orders.count(),
            'pending_orders':orders.filter(status__in=['PENDING','CONFIRMED','PREPARING']).count(),
            'completed_orders':orders.filter(status='COMPLETED').count(),
            'cancelled_orders':orders.filter(status='CANCELLED').count(),
            'registered_users':User.objects.count(),
            'popular_items':popular,
            'peak_hours':hourly,
            'low_stock':[
                {'name':i.name,'quantity':str(i.quantity),'minimum':str(i.minimum_stock)}
                for i in Ingredient.objects.filter(quantity__lte=F('minimum_stock'))
            ],
        })
class ReportView(APIView):
    permission_classes=[IsAdmin]
    def get(self,request,kind):
        fmt=request.query_params.get('format','csv')
        if kind=='sales':
            rows=list(Payment.objects.filter(status='PAID').filter(
                Q(method='CASH') | Q(method='UPI',test_mode=False)
            ).annotate(paid_on=Coalesce('paid_at','created_at')).values_list('order__number','amount','status','paid_on'))
            headers=['Order','Amount','Status','Date']
        elif kind=='inventory':
            rows=list(Ingredient.objects.values_list('name','quantity','unit','minimum_stock'))
            headers=['Ingredient','Quantity','Unit','Minimum']
        else:
            rows=list(Order.objects.values_list('number','status','total','created_at'))
            headers=['Order','Status','Total','Date']
        if fmt=='pdf':
            response=HttpResponse(content_type='application/pdf')
            response['Content-Disposition']=f'attachment; filename="{kind}-report.pdf"'
            p=canvas.Canvas(response,pagesize=A4)
            p.drawString(40,800,f'GCLET Canteen - {kind.title()} Report')
            y=760
            for row in [headers,*rows][:50]:
                p.drawString(40,y,' | '.join(str(v) for v in row))
                y-=18
            p.save()
            return response
        response=HttpResponse(content_type='text/csv')
        response['Content-Disposition']=f'attachment; filename="{kind}-report.csv"'
        writer=csv.writer(response)
        writer.writerow(headers)
        writer.writerows(rows)
        return response
