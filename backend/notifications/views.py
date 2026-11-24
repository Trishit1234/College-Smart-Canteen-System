from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model=Notification
        fields='__all__'
        read_only_fields=['user']

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=NotificationSerializer
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    @action(detail=False,methods=['post'])
    def read_all(self,request):
        self.get_queryset().update(read=True)
        return Response({'detail':'All notifications marked read.'})
