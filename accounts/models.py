from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.utils import timezone

from .manager import CustomUserManager

class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(max_length=15, unique=True)#Is this going to be blank=False??
    username = models.CharField(max_length=150, blank=True)
    full_name = models.CharField(max_length=255)
    description=models.CharField(max_length=1000, default='Available')
    profile_picture=models.ImageField('Profile Photo',upload_to="profile_pictures/")
    is_profile_complete = models.BooleanField(default=False)
    current_otp=models.IntegerField(blank=True,null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone
    
class OTPverification(models.Model):
    phone=models.CharField(max_length=12,null=False,blank=False)
    otp_hash=models.CharField(max_length=2000,blank=True,null=True)
    attempt_count=models.IntegerField(default=0)
    resend_count=models.IntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)