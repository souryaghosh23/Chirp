from django.db import models
from django.db.models import TextField, CharField, DateTimeField, ForeignKey, BooleanField, CASCADE, DO_NOTHING
from root.settings import AUTH_USER_MODEL

# Create your models here.

class ChatRoom(models.Model):
    room_type=[
        ('private','Private'),
        ('group','Group')
    ]
    room_type=CharField('Room Type',choices=room_type)
    room_name=CharField('Room Name',blank=False,null=False)
    image=models.ImageField('Image',upload_to='group_image/',null=True,blank=True)
    description=TextField('Description',blank=True,null=True)
    created_by=ForeignKey(AUTH_USER_MODEL,on_delete=DO_NOTHING)
    created_at=DateTimeField('Created On',auto_now_add=True)
    private_key=CharField(max_length=255,null=True,blank=True,unique=True)
    last_message = models.TextField(null=True, blank=True)
    last_message_time = models.DateTimeField(null=True, blank=True)
    
    
class Messages(models.Model):
    sender = ForeignKey(AUTH_USER_MODEL,on_delete=CASCADE,related_name='message_send')
    room_name = ForeignKey(ChatRoom,on_delete=CASCADE,related_name='message_room')
    chats = TextField()
    created_at = DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)    
    is_deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.room_name} : {self.chats[:20]}"
    
    
class RoomParticipants(models.Model):
    room=ForeignKey(ChatRoom,on_delete=CASCADE,related_name='room')
    user=ForeignKey(AUTH_USER_MODEL,on_delete=DO_NOTHING,related_name='room_user')
    is_admin=BooleanField('Admin',blank=True,null=True)
    created_at=DateTimeField('Created On',auto_now_add=True)
    


    
    
    