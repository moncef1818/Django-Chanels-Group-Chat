import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # send last 30 messages to the user who just joined
        messages = await self.get_last_messages()
        for msg in messages:
            await self.send(text_data=json.dumps({
                'message': msg.content,
                'username': msg.username,
                'timestamp': msg.created_at.strftime('%H:%M'),
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        # check if it's a "load more" request
        if data.get('type') == 'load_more':
            messages = await self.get_messages_before(data['oldest_id'])
            await self.send(text_data=json.dumps({
                'type': 'history',
                'messages': [
                    {
                        'id': msg.id,
                        'message': msg.content,
                        'username': msg.username,
                        'timestamp': msg.created_at.strftime('%H:%M'),
                    } for msg in messages
                ]
            }))
            return

        message = data['message']
        username = data['username']

        # save to database
        msg = await self.save_message(username, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'timestamp': msg.created_at.strftime('%H:%M'),
                'id': msg.id,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def get_last_messages(self):
        room, _ = Room.objects.get_or_create(name=self.room_name)
        return list(room.messages.order_by('-created_at')[:30])[::-1]

    @database_sync_to_async
    def get_messages_before(self, oldest_id):
        room, _ = Room.objects.get_or_create(name=self.room_name)
        return list(room.messages.filter(id__lt=oldest_id).order_by('-created_at')[:30])[::-1]

    @database_sync_to_async
    def save_message(self, username, content):
        room, _ = Room.objects.get_or_create(name=self.room_name)
        return Message.objects.create(room=room, username=username, content=content)