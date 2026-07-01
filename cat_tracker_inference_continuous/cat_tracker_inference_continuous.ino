#include <Wire.h>
#include "LSM6DS3.h"
#include <NimBLEDevice.h>
#include <CatMonitor_inferencing.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// Stride length in ms — must match what you trained with in EI Studio
#define STRIDE_MS 500

NimBLECharacteristic* pCharacteristic;
LSM6DS3 imu(I2C_MODE, 0x6A);

// Full window buffer (unchanged size from the original single-shot sketch)
float buffer[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE] = { 0 };

static const size_t AXES = 6; // ax, ay, az, gx, gy, gz
static const size_t stride_samples    = (EI_CLASSIFIER_FREQUENCY * STRIDE_MS) / 1000; // e.g. 25 @ 50Hz
static const size_t stride_frame_size = stride_samples * AXES;                        // floats per stride

int get_imu_data(size_t offset, size_t length, float *out_ptr) {
    memcpy(out_ptr, buffer + offset, length * sizeof(float));
    return 0;
}

void readOneSample(size_t writeIndex) {
    buffer[writeIndex + 0] = imu.readFloatAccelX();
    buffer[writeIndex + 1] = imu.readFloatAccelY();
    buffer[writeIndex + 2] = imu.readFloatAccelZ();
    buffer[writeIndex + 3] = imu.readFloatGyroX();
    buffer[writeIndex + 4] = imu.readFloatGyroY();
    buffer[writeIndex + 5] = imu.readFloatGyroZ();
}

void classifyAndSend() {
    signal_t signal;
    signal.total_length = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE;
    signal.get_data = &get_imu_data;

    ei_impulse_result_t result = { 0 };
    EI_IMPULSE_ERROR res = run_classifier(&signal, &result, false);
    if (res != EI_IMPULSE_OK) {
        Serial.printf("Classifier failed (%d)\n", res);
        return;
    }

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

    // One-time startup: fill the full 2.5s window before the first classification
    Serial.println("Filling initial window...");
    size_t totalSamples = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE / AXES;
    for (size_t s = 0; s < totalSamples; s++) {
        readOneSample(s * AXES);
        delay(1000 / EI_CLASSIFIER_FREQUENCY);
    }
    Serial.println("Initial window filled, starting classification.");
}

void loop() {
    // Drop the oldest stride worth of samples (shift everything left)
    memmove(buffer,
            buffer + stride_frame_size,
            (EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE - stride_frame_size) * sizeof(float));

    // Read one new stride worth of samples into the freed-up space at the end
    size_t writeStart = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE - stride_frame_size;
    for (size_t s = 0; s < stride_samples; s++) {
        readOneSample(writeStart + s * AXES);
        delay(1000 / EI_CLASSIFIER_FREQUENCY);
    }

    // Classify the full (now-shifted) window and send the result over BLE
    classifyAndSend();
}