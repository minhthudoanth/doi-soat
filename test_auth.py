import os
import sys

# Ensure UTF-8
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import asyncio
from telethon import TelegramClient
from config import API_ID, API_HASH, SESSION_NAME

async def check():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    is_auth = await client.is_user_authorized()
    print("IS_AUTHORIZED:", is_auth, flush=True)
    if is_auth:
        me = await client.get_me()
        print(f"Logged in as: {me.id} - {me.first_name} {getattr(me, 'last_name', '')}", flush=True)
        dialogs = await client.get_dialogs(limit=20)
        print(f"Total dialogs loaded: {len(dialogs)}", flush=True)
        for d in dialogs:
            print(f"- [{d.id}] {d.title or d.name} (is_group={d.is_group}, is_channel={d.is_channel})", flush=True)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(check())
