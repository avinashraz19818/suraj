import sys
sys.stdout.reconfigure(encoding='utf-8')
import asyncio, os
from pyrogram import Client

API_ID = 26526155
API_HASH = "81ab29e846065e128eb479c78ba8c465"

async def main():
    env = {}
    with open('/root/surajfeed/.env') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                env[k] = v
    s = env.get('OWNER_6649173245_SESSION')
    owner = Client('chk_u', api_id=API_ID, api_hash=API_HASH, session_string=s, in_memory=True)
    await owner.start()
    me = await owner.get_me()
    print('Owner ID:', me.id)
    print('Username:', repr(me.username))
    print('First Name:', repr(me.first_name))
    
    # Now check client 2
    c2_s = env.get('CLIENT_2_SESSION')
    c2 = Client('chk_c2', api_id=API_ID, api_hash=API_HASH, session_string=c2_s, in_memory=True)
    await c2.start()
    print('Client 2 ID:', c2.me.id)
    
    # Try resolving owner with username vs ID
    try:
        p1 = await c2.resolve_peer(me.username)
        print('Resolve with username:', p1)
    except Exception as e:
        print('Resolve with username failed:', e)
        
    try:
        p2 = await c2.resolve_peer(f"@{me.username}")
        print('Resolve with @username:', p2)
    except Exception as e:
        print('Resolve with @username failed:', e)

    try:
        p3 = await c2.resolve_peer(me.id)
        print('Resolve with me.id:', p3)
    except Exception as e:
        print('Resolve with me.id failed:', e)

    await owner.stop()
    await c2.stop()

asyncio.run(main())
