#include "pinout.h"
//VARIABLES
int version=0;

//FUNCIONES
void setup() {
  
  pinMode(PWM1, OUTPUT);
  pinMode(PWM2, OUTPUT);
  Serial.begin(115200);
  menu_principal();
}

void loop() {
  if (Serial.available()>0){
    String option= Serial.readString();
    Serial.println("Opción elegida: "+option);
    switch(option.toInt()){
      case 1:
        test_pwm(PWM1);
        break;
      case 2:
        test_pwm(PWM1);
        break;
      case 3:
        test_rele(OUT1);
        break;
      case 4:
        test_rele(OUT2);
        break;
      case 5:
        test_ADC(A0);
        break;
      case 6:
        test_ADC(A1);
        break;
      case 7:
        test_rele(DIO1);
        break;
      case 8:
        test_rele(DIO2);
        break;

    }
  menu_principal();
  }
}

void test_pwm(int pin){
  Serial.println("Test PWM pin: "+String(pin));
  for(int i=0; i<10; i++){
    int val= i*25+5;
    Serial.println(val);
    analogWrite(pin, val);
    delay(1000);    
  }
return;
}

void test_rele(int pin){
  Serial.println("Test Rele Output pin: "+String(pin));
  for(int i=0;i<10;i++){
    Serial.println("OFF");
    digitalWrite(pin, 0);
    delay(1000);
    Serial.println("ON");
    digitalWrite(pin, 1);
    delay(1000);
  }
  return;

}

void test_ADC(int pin){
  int val_adc;
  for(int i=0;i<10;i++){
    val_adc= analogRead(pin);
    Serial.println(val_adc);
    delay(1000);
  }  
}
void menu_principal(void){
  Serial.println("---------------------------------------------------");
  Serial.println("POD Board Test v"+String(version));
  Serial.println("---------------------------------------------------");
  Serial.println("Elija el test:");
  Serial.println("      1- PWM1(D5)");
  Serial.println("      2- PWM2(D6)");
  Serial.println("      3- OUT1(D12)");
  Serial.println("      4- OUT2(D13)");
  Serial.println("      5- A0");
  Serial.println("      6- A1");
  Serial.println("      7- DIO1(D9)");
  Serial.println("      8- DIO2(D10)");
  return;
}
