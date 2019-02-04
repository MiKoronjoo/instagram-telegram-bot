from telethon import TelegramClient
import sys
import asyncio

api_id = 509628
api_hash = '181804b2ffa7bdc89c0cd66e95916650'
name = 'session_name'
bot_username = 'test4everbot'

local_file_addr = sys.argv[1]
user_id = sys.argv[2]

async def main():
    client = await TelegramClient(name, api_id, api_hash).start()
    # Now you can use all client methods listed below, like for example...
    await client.send_file(bot_username, local_file_addr, caption=user_id)


asyncio.get_event_loop().run_until_complete(main())
