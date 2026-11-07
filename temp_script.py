
import os, sys, asyncio
from pyrogram import Client
from dotenv import load_dotenv
load_dotenv('/root/surajfeed/.env')
api_id = int(os.getenv('API_ID', 1234567))
api_hash = os.getenv('API_HASH', 'abcdef')

async def warmup():
    owner = Client('o_warm', api_id=api_id, api_hash=api_hash, session_string=os.getenv('OWNER_6649173245_SESSION'), in_memory=True)
    await owner.start()
    o_me = await owner.get_me()
    print('OWNER ready:', o_me.username)
    
    for i in range(1, 7):
        s = os.getenv(f'CLIENT_{i}_SESSION')
        if s:
            c = Client(f'c_warm_{i}', api_id=api_id, api_hash=api_hash, session_string=s, in_memory=True)
            await c.start()
            c_me = await c.get_me()
            try:
                # Client sends greeting to owner by username
                msg = await c.send_message(o_me.username, "Hii sir")
                print(f"✅ Client {i} -> Owner: message sent (id={msg.id})")
                await asyncio.sleep(1)
                # Now owner replies to client by user id!
                reply = await owner.send_message(c_me.id, "Hello")
                print(f"✅ Owner -> Client {i}: message sent (id={reply.id})")
            except Exception as e:
                print(f"❌ Error for Client {i}: {e}")
            await c.stop()
    await owner.stop()

asyncio.run(warmup())
