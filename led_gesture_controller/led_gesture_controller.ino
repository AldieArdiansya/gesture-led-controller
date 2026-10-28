/* Arduino Uno: Kontrol 3 LED (Merah, Hijau, Biru) */
#include <Arduino.h>
#include <stdio.h>

const int pinRed   = 9;
const int pinGreen = 10;
const int pinBlue  = 11;

char serialLine[32];
size_t serialLineLength = 0;
bool serialLineOverflow = false;

void setup() {
  Serial.begin(115200);
  pinMode(pinRed, OUTPUT);
  pinMode(pinGreen, OUTPUT);
  pinMode(pinBlue, OUTPUT);
  analogWrite(pinRed, 0);
  analogWrite(pinGreen, 0);
  analogWrite(pinBlue, 0);
}

void loop() {
  while (Serial.available() > 0) {
    char incoming = Serial.read();

    if (incoming == '\r') {
      continue;
    }

    if (incoming == '\n') {
      if (!serialLineOverflow && serialLineLength > 0) {
        serialLine[serialLineLength] = '\0';

        int r;
        int g;
        int b;
        if (sscanf(serialLine, "%d,%d,%d", &r, &g, &b) == 3) {
          analogWrite(pinRed, constrain(r, 0, 255));
          analogWrite(pinGreen, constrain(g, 0, 255));
          analogWrite(pinBlue, constrain(b, 0, 255));
        }
      }

      serialLineLength = 0;
      serialLineOverflow = false;
      continue;
    }

    if (serialLineLength < sizeof(serialLine) - 1) {
      serialLine[serialLineLength++] = incoming;
    } else {
      serialLineOverflow = true;
    }
  }
}