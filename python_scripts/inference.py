import asyncio
import tkinter as tk
from bleak import BleakClient, BleakScanner
import threading

DEVICE_NAME = "CatTracker"
CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# Color per activity label (falls back to gray for anything unrecognized)
ACTIVITY_COLORS = {
    "walk": "#3498db",
    "chill": "#2ecc71",
    "groom": "#9b59b6",
}
DEFAULT_COLOR = "#7f8c8d"
DISCONNECTED_COLOR = "#2c3e50"


class CatTrackerInferenceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cat Activity Monitor")
        self.root.geometry("480x360")
        self.root.configure(bg=DISCONNECTED_COLOR)

        self.ble_loop = None
        self.ble_connected = False

        # Big activity label (the main event)
        self.activity_label = tk.Label(
            root,
            text="—",
            font=("Arial", 42, "bold"),
            fg="white",
            bg=DISCONNECTED_COLOR,
        )
        self.activity_label.pack(expand=True, fill=tk.BOTH)

        # Confidence readout
        self.confidence_label = tk.Label(
            root,
            text="",
            font=("Arial", 16),
            fg="white",
            bg=DISCONNECTED_COLOR,
        )
        self.confidence_label.pack(pady=(0, 10))

        # Connection status bar
        self.status_label = tk.Label(
            root,
            text="Status: Connecting to BLE...",
            font=("Arial", 10),
            fg="#bdc3c7",
            bg=DISCONNECTED_COLOR,
        )
        self.status_label.pack(pady=(0, 15))

        self.ble_thread = threading.Thread(target=self.start_ble_loop, daemon=True)
        self.ble_thread.start()

    # ---------- BLE handling ----------

    def start_ble_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.ble_loop = loop
        loop.run_until_complete(self.ble_main())

    async def ble_main(self):
        try:
            self.update_status("Scanning for device...")
            devices = await BleakScanner.discover()
            target = None

            for d in devices:
                if d.name == DEVICE_NAME:
                    target = d
                    break

            if not target:
                self.update_status("ERROR: Device not found!")
                return

            self.update_status(f"Connecting to {target.address}...")

            async with BleakClient(target.address) as client:
                self.ble_connected = True
                self.update_status("Connected! Waiting for inference...")

                await client.start_notify(CHAR_UUID, self.ble_handler)

                while True:
                    await asyncio.sleep(0.5)
                    if not client.is_connected:
                        break

            self.ble_connected = False
            self.update_status("Disconnected.")

        except Exception as e:
            self.ble_connected = False
            self.update_status(f"BLE Error: {str(e)}")

    def ble_handler(self, sender, data):
        try:
            line = data.decode("utf-8").strip()
            self.root.after(0, self.handle_inference, line)
        except Exception as e:
            print(f"Handler error: {e}")

    # ---------- UI update ----------

    def handle_inference(self, line):
        """Parse a string like 'walk: 87.3%' and update the display."""
        label, confidence = self.parse_result(line)
        color = ACTIVITY_COLORS.get(label.lower(), DEFAULT_COLOR)

        self.root.configure(bg=color)
        self.activity_label.config(text=label.upper(), bg=color)
        self.confidence_label.config(
            text=f"{confidence:.1f}% confidence" if confidence is not None else "",
            bg=color,
        )
        self.status_label.config(bg=color)

    @staticmethod
    def parse_result(line):
        # Expected format: "<label>: <value>%"
        try:
            label, value = line.split(":", 1)
            value = value.strip().rstrip("%")
            return label.strip(), float(value)
        except Exception:
            return line, None

    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=f"Status: {message}"))


if __name__ == "__main__":
    root = tk.Tk()
    app = CatTrackerInferenceGUI(root)
    root.mainloop()