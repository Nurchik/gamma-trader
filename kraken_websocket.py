import websockets
import asyncio
import json


async def kraken_ws():
    async with websockets.connect("wss://ws-sandbox.kraken.com") as websocket:
        subscription = {
            "event": "subscribe",
            "pair": ["XBT/USD"],
            "subscription": {
                "name": "ticker"
            }
        }
        await websocket.send(json.dumps(subscription))
        async for message in websocket:
            print(message)

asyncio.get_event_loop().run_until_complete(kraken_ws())
