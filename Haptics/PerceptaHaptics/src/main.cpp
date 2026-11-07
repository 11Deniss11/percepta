#include <Arduino.h>

#define LED_BUILTIN 8

void setup() {
  // Initialize the LED pin as a digital output
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  // Turn LED ON (Active LOW on C3 SuperMini)
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);

  // Turn LED OFF
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
}