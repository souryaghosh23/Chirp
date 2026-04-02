from django.contrib import admin

from .models import Messages, ChatRoom, RoomParticipants
# Register your models here.
admin.site.register([Messages,RoomParticipants, ChatRoom])