#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#define LED_BUILTIN 8

// Wi-Fi stuffs
const char* wifi_ssid = "iPhone SE (2nd generation)";
const char* wifi_password = "passpasspasspass";

// UDP Configuration
const int udpPort = 5000;
WiFiUDP udp;
char incomingPacket[255];

void setup() {
  // Initialize the LED pin as a digital output
  pinMode(LED_BUILTIN, OUTPUT);

  Serial.begin(115200);

  delay(3000); // Give time for Serial to initialize

  //Attempt to connect to Wi-Fi
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(wifi_ssid, wifi_password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  // Confirm connection
  Serial.print("\nWiFi connected with IP address: ");
  Serial.println(WiFi.localIP());

  // Start listening for UDP packets
  udp.begin(udpPort);
  Serial.printf("Listening on UDP port %d\n", udpPort);
}


void loop() {
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