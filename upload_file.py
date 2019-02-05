from telethon import TelegramClient
import sys
import asyncio
from config import *

local_file_addr = sys.argv[1]
user_id = sys.argv[2]

async def main():
    client = await TelegramClient(name, api_id, api_hash).start()
    # Now you can use all client methods listed below, like for example...
    await client.send_file(bot_username, local_file_addr, caption=user_id)


asyncio.get_event_loop().run_until_complete(main())
