import json
import logging, asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from datetime import datetime
from .models import Messages, RoomParticipants, ChatRoom

logger = logging.getLogger(__name__)

class Chatconsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f'chat_{self.room_id}'
        self.user_group=f"user_{self.scope['user'].id}"
        user = self.scope['user']

        if user.is_anonymous:
            await self.close()
            return

        is_member = await self.check_room_membership(user.id, self.room_id)
        
        if not is_member:
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        await self.transform_message_state(user.id,self.room_id)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "seen_bulk",
                "user_id": user.id,
                "room_id": self.room_id
            }
        )
        
        room = await self.get_room(self.room_id)
        self.room_type = room.room_type
        
        await self.channel_layer.group_add(
            f"active_room_{self.room_id}",
            self.channel_name
        )

        # ✅ Load old messages safely
        old_messages = await self.get_old_messages(self.room_id)

        for msg in old_messages:
            await self.send(text_data=json.dumps({
                "type": "chat",
                'is_deleted':msg['is_deleted'],
                "message": msg['messages'],
                "sender": msg['sender'],
                'room_type':self.room_type,
                "timestamp": msg['timestamp'],
                'message_id':msg['message_id']
            }))

        # ✅ Only notify for GROUP chats
        room = await self.get_room(self.room_id)

        # if room.room_type == "group":
        #     await self.channel_layer.group_send(
        #         self.group_name,
        #         {
        #             "type": "new_user",
        #             "user": user.username
        #         }
        #     )


    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            f"active_room_{self.room_id}",
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        # ✅ Directly broadcast raw message
        if text_data:
            data = json.loads(text_data)  # ✅ Parse once
            message = data.get('message')
            msg_type = data.get("type")
            user=self.scope['user'] 
            
            if msg_type is None:
                if not message:
                    return
            
            room = await self.get_room(self.room_id)
            self.room_type = room.room_type
            
            if msg_type == "delete":
                message_id = data.get("message_id")

                success=await self.delete_message(message_id,user.id)
                
                if not success:
                    return
                
                await self.update_last_message(self.room_id)
                room = await self.get_room(self.room_id)
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "delete_message_event",
                        "message_id": message_id
                    }
                )
                participants = await self.get_room_participants(self.room_id)

                tasks = [
                    self.channel_layer.group_send(
                        f"user_{uid}",
                        {
                            "type": "sidebar_delete",
                            "room_id": self.room_id,
                            "message": room.last_message or "No messages yet"
                        }
                    )
                    for uid in participants
                ]

                await asyncio.gather(*tasks)
                return
                            
            if msg_type == "typing":
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "typing_event",
                        "user": self.scope["user"].username
                    }
                )
                return

            if msg_type == "stop_typing":
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "stop_typing_event",
                        "user": self.scope["user"].username
                    }
                )
                return

            msg= await self.save_message(self.room_id, user.id,message) 
            message_id=msg['message'] 
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender':user.username,
                    'room_type':self.room_type,
                    'timestamp':msg['timestamp'],
                    'is_seen': False,
                    'room_id': self.room_id,
                    'message_id':message_id.id
                }
            )
            asyncio.create_task(self.delayed_mark_seen(user.id, message_id.id))
            asyncio.create_task(self.send_sidebar_updates(message, msg['timestamp']))

    async def send_sidebar_updates(self, message, timestamp):
        participants = await self.get_room_participants(self.room_id)
        room = await self.get_room(self.room_id)
        
        await asyncio.gather(*[
            self.channel_layer.group_send(
                f"user_{uid}",
                {
                    "type": "sidebar_update",
                    "room_id": self.room_id,
                    "message": message,
                    "timestamp": timestamp,
                    "name": room.room_name if room.room_type == "group" else None

                }
            )
            for uid in participants
        ])
    async def delayed_mark_seen(self, sender_id, message_id):
        await asyncio.sleep(0.05)  # 🔥 THIS FIXES REAL-TIME

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "mark_seen",
                "room_id": self.room_id,
                "sender_id": sender_id,
                "message_id": message_id
            }
        )
    async def sidebar_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "sidebar",
            "room_id": event["room_id"],
            "message": event["message"],
            "timestamp": event["timestamp"]
        }))
        

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat",
            "message": event["message"],
            "sender": event["sender"],
            'room_type':event['room_type'],
            'timestamp':event['timestamp'],
            'is_seen': event['is_seen'],
            'room_id':event['room_id'],
            'message_id':event['message_id']
        }))


    async def new_user(self, event):
        await self.send(text_data=json.dumps({
            "type": "info",
            "message": f"{event['user']} joined the chat"
        }))
        
    async def typing_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "typing",
            "user": event["user"]
        }))

    async def stop_typing_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "stop_typing",
            "user": event["user"]
        }))
        
    async def delete_message_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "delete",
            "message_id": event["message_id"]
        }))
        
    async def mark_seen(self, event):
        user = self.scope["user"]

        # don't mark sender's own messages
        if user.id == event["sender_id"]:
            return

        # mark messages as seen
        await self.transform_message_state(user.id, event["room_id"])

        # notify sender → ticks turn blue
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "seen_update",
                "room_id": event["room_id"],
                "message_id":event["message_id"]
            }
        )
    async def seen_bulk(self, event):
        await self.send(text_data=json.dumps({
            "type": "seen_bulk",
            "room_id": event["room_id"]
        }))
    async def seen_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "seen",
            "room_id": event["room_id"],
            "message_id":event["message_id"]
        }))
    
    @sync_to_async
    def get_room_participants(self, room_id):
        return list(
            RoomParticipants.objects.filter(room_id=room_id)
            .values_list("user_id", flat=True)
        )
    @sync_to_async
    def delete_message(self, message_id, user_id):
        try:
            msg = Messages.objects.get(id=message_id)
            if msg.sender_id != user_id:
                return False
            if msg.is_deleted:
                return False
            msg.is_deleted = True
            msg.save()
            
            return True
        except Exception as e:
            logging.error(f"Couldn't delete a message because,{str(e)}")
            return False

    @sync_to_async
    def update_last_message(self, room_id):
        last_msg = (
            Messages.objects
            .filter(room_name_id=room_id, is_deleted=False)
            .order_by('-created_at')
            .first()
        )

        room = ChatRoom.objects.get(id=room_id)

        if last_msg:
            room.last_message = last_msg.chats
            room.last_message_time = last_msg.created_at
        else:
            room.last_message = "No messages yet"
            room.last_message_time = None

        room.save()
        
    @sync_to_async
    def get_room(self, room_id):
        return ChatRoom.objects.get(id=room_id)

    @sync_to_async
    def check_room_membership(self,user_id,room_id):
        return RoomParticipants.objects.filter(room_id=room_id,user_id=user_id).exists()
    
    @sync_to_async
    def transform_message_state(self,user_id,room_id):
        messages=Messages.objects.filter(room_name_id=room_id).exclude(sender_id=user_id).update(is_seen=True)
        
    @sync_to_async
    def get_old_messages(self, room_id):
        messages=(
            Messages.objects.filter(room_name_id=room_id).select_related('sender').order_by('-created_at')[:50]
        )
        return [{
            'messages': msg.chats,
            'is_deleted':msg.is_deleted,
            'sender':msg.sender.username,
            'timestamp':str(msg.created_at),
            'is_seen':msg.is_seen,
            'message_id':msg.id
        } for msg in messages][::-1]
        
    @sync_to_async
    def save_message(self, room_id, user_id, message):
        try:
            chatroom=ChatRoom.objects.get(id=room_id)
        except Exception as e:
            logger.error(msg="Couldn't save the message to last message.")
        message_object= Messages.objects.create(
            room_name_id=room_id,
            chats=message,
            sender_id=user_id,
        )
        chatroom.last_message=message
        chatroom.last_message_time=message_object.created_at
        chatroom.save()
        return {'message':message_object,'timestamp':str(message_object.created_at)}
    
        
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        if user.is_anonymous:
            await self.close()
            return

        self.user_group = f"user_{user.id}"

        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_group,
            self.channel_name
        )

    async def sidebar_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "sidebar",
            "room_id": event["room_id"],
            "message": event["message"],
            "timestamp": event["timestamp"],
            "name": event.get("name")   # ✅ ADD THIS

        }))
    async def sidebar_delete(self, event):
        await self.send(text_data=json.dumps({
            "type": "sidebar_delete",
            "room_id": event["room_id"],
            "message": event["message"]
        }))
    async def seen_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "seen",
            "room_id": event["room_id"],
            "message_id":event['message_id']
        }))
        