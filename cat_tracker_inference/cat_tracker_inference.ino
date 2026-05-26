#include <Wire.h>
#include "LSM6DS3.h"
#include <NimBLEDevice.h>
#include <CatMonitor_inferencing.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

NimBLECharacteristic* pCharacteristic;
LSM6DS3 imu(I2C_MODE, 0x6A);

float buffer[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE] = { 0 };
static int sampleIndex = 0;

int get_imu_data(size_t offset, size_t length, float *out_ptr) {
    memcpy(out_ptr, buffer + offset, length * sizeof(float));
    return 0;
}

void setup() {
    Serial.begin(115200);
    Wire.begin();

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
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    pCharacteristic->setValue("Waiting...");
    pService->start();

    NimBLEAdvertising *pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->setName("CatTracker");
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->start();
    Serial.println("Advertising started");
}

void loop() {
    // Fill buffer
    buffer[sampleIndex++] = imu.readFloatAccelX();
    buffer[sampleIndex++] = imu.readFloatAccelY();
    buffer[sampleIndex++] = imu.readFloatAccelZ();
    buffer[sampleIndex++] = imu.readFloatGyroX();
    buffer[sampleIndex++] = imu.readFloatGyroY();
    buffer[sampleIndex++] = imu.readFloatGyroZ();

    delay(1000 / EI_CLASSIFIER_FREQUENCY);

    // When full, classify and send top result over BLE
    if (sampleIndex >= EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) {
        sampleIndex = 0;

        signal_t signal;
        signal.total_length = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE;
        signal.get_data = &get_imu_data;

        ei_impulse_result_t result = { 0 };
        EI_IMPULSE_ERROR res = run_classifier(&signal, &result, false);
        if (res != EI_IMPULSE_OK) {
            Serial.printf("Classifier failed (%d)\n", res);
            return;
        }

        // Find top class
        int topIndex = 0;
        float topValue = 0;
        for (uint16_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
            if (result.classification[i].value > topValue) {
                topValue = result.classification[i].value;
                topIndex = i;
            }
        }

        String classResult = String(ei_classifier_inferencing_categories[topIndex])
                             + ": " + String(topValue * 100, 1) + "%";
        Serial.println(classResult);
        pCharacteristic->setValue(classResult.c_str());
        pCharacteristic->notify();
    }
}