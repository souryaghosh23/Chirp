from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from root import settings

from .views import VerifyView, VerifyOtp, EntryDetails, twilio_service,logout_function
from chat.views import ChatRoomView, DashboardView,AddContactView, ContactSearchView, StartChatView, ChatInfo, leave_group, add_members_group, delete_chat, make_admin

urlpatterns = [
    path('auth', VerifyView.as_view(),name='register'),
    path('logout/',logout_function,name='logout'),
    path('auth/verify_otp/',VerifyOtp.as_view(),name='verify_otp'),
    path('profile/',EntryDetails.as_view(),name='entry_profile'),
    path('dashboard/', DashboardView.as_view(),name='dashboard'),
    path('profile/<int:room_id>/',ChatInfo.as_view(),name='chat_info'),
    path('delete-chat/<int:room_id>/',delete_chat,name='delete_chat'),
    path('make-admin/<int:room_id>/<int:user_id>/',make_admin,name='make_admin'),
    path('addcontact/',AddContactView.as_view(),name='add_contact'),
    path("contacts/search/", ContactSearchView.as_view(), name="contact-search"),
    path("start-chat/",StartChatView.as_view(),name='start_chat'),
    path("chat/<int:room_id>/", ChatRoomView.as_view(), name="chat_room"),
    path('auth/resend-otp',twilio_service,name='resend_otp'),
    path('leave-group/<int:room_id>/', leave_group,name='leave_group'),
    path('add-members/<int:room_id>/', add_members_group,name='add_memebers'),
]+ static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

