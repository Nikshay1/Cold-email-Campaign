import sys
import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Inbox, EmailRecord
from app.config import get_settings
settings = get_settings()

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

async def test():
    with open('output.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Inbox).where(Inbox.email == 'nikshaypookiw@gmail.com'))
            inbox = result.scalar_one_or_none()
            if not inbox:
                print('Inbox not found')
                return
                
            print(f"Testing inbox: {inbox.email}")
        creds = Credentials(
            token=inbox.gmail_access_token,
            refresh_token=inbox.gmail_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        msgs_result = service.users().messages().list(
            userId='me', q='is:unread label:inbox -from:me', maxResults=5
        ).execute()
        
        messages = msgs_result.get('messages', [])
        print(f'Found {len(messages)} unread messages via API query with -from:me')
        
        # Also grab just ANY unread message to see if `-from:me` is the culprit
        all_msgs = service.users().messages().list(userId='me', q='is:unread label:inbox', maxResults=5).execute().get('messages', [])
        print(f'Found {len(all_msgs)} unread messages WITHOUT -from:me')
        
        for msg in all_msgs:
            msg_data = service.users().messages().get(
                userId='me', id=msg['id'], format='full'
            ).execute()
            
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            from_h = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            in_reply_to = next((h['value'] for h in headers if h['name'].lower() == 'in-reply-to'), None)
            
            print(f'\n--- MSG ID {msg["id"]} ---')
            print(f'Subject: {subject}')
            print(f'From: {from_h}')
            print(f'In-Reply-To: {in_reply_to}')
            print(f'ThreadId: {msg_data.get("threadId")}')
            
            if not in_reply_to:
                print(' -> Ignored: No In-Reply-To header')
                continue
            
            # Check DB match
            res = await db.execute(select(EmailRecord).where(
                (EmailRecord.gmail_message_id == in_reply_to) |
                (EmailRecord.gmail_thread_id == msg_data.get('threadId'))
            ))
            email_record = res.scalar_one_or_none()
            if email_record:
                print(f' -> Matched EmailRecord! ID: {email_record.id}')
                print(f'    DB Thread: {email_record.gmail_thread_id}, DB MsgId: {email_record.gmail_message_id}')
            else:
                print(' -> FAILED TO MATCH in DB EmailRecord')

asyncio.run(test())
