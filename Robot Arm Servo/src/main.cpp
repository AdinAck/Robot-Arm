#include <Arduino.h>
#include <Servo.h>
Servo myservo; // declare servo
int integerData;
String comdata;

void setup ()
{
  Serial.begin(9600);
  myservo.attach(3);

}

void loop ()
{
  SerialChecker();
  
  myservo.write(integerData);
  
  delay(50);

}

void SerialChecker()
{
  //read string from serial monitor
  if (Serial.available() > 0) // if we get a valid byte, read analog ins:
  {
    comdata = ""; //reset the old values
    while (Serial.available() > 0)
    {
      comdata += char(Serial.read()); //Add the character value to comdata
      delay(2);//so that whole message is sent before the arduino reads it
      integerData = comdata.toInt(); //converts our character data into a number
    }
    Serial.println(comdata);//prints out what you are typing
  }
}
