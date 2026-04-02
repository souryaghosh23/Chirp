from django.urls import re_path
from .consumers import Chatconsumer, NotificationConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_id>\d+)/$',Chatconsumer.as_asgi()),
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi())
]