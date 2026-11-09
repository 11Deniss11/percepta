#include <Arduino.h>
#include <math.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#define LED_BUILTIN 8

// Connect the motor drivers to these GPIOs. Each motor must be driven through
// an appropriate transistor or motor driver, not directly from an ESP32 pin.
const uint8_t motorPins[] = {4, 5, 6, 7};
const uint8_t motorCount = sizeof(motorPins) / sizeof(motorPins[0]);
const unsigned long motorTimeoutMs = 500;

// Wi-Fi settings
const char* wifi_ssid = "iPhone SE (2nd generation)";
const char* wifi_password = "passpasspasspass";

// UDP configuration
const uint16_t udpPort = 5000;
WiFiUDP udp;
char incomingPacket[64];
unsigned long lastMotorPacketMs = 0;

void setMotorPower(float motor_nx, float motor_px, float motor_ny, float motor_py) {
  const float motorPowers[] = {motor_nx, motor_px, motor_ny, motor_py};

  for (uint8_t i = 0; i < motorCount; i++) {
    float power = motorPowers[i];
    if (!isfinite(power)) {
      power = 0.0f;
    }
    power = constrain(power, 0.0f, 1.0f);
    analogWrite(motorPins[i], static_cast<uint8_t>(power * 255.0f));
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  for (uint8_t pin : motorPins) {
    pinMode(pin, OUTPUT);
  }
  setMotorPower(0.0f, 0.0f, 0.0f, 0.0f);

  Serial.begin(115200);

  delay(3000);

  // Attempt to connect to Wi-Fi.
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(wifi_ssid, wifi_password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.print("\nWiFi connected with IP address: ");
  Serial.println(WiFi.localIP());

  udp.begin(udpPort);
  Serial.printf("Listening on UDP port %d\n", udpPort);
}

void loop() {
  int packetSize = udp.parsePacket();

  if (packetSize) {
    int len = udp.read(incomingPacket, sizeof(incomingPacket) - 1);
    if (len > 0) {
      incomingPacket[len] = '\0';
    }

    float motor_nx, motor_px, motor_ny, motor_py;

    if (sscanf(incomingPacket, "%f,%f,%f,%f", &motor_nx, &motor_px, &motor_ny, &motor_py) == 4) {
      Serial.printf("Parsed -> nx: %.3f | px: %.3f | ny: %.3f | py: %.3f\n", 
                    motor_nx, motor_px, motor_ny, motor_py);
      setMotorPower(motor_nx, motor_px, motor_ny, motor_py);
      lastMotorPacketMs = millis();
      digitalWrite(LED_BUILTIN, LOW);
      delay(50);
      digitalWrite(LED_BUILTIN, HIGH);
    } else {
      Serial.println("Failed to parse packet format.");
    }
  }

  if (lastMotorPacketMs != 0 && millis() - lastMotorPacketMs > motorTimeoutMs) {
    setMotorPower(0.0f, 0.0f, 0.0f, 0.0f);
    lastMotorPacketMs = 0;
  }
}
