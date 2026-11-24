from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings

class Notification(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,related_name='notifications',on_delete=models.CASCADE)
    title=models.CharField(max_length=150)
    message=models.TextField()
    kind=models.CharField(max_length=30,default='ORDER')
    read=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
