#include <ESP8266WiFi.h>
#include <DNSServer.h>
#include <ESP8266WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

extern "C" {
  #include "user_interface.h"
}

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 32   // your OLED is 32px tall
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

const char* ssid = "EXB-DEMO";
const byte DNS_PORT = 53;

DNSServer dnsServer;
ESP8266WebServer server(80);

String lastText = "";

// store known MACs
uint8_t knownMACs[10][6];
int knownCount = 0;

// ---------- OLED ----------
void showOLED(String l1, String l2) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0,0);
  display.println(l1);
  display.println(l2);
  display.display();
}

// ---------- WEB ----------
void handleRoot() {
  int count = wifi_softap_get_station_num();

  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <style>
    body { background:black; color:lime; font-family:Arial; text-align:center; }
    h1 { font-size:48px; }
    p { font-size:26px; }
    textarea { font-size:22px; width:80%; margin:10px; }
    button { font-size:24px; padding:10px 20px; }
    .msg { font-size:30px; color:yellow; margin-top:20px; }
  </style>
</head>
<body>
  <h1>Open Wi-Fi Demo</h1>
  <p>This page opened automatically.</p>
  <p>Devices connected: %COUNT%</p>

  <form action="/send" method="POST">
    <textarea name="msg" rows="3" placeholder="Type a secret message..."></textarea><br>
    <button type="submit">Send</button>
  </form>

  <div class="msg">%TEXT%</div>
</body>
</html>
)rawliteral";

  html.replace("%COUNT%", String(count));
  html.replace("%TEXT%", lastText);
  server.send(200, "text/html", html);
}

// ---------- TEXT ----------
void handleSend() {
  if (server.hasArg("msg")) {
    lastText = server.arg("msg");
    Serial.println("LEAKED MESSAGE:");
    Serial.println(lastText);
    showOLED("Leaked Text:", lastText.substring(0,16));
  }
  server.sendHeader("Location", "/");
  server.send(303);
}

// ---------- MAC CHECK ----------
bool macKnown(uint8_t* mac) {
  for (int i=0;i<knownCount;i++) {
    if (memcmp(knownMACs[i], mac, 6)==0) return true;
  }
  return false;
}

void addMAC(uint8_t* mac) {
  memcpy(knownMACs[knownCount], mac, 6);
  knownCount++;
}

String macToString(uint8_t* m) {
  char buf[18];
  sprintf(buf,"%02X:%02X:%02X:%02X:%02X:%02X",m[0],m[1],m[2],m[3],m[4],m[5]);
  return String(buf);
}

// ---------- CLIENT MONITOR ----------
void checkClients() {
  struct station_info *stat = wifi_softap_get_station_info();
  while (stat) {
    if (!macKnown(stat->bssid)) {
      addMAC(stat->bssid);
      String macStr = macToString(stat->bssid);

      Serial.print("NEW DEVICE: ");
      Serial.println(macStr);

      showOLED("New Device:", macStr);
      delay(2000);   // blink time
      showOLED("Connected:", String(wifi_softap_get_station_num()));
    }
    stat = STAILQ_NEXT(stat, next);
  }
  wifi_softap_free_station_info();
}

// ---------- SETUP ----------
void setup() {
  Serial.begin(115200);
  Serial.println("Captive portal + Unencryption.");

  Wire.begin();
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  showOLED("Starting...","");

  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid);

  dnsServer.start(DNS_PORT, "*", WiFi.softAPIP());

  server.on("/", handleRoot);
  server.on("/send", HTTP_POST, handleSend);
  server.onNotFound(handleRoot);
  server.begin();

  showOLED("Waiting for","devices...");
}

// ---------- LOOP ----------
void loop() {
  dnsServer.processNextRequest();
  server.handleClient();
  checkClients();
}
