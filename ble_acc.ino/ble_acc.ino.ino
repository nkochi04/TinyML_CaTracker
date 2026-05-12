#include <Wire.h>
#include "LSM6DS3.h"
#include <NimBLEDevice.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

NimBLECharacteristic* pCharacteristic;
LSM6DS3 imu;

void setup() {
  Serial.begin(115200);

  Wire.begin(); // ESP32-S3 I2C

  if (imu.begin() != 0) {
    Serial.println("IMU init failed");
    while (1);
  }

  Serial.println("IMU ready");

  NimBLEDevice::init("CatTracker");

  NimBLEServer *pServer = NimBLEDevice::createServer();

  NimBLEService *pService = pServer->createService(SERVICE_UUID);

  pCharacteristic = pService->createCharacteristic(
      CHARACTERISTIC_UUID,
      NIMBLE_PROPERTY::READ |
      NIMBLE_PROPERTY::NOTIFY
  );

  pCharacteristic->setValue("Hello");

  pService->start();

  NimBLEAdvertising *pAdvertising = NimBLEDevice::getAdvertising();
  pAdvertising->setName("CatTracker");
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();

  Serial.println("Advertising started");
}

void loop() {
  static int counter = 0;

  float ax = imu.readFloatAccelX();
  float ay = imu.readFloatAccelY();
  float az = imu.readFloatAccelZ();

  float gx = imu.readFloatGyroX();
  float gy = imu.readFloatGyroY();
  float gz = imu.readFloatGyroZ();

  String value = String(counter++) + ", " +
  String(ax) + ", " +
  String(ay) + ", " +
  String(az) + ", " +
  String(gx) + ", " + 
  String(gy) + ", " +
  String(gz);

  pCharacteristic->setValue(value.c_str());
  pCharacteristic->notify();

  Serial.println(value);

  delay(20);
}