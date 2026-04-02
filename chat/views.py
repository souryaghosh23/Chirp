from django.shortcuts import render, get_list_or_404, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import JsonResponse
from django.utils import timezone

from .models import RoomParticipants, ChatRoom, Messages
from contacts.models import Contacts
from accounts.models import CustomUser

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

class DashboardView(LoginRequiredMixin,View):
    template_name='chats/dashboard.html'
    def get(self,request,*args,**kwargs):
        if not request.user.is_authenticated:
            return redirect('register')
        
        current_user=request.user
        rooms_data=[]
        
        participants=RoomParticipants.objects.filter(user=current_user).select_related('room')
        for p in participants:
            room=p.room
            
            if room.room_type=='private':
                other_user=RoomParticipants.objects.filter(
                    room=room
                ).exclude(user=current_user).first()
                
                if other_user:
                    contact=Contacts.objects.filter(user=current_user,contact_id=other_user.user.id).first()
                    display_name=contact.pet_name if contact else other_user.user.username

                last_message=room.last_message
                last_message_time=room.last_message_time
                profile_picture = (
                    other_user.user.profile_picture.url
                    if other_user and other_user.user.profile_picture
                    else None
                )           
            else:
                display_name=room.room_name
                last_message=room.last_message
                last_message_time=room.last_message_time
                profile_picture=room.image.url if room.image else None
            
            rooms_data.append({
                'room_id':room.id,
                'name':display_name,
                'last_message':last_message,
                'profile_photo':profile_picture,
                'last_message_time':last_message_time
            })
        rooms_data.sort(
                key=lambda x: x['last_message_time'] or timezone.make_aware(datetime.min),
                reverse=True
            )

        context={
            'rooms':rooms_data
        }
        return render(request,self.template_name,context)


class StartChatView(LoginRequiredMixin,View):
    def get(self,request,*args,**kwargs):
        return redirect('dashboard')
    def post(self,request,*args,**kwargs):
        contact_ids=request.POST.getlist('contact_ids[]')
        group_name=request.POST.get('group_name')
        is_group = request.POST.get("is_group")=='true'
        current_user=request.user
        
        user_ids=set(map(int,contact_ids))
        user_ids.add(current_user.id)
        
        if len(user_ids) > 10:
            messages.error(request,message='You have selected more than 10 users.')
            logging.error(msg='User selected more than 10 chat members.')
            return ('dashboard')
        
        if not is_group:
            
            u1,u2 = list(user_ids)
            private_key=self.generate_private_key(u1,u2)
            
            room = ChatRoom.objects.filter(private_key=private_key).first()
            
            if room:
                return JsonResponse({'room_id':room.id})
            
            new_room=ChatRoom.objects.create(
                room_type='private',
                private_key = private_key,
                created_by = current_user
            )
            
            p = RoomParticipants.objects.bulk_create([
                RoomParticipants(room=new_room,user_id=u1),
                RoomParticipants(room=new_room,user_id=u2)
            ])

            return JsonResponse({'room_id': new_room.id})
        else:
            group_room=ChatRoom.objects.create(
                room_type='group',
                room_name=group_name,
                created_by=current_user,
            )
            
            RoomParticipants.objects.bulk_create([
                RoomParticipants(room=group_room,user_id=uid,is_admin=(uid == current_user.id)) for uid in user_ids
            ])
            
            Messages.objects.create(
                room_name=group_room,
                chats=f"{current_user.username} created the group",
                sender=current_user,
            )
            
            users = CustomUser.objects.filter(id__in=user_ids).values("id", "username")
            user_map = {u["id"]: u["username"] for u in users}

            channel_layer = get_channel_layer()

            for uid in user_ids:
                async_to_sync(channel_layer.group_send)(
                    f"user_{uid}",
                    {
                        "type": "sidebar_update",
                        "room_id": group_room.id,
                        "message": "Group created",
                        "timestamp": str(timezone.now()),
                        "name": group_name   # 🔥 IMPORTANT
                    }
                )
            
            return JsonResponse({'room_id':group_room.id})
                
    def generate_private_key(self,user1,user2):
            return f"{min(user1,user2)}_{max(user1,user2)}"
        
class ChatInfo(LoginRequiredMixin, View):
    template_name = 'chats/profile.html'

    def get(self, request, room_id):

        room = ChatRoom.objects.filter(id=room_id).first()
        if not room:
            return redirect('dashboard')

        # 🔥 ADMIN CHECK (cheap query)
        is_admin = RoomParticipants.objects.filter(
            room=room,
            user=request.user,
            is_admin=True
        ).exists()

        context = {
            "room": room,
            "type": room.room_type,
            "is_admin": is_admin
        }

        # ================= PRIVATE =================
        if room.room_type == "private":

            participant = RoomParticipants.objects.filter(
                room=room
            ).exclude(user=request.user).select_related("user").first()

            other_user = participant.user if participant else None

            contact = Contacts.objects.filter(
                user=request.user,
                contact=other_user
            ).only("pet_name").first()

            display_name = (
                contact.pet_name if contact and contact.pet_name
                else other_user.username if other_user else "Unknown"
            )

            context["display_name"] = display_name
            context['other_user'] = other_user

        # ================= GROUP =================
        else:

            participants = RoomParticipants.objects.filter(
                room=room
            ).select_related("user")

            user_ids = participants.values_list("user_id", flat=True)

            contacts = Contacts.objects.filter(
                user=request.user,
                contact_id__in=user_ids
            ).only("contact_id", "pet_name")

            contact_map = {
                c.contact_id: c.pet_name
                for c in contacts
            }

            members = [
                {
                    "id": p.user.id,
                    "name": contact_map.get(p.user.id, p.user.username),
                    "is_admin": p.is_admin,
                    "profile_picture": p.user.profile_picture.url if p.user.profile_picture else None
                }
                for p in participants
            ]

            context["members"] = members

        return render(request, self.template_name, context)
    
    def post(self, request, room_id):
        room=ChatRoom.objects.get(id=room_id)
        if not room:
            return redirect('dashboard')
        
        description=request.POST.get('description')
        if description is not None:
            room.description = description
        photo=request.FILES.get('image')
        if photo:
            room.image=photo
        
        room.save()
        return redirect(f'/profile/{room_id}')

@login_required(redirect_field_name='register')
@require_POST
def make_admin(request,room_id,user_id):
    room=ChatRoom.objects.get(id=room_id)
    if not room_id:
        messages.error(request,message='The room does not exist!')
        return redirect('dashboard')
    
    user=RoomParticipants.objects.get(room=room,user=user_id)
    if user.is_admin:
        user.is_admin=False
        user.save()
        return redirect(f'/profile/{room_id}')
    
    admin_count=RoomParticipants.objects.filter(room=room,is_admin=True).count()
    if admin_count >= 2:
        messages.info(request,message='You can add upto 2 admins per room. Remove one to add another.')
        return redirect(f'/profile/{room_id}')
    
    user.is_admin =True
    user.save()
    return redirect(f'/profile/{room_id}')     

@login_required(redirect_field_name='register')
@require_POST
def add_members_group(request, room_id):
    room = ChatRoom.objects.get(id=room_id)
    is_admin = RoomParticipants.objects.filter(room=room,user=request.user,is_admin=True).exists()
    if not is_admin:
        messages.error(request,message='You do not have the permission to add users into this group')
        return redirect('#')
    
    ids_str = request.POST.get("contact_ids", "")
    new_ids = [int(i) for i in ids_str.split(",") if i] 
       
    existing_ids=set(RoomParticipants.objects.filter(room=room).values_list('user_id',flat=True))
    
    to_add = [
        RoomParticipants(room=room,user_id=uid)
        for uid in new_ids
        if int(uid) not in existing_ids
    ]
    
    if len(existing_ids) + len(to_add) > 10:
        messages.error(request,message='You cannot add more than 10 particpants per group')
        return redirect(f'profile/{room_id}')
    
    RoomParticipants.objects.bulk_create(to_add)
    
    return redirect(f'/profile/{room_id}')

@login_required(redirect_field_name='register')
@require_POST
def leave_group(request,room_id):
    room=ChatRoom.objects.get(id=room_id)
    participant=RoomParticipants.objects.filter(room=room,user=request.user).first()
    
    if not participant:
        messages.error(request,message='You cannot leave the group. As your not in it')
        return redirect('dashboard')
    
    if participant.is_admin:
        admin_count=RoomParticipants.objects.filter(room=room,is_admin=True).count()
        if admin_count <= 1:
            messages.error(request,message='Please appoint a admin before you leave the group')
            return redirect('dashboard')
    
    participant.delete()
    messages.success(request,message='You have successfully left the group')
    return redirect('dashboard')

@login_required(redirect_field_name='register')
@require_POST
def delete_chat(request,room_id):
    room=ChatRoom.objects.get(id=room_id)
    if room:
        room.delete()
        messages.success(request,message='Chat deleted successfullt')
        return redirect('dashboard')
    
@method_decorator(login_required,name='dispatch')
class ChatRoomView(LoginRequiredMixin, View):

    def get(self, request, room_id):
        return render(
            request,
            "chats/chat.html",
            {
                "room_id": room_id
            }
        )
        
class AddContactView(LoginRequiredMixin,View):
    def post(self, request, *args, **kwargs):
        
        petname=request.POST.get('contact_name')
        phone=request.POST.get('phone')
        
        user_contact=CustomUser.objects.filter(phone=phone).first()
        if not user_contact:
            messages.error(request,message='The User is not on Chirp.')
            logging.error(msg=f'Cannot create the contact, as the user isnt on Chirp.')
            return redirect('dashboard')
        
        try:
            contact_identity,status=Contacts.objects.get_or_create(user=request.user,contact=user_contact)
            contact_identity.pet_name=petname
            contact_identity.save()
            #You need to handle the case where the phone number already exists.
        except Exception as e:
            logging.error(msg=f'Error fetching or creating the contact related to the user,{str(e)}.')
            messages.error(request,message='Couldn\'t add the contact, unfortunately.')
            return redirect('dashboard')
        
        # if status:
        #     return redirect('#')
        messages.success(request,message='Contact added successfully. Search your phonebook to chat.')
        return redirect('dashboard')

class ContactSearchView(LoginRequiredMixin,View):
    def get(self,request,*args,**kwargs):
        
        query=request.GET.get('q','')
        
        contacts=Contacts.objects.filter(user=request.user).filter(Q(pet_name__icontains=query))[:10]
        
        results = []
        
        for c in contacts:
            results.append({
                'id':c.contact.id,
                "name": c.pet_name,
                "phone": c.contact.phone,
            })
            
        return JsonResponse({
            "contacts": results
        })

@csrf_exempt
@require_POST
@login_required(redirect_field_name='register')
def delete_message(request):
    data = request.POST.get('body')

    msg_id = data.get("message_id")
    user = request.user

    try:
        msg = Messages.objects.get(id=msg_id)

        # 🔥 IMPORTANT: only sender can delete
        if msg.sender != user:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        msg.is_deleted = True
        msg.save()

        return JsonResponse({"status": "deleted", "message_id": msg_id})

    except Messages.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

        
        