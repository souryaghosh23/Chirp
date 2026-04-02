from django.db import models
from django.db.models import ForeignKey, DateTimeField, CharField, CASCADE

from accounts.models import CustomUser

# Create your models here.
class Contacts(models.Model):
    user=ForeignKey(CustomUser,on_delete=CASCADE,blank=False,null=False,related_name='contact_user')
    contact=ForeignKey(CustomUser,on_delete=CASCADE,blank=False,null=False,related_name='my_contacts')
    pet_name=CharField(max_length=200,null=True,blank=True)
    created_by=DateTimeField('Created By',auto_now_add=True)
    
    class Meta:
        unique_together = ("user", "contact")