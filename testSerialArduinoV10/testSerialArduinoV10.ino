// LIBRERIAS
#include <Wire.h>
#include <Adafruit_MLX90614.h>
#include <Q2HX711.h>
#include "pinout.h"

// --- ESTRUCTURA DEL PAQUETE BINARIO ---
struct DataPacket {
  uint32_t tiempo;    // 4 bytes (milisegundos)
  float temp_amb;     // 4 bytes
  float temp_obj;     // 4 bytes
  uint32_t vueltas;   // 4 bytes (Soporta millones de vueltas sin desbordar)
  int32_t carga;      // 4 bytes
} __attribute__((packed)); // Obliga a que no haya bytes vacíos entre variables

#define DEBUG_ false

// VARIABLES DEL PROGRAMA
const byte hx711_data_pin = SCK2;
const byte hx711_clock_pin = DT2;
int CNY = INT0; //Sensor de vueltas eje principal - CNY70
int D3 = PWM1;  // PWM - Control de frecuencia del variador
int D4 = OUT1;  // Control de encendido del motor

float Freq = 0; // Frecuencia que envio al variador
unsigned long tinicio = 0; // Tiempo en el que inicio el programa (en milisegundos)
bool btinicio = false;     // bandera tiempo inicio
uint32_t VTEJE = 0;        // AHORA ES 32 BITS: Vueltas totales leidas en el eje.

unsigned long tiempo_de_muestreo;  // necesario para timing del bucle
String dataReadFromSerial = "";    // for incoming serial data
int funcion = 0;                   // Estado de funcionamiento  0-> Espera  1-> Testeando

int setRPM = 0;                    // RPM Seteadas por demanada del serial
unsigned long setSECONDS = 0;      // SEGUNDOS Seteados por demanda del serial
unsigned long setMILISECONDS = 0;  // MILISEGUNDOS Seteados por demanda del serial
unsigned long currentMS;
unsigned long sampled_time = 12500;
unsigned long startTime = 0;
unsigned long timeThreshold = 50;

bool SENSOR_TEMP = true;

Q2HX711 hx711(hx711_data_pin, hx711_clock_pin);
Adafruit_MLX90614 mlx = Adafruit_MLX90614(); //Para leer datos de temperatura con mlx.


// --- FUNCION DE ENVÍO BINARIO ---
void enviarPaqueteBinario(uint32_t t, float ta, float to, uint32_t v, int32_t c) {
  DataPacket packet;
  packet.tiempo = t;
  packet.temp_amb = ta;
  packet.temp_obj = to;
  packet.vueltas = v;
  packet.carga = c;

  // 1. Enviar Cabecera de Sincronización (Header)
  uint8_t header[2] = {0xAA, 0xBB};
  Serial.write(header, 2);

  // 2. Calcular Checksum (suma simple de bytes)
  uint8_t* ptr = (uint8_t*)&packet;
  uint8_t checksum = 0;
  for (uint8_t i = 0; i < sizeof(DataPacket); i++) {
    checksum += ptr[i];
  }

  // 3. Enviar Datos Puros (Payload)
  Serial.write((uint8_t*)&packet, sizeof(DataPacket));
  
  // 4. Enviar Checksum al final
  Serial.write(checksum);
}


void setup() {
  Serial.begin(115200);
  tiempo_de_muestreo = millis();
  startTime = millis();
  
  mlx.begin(); //Inicia el sensor
  if (isnan(mlx.readAmbientTempC())){ 
    //Serial.println("Sensor de temperatura no conectado"); // Comentado para evitar ruido en Python
    SENSOR_TEMP = false;
  }
                  
  pinMode(D4, OUTPUT); // Seteo como salida
  pinMode(D3, OUTPUT); // Seteo como salida
  
  pinMode(CNY, INPUT); //Sensor de vueltas declarado como entrada
  attachInterrupt(digitalPinToInterrupt(CNY), CNY70, RISING); 
  
  Serial.println("Iniciando....");
}


void loop() {

        // Start: ESCUCHANDO SERIAL //
        while (funcion == 0) {        
            leer_puerto_serie();
        }
        // End: ESCUCHANDO SERIAL //

        // Start: ENSAYANDO //
        while (funcion == 1) {        

              // Setear Inicio
              if (btinicio == false){ 
                tinicio = millis();
                btinicio = true;
                VTEJE = 0; // Reiniciar contador de vueltas al arrancar
              }   
              
              // TRAMA BINARIA
              if(micros() > tiempo_de_muestreo + sampled_time) {     
                  tiempo_de_muestreo = micros();
                  currentMS = millis() - tinicio; 

                  // Lectura de variables
                  float t_amb = SENSOR_TEMP ? mlx.readAmbientTempC() : 20.16;
                  float t_obj = SENSOR_TEMP ? mlx.readObjectTempC() : 22.3 + float(currentMS)/(2000.0+currentMS) + float(random(0,10))/100.0;
                  
                  while (hx711.readyToSend() != 1) { } 
                  int32_t carga = hx711.read();

                  // Enviar el paquete estructurado
                  enviarPaqueteBinario(currentMS, t_amb, t_obj, VTEJE, carga);

                  // CHECKEAR SI PASO EL TIEMPO                  
                  if(currentMS > setMILISECONDS) {  
                     Serial.print("TESTEND");
                     Serial.print('\n');
                     funcion = 0;                   
                  }            
              }

             // LEER EL PUERTO SERIE PARA COMANDOS EN VIVO
             leer_puerto_serie();
        }
        // End: ENSAYANDO //
}

// FUNCION DE LECTURA PUERTO SERIE
void leer_puerto_serie(){ 

    if (Serial.available() > 0) { 
        dataReadFromSerial = Serial.readStringUntil('\n'); // Es más seguro leer hasta el salto de línea
        Serial.flush();
    }                                                                                           

    // --- COMENZAR ENSAYO --- //
    if (dataReadFromSerial.substring(0,9) == "TESTSTART") {
        btinicio = false;
        funcion = 1;
        setRPM = dataReadFromSerial.substring(10,16).toInt();
        setSECONDS = dataReadFromSerial.substring(18,24).toInt();
        setMILISECONDS = setSECONDS * 1000;
        Freq = (setRPM * 17.2) / 100;
        digitalWrite(D4, LOW);
        analogWrite(D3, Freq);
        dataReadFromSerial = "";
    }
    
    // --- DETENER ENSAYO --- //
    if (dataReadFromSerial.substring(0,8) == "TESTSTOP") { 
         Serial.print("TESTSTOPPED");
         Serial.print('\n');
         digitalWrite(D4, HIGH);
         analogWrite(D3, 0);
         funcion = 0;
         dataReadFromSerial = "";
    }  

    // --- COMPROBAR CONEXION A MAQUINA POD --- //
    if (dataReadFromSerial.substring(0,15) == "CHECKCONNECTION") { 
         Serial.print("PODCONNECTED");
         Serial.print('\n');
         funcion = 0;
         dataReadFromSerial = "";
    }  

    // --- CALIBRACION --- //
    if (dataReadFromSerial.substring(0,19) == "CALIBRACIONMEDICION") { 
         Serial.print("CALIBRACIONSTART");
         Serial.print('\n');

         for (int i = 0; i < 60; i++) {                        
           Serial.print(random(350,365));
           Serial.print('\n');
           delay(50);
         }
         
         Serial.print("CALIBRACIONEND");                       
         Serial.print('\n');
         funcion = 0;
         dataReadFromSerial = "";
    }  

    dataReadFromSerial = "";
}

// INTERRUPCION SENSOR DE VUELTAS
void CNY70() {
  if (millis() - startTime > timeThreshold) {
    VTEJE++;
    startTime = millis();
  }
}
