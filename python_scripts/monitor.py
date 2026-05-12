import asyncio
from bleak import BleakClient, BleakScanner

DEVICE_NAME = "CatTracker"
CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

def handler(sender, data):
    try:
        line = data.decode("utf-8").strip()
        print("IMU:", line)
    except:
        pass

async def main():
    print("Scanning...")

    devices = await BleakScanner.discover()

    target = None
    for d in devices:
        if d.name == DEVICE_NAME:
            target = d
            break

    if not target:
        print("Device not found")
        return

    print("Connecting to:", target.address)

    async with BleakClient(target.address) as client:
        print("Connected")

        await client.start_notify(CHAR_UUID, handler)

        print("Live stream started...")

        while True:
            await asyncio.sleep(1)

asyncio.run(main())