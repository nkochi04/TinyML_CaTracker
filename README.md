# CaTracker

*feat. Molly & Balu*

CaTracker is a TinyML-based activity tracker for cats that classifies feline activity in real time, directly on a low-power microcontroller.

## Goal

Build a wearable that shows a cat's current activity live — without relying on cloud processing or heavy hardware.

## Why TinyML?

- **Energy efficiency** – on-device inference keeps power draw low, extending battery life on a small wearable.
- **A clean classification problem** – cat activity naturally separates into a small set of well-defined motion patterns.
- **Local, real-time detection** – no network dependency; the classification result is available instantly on the device.

## Approach

1. **Hardware** – Seeed Xiao ESP32-S3 Sense with an IMU breakout board (6-axis accelerometer + gyroscope), powered by a 300 mAh LiPo battery.
2. **Data collection** – Since a wired connection isn't practical on a moving cat, sensor data (6 axes, 50 Hz) is streamed over Bluetooth to a laptop, where a Python script labels the incoming data live while a person records and prompts the cat through different movements.
3. **Preprocessing** – Using Edge Impulse: a sliding window (2500 ms window, 500 ms stride) with FFT-based spectral analysis on the accelerometer/gyroscope data, exported to a unified CSV and split into training/test sets.
4. **Training** – A neural network classifier trained on three activity classes: **Chill**, **Groom**, and **Walk** (the *Eat* and *Play* classes were dropped, as they proved too hard to capture consistently).
5. **Deployment** – The trained model runs on-device, outputting class probabilities every 2500 ms.

## Results

- **93.7% accuracy** on the test set, with strong per-class F1 scores across Chill, Groom, and Walk.
- Live on-device classification verified for all three classes.

## Future Work

- Collect more training data and add further activity classes (e.g. Eat, Play)
- Apply class balancing
- Recruit more motivated cats 🐱
- Move to a smaller board integrated into a collar
