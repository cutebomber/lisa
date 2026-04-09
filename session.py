"""
Session String Generator
Run this once to get your session string, then paste it into telegram_userbot.py
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID   = int(input("Enter API_ID   : "))
API_HASH = input("Enter API_HASH : ").strip()

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\n✅ Your session string (keep this secret!):\n")
    print(client.session.save())
