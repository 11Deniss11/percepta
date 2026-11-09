#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#define LED_BUILTIN 8
#define LEFT 0
#define RIGHT 1
#define BOTTOM 4
#define TOP 3

// Wi-Fi stuffs
const char* wifi_ssid = "Percepta";
const char* wifi_password = "percepta-camera";

// UDP Configuration
const int udpPort = 5000;
WiFiUDP udp;
char incomingPacket[255];

bool connectToWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.disconnect();
  delay(100);

  Serial.printf("Connecting to Wi-Fi network \"%s\"", wifi_ssid);
  WiFi.begin(wifi_ssid, wifi_password);

  const unsigned long timeout = 15000;
  const unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < timeout) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi connected. IP address: ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.printf("Wi-Fi connection failed (status %d): ", WiFi.status());
  switch (WiFi.status()) {
    case WL_NO_SSID_AVAIL:
      Serial.println("SSID not found. Make sure the network is 2.4 GHz.");
      break;
    case WL_CONNECT_FAILED:
      Serial.println("authentication failed. Check WPA mode and password.");
      break;
    case WL_CONNECTION_LOST:
      Serial.println("connection was lost.");
      break;
    case WL_DISCONNECTED:
      Serial.println("disconnected or timed out.");
      break;
    default:
      Serial.println("timed out.");
      break;
  }
  return false;
}

void setup() {
  // Initialize the LED pin as a digital output
  pinMode(LED_BUILTIN, OUTPUT);

  Serial.begin(115200);

  delay(3000); // Give time for Serial to initialize

  if (connectToWiFi()) {
    udp.begin(udpPort);
    Serial.printf("Listening on UDP port %d\n", udpPort);
  }
}


void loop() {
  static unsigned long lastReconnectAttempt = 0;
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastReconnectAttempt >= 10000) {
      lastReconnectAttempt = millis();
      if (connectToWiFi()) {
        udp.begin(udpPort);
        Serial.printf("Listening on UDP port %d\n", udpPort);
      }
    }
    delay(10);
    return;
  }

  // Check if a UDP packet has arrived
  int packetSize = udp.parsePacket();
  
  if (packetSize) {
    // Read the packet into the buffer
    int len = udp.read(incomingPacket, sizeof(incomingPacket) - 1);
    if (len > 0) {
      incomingPacket[len] = '\0'; // Null-terminate the string so it can be parsed
    }

    // Declare motor power values
    float motor_nx, motor_px, motor_ny, motor_py;
    

    if (sscanf(incomingPacket, "%f,%f,%f,%f", &motor_nx, &motor_px, &motor_ny, &motor_py) == 4) {
      Serial.printf("Parsed -> nx: %.3f | px: %.3f | ny: %.3f | py: %.3f\n", 
                    motor_nx, motor_px, motor_ny, motor_py);
                

                    
      // Flash LED to visually indicate successful data extraction
      digitalWrite(LED_BUILTIN, LOW);
      delay(50);
      digitalWrite(LED_BUILTIN, HIGH);
      
      // TODO: Apply these parsed magnitudes to your motor drivers here
      // Passed motor values between 0 and 1
      
    } else {
      Serial.println("Failed to parse packet format.");
    }
  }
}