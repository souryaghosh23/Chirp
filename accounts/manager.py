from django.contrib.auth.models import (
    BaseUserManager
)

class CustomUserManager(BaseUserManager):

    def create_user(self, phone, username=None, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")

        phone = self.normalize_email(phone)  # just normalizing format
        user = self.model(
            phone=phone,
            username=username,
            **extra_fields
        )

        user.set_password(password)  # 🔐 hashes using make_password
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(phone, password=password, **extra_fields)
