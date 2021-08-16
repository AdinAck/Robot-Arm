#include <Arduino.h>
#include <Servo.h>

Servo myservo;

int pos = 0;

void setup() {
  myservo.attach(3);
}

void loop() {
  for (pos = 20; pos <= 160; pos += 1) {
    myservo.write(pos);
    delay(15);
  }
  for (pos = 160; pos >= 20; pos -= 1) {
    myservo.write(pos);
    delay(15);
  }
}