import asyncio
from bleak import BleakScanner

async def main():
    devices = await BleakScanner.discover()
    for d in devices:
        if (d.name == "CatTracker"):
            print(d.name, d.address)

asyncio.run(main())