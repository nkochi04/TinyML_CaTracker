import asyncio
import tkinter as tk
from tkinter import messagebox, simpledialog
from bleak import BleakClient, BleakScanner
import os
from pathlib import Path
import threading

DEVICE_NAME = "CatTracker"
CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BUTTON_COLORS = [
    "#3498db", "#2ecc71", "#e74c3c", "#9b59b6",
    "#f39c12", "#1abc9c", "#e67e22", "#34495e"
]

class CatTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cat Tracker Recorder")
        self.root.geometry("420x500")

        # State variables
        self.recording_label = None
        self.csv_files = {}
        self.data_queue = None  # created in BLE thread's event loop
        self.ble_loop = None    # reference to BLE event loop
        self.ble_connected = False
        self.labels = []
        self.buttons = {}
        self.color_index = 0

        # Title
        title_label = tk.Label(root, text="Cat Activity Recorder", font=("Arial", 16, "bold"))
        title_label.pack(pady=(20, 5))

        # Active indicator label
        self.active_label = tk.Label(root, text="", font=("Arial", 11, "bold"), fg="#27ae60")
        self.active_label.pack(pady=(0, 10))

        # Scrollable frame for buttons
        self.buttons_frame = tk.Frame(root)
        self.buttons_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        # Bottom controls
        bottom_frame = tk.Frame(root)
        bottom_frame.pack(pady=10, fill=tk.X, padx=20)

        self.new_label_entry = tk.Entry(bottom_frame, font=("Arial", 12), width=14)
        self.new_label_entry.insert(0, "label name")
        self.new_label_entry.bind("<FocusIn>", self._clear_placeholder)
        self.new_label_entry.pack(side=tk.LEFT, padx=(0, 8))

        add_btn = tk.Button(
            bottom_frame,
            text="+ Add Button",
            font=("Arial", 11, "bold"),
            bg="#2c3e50",
            fg="white",
            activebackground="#34495e",
            command=self.add_label_button
        )
        add_btn.pack(side=tk.LEFT)

        # Status label
        self.status_label = tk.Label(root, text="Status: Connecting to BLE...", font=("Arial", 10))
        self.status_label.pack(pady=(5, 15))

        # Start BLE connection in background
        self.ble_thread = threading.Thread(target=self.start_ble_loop, daemon=True)
        self.ble_thread.start()

    def _clear_placeholder(self, event):
        if self.new_label_entry.get() == "label name":
            self.new_label_entry.delete(0, tk.END)

    def add_label_button(self):
        """Add a new recording button with the entered label name"""
        label = self.new_label_entry.get().strip().lower()

        if not label or label == "label name":
            messagebox.showwarning("No Label", "Please enter a label name.")
            return
        if label in self.labels:
            messagebox.showwarning("Duplicate", f"Label '{label}' already exists.")
            return

        # Create folder
        Path(label).mkdir(exist_ok=True)
        self.labels.append(label)

        # Pick a color
        color = BUTTON_COLORS[self.color_index % len(BUTTON_COLORS)]
        self.color_index += 1

        btn = tk.Button(
            self.buttons_frame,
            text=label.upper(),
            font=("Arial", 13, "bold"),
            bg=color,
            fg="white",
            activebackground=color,
            width=20,
            height=2,
            command=lambda l=label: self.toggle_recording(l)
        )
        btn.pack(pady=6)
        self.buttons[label] = btn

        # Store color for reset
        if not hasattr(self, '_button_colors'):
            self._button_colors = {}
        self._button_colors[label] = color

        # Clear entry
        self.new_label_entry.delete(0, tk.END)
        self.new_label_entry.insert(0, "label name")

    def start_ble_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.ble_loop = loop
        self.data_queue = asyncio.Queue()
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
                self.update_status("Connected! Ready to record.")

                await client.start_notify(CHAR_UUID, self.ble_handler)

                while True:
                    await asyncio.sleep(0.1)
                    await self.process_queue()

        except Exception as e:
            self.update_status(f"BLE Error: {str(e)}")
            self.ble_connected = False

    def ble_handler(self, sender, data):
        try:
            line = data.decode("utf-8").strip()
            print("IMU:", line)
            if self.ble_loop and self.data_queue:
                self.ble_loop.call_soon_threadsafe(self.data_queue.put_nowait, line)
        except Exception as e:
            print(f"Handler error: {e}")

    async def process_queue(self):
        try:
            while not self.data_queue.empty():
                data = await self.data_queue.get()

                if self.recording_label and self.recording_label in self.csv_files:
                    file_handle = self.csv_files[self.recording_label]
                    file_handle.write(data + "\n")
                    file_handle.flush()

        except Exception as e:
            print(f"Queue processing error: {e}")

    def toggle_recording(self, label):
        if not self.ble_connected:
            messagebox.showwarning("Not Connected", "BLE device not connected yet!")
            return

        if self.recording_label == label:
            self.stop_recording(label)
        else:
            if self.recording_label:
                self.stop_recording(self.recording_label)
            self.start_recording(label)

    def start_recording(self, label):
        try:
            index = self.get_next_index(label)
            filename = f"{label}/{label}_{index}.csv"

            file_handle = open(filename, 'w')
            file_handle.write("t,ax,ay,az,gx,gy,gz\n")

            self.csv_files[label] = file_handle
            self.recording_label = label

            self.buttons[label].config(relief=tk.SUNKEN, bg="#27ae60")
            self.active_label.config(text=f"● ACTIVE: {label.upper()} — recording...", fg="#27ae60")
            self.update_status(f"Recording: {label} → {filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")

    def stop_recording(self, label):
        try:
            if label in self.csv_files:
                self.csv_files[label].close()
                del self.csv_files[label]

            self.recording_label = None

            orig_color = self._button_colors.get(label, "#3498db")
            self.buttons[label].config(relief=tk.RAISED, bg=orig_color)
            self.active_label.config(text="")
            self.update_status("Ready to record.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop recording: {str(e)}")

    def get_next_index(self, label):
        folder = Path(label)
        existing_files = list(folder.glob(f"{label}_*.csv"))

        if not existing_files:
            return 1

        indices = []
        for f in existing_files:
            try:
                idx = int(f.stem.split('_')[1])
                indices.append(idx)
            except:
                pass

        return max(indices) + 1 if indices else 1

    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=f"Status: {message}"))


if __name__ == "__main__":
    root = tk.Tk()
    app = CatTrackerGUI(root)
    root.mainloop()