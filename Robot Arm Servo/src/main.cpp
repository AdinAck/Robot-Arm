#include <Arduino.h>
#include <Servo.h>

Servo servo;

void setup ()
{
  servo.attach(3);
  Serial.begin(9600);
}

void loop ()
{
  if (Serial.available() > 0) {
    servo.write(Serial.readStringUntil('\n').toInt());
  }
}
