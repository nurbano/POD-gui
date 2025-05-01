// LIBRERIAS
#include <Wire.h>
#include <Adafruit_MLX90614.h>
#include <Q2HX711.h>

// VARIABLES DEL PROGRAMA
int CNY = 2; //Sensor de vueltas eje principal - CNY70 - Configurar como interrupcion del programa
int D3 = 3;  // PWM - Control de frecuencia del variador
int D4 = 4;  // Control de encendido del motor
float Freq = 0; // Frecuencia que envio al variador

long tinicio = 0;                            // Tiempo en el que inicio el programa (en milisegundos)
bool btinicio = false;         // bandera tiempo inicio
int VTEJE = 0;                              // Vueltas totales leidas en el eje.
long tiempo_de_muestreo;                    // necesario para timing del puerto serie
String dataRowToSend;
String dataReadFromSerial = "";             // for incoming serial data
int funcion = 0;                            // Estado de funcionamiento  0-> Espera  1-> Testeando
bool headerSent = false;                    // Flag si se ha enviado el header en el CSV
int setRPM = 0;                             // RPM Seteadas por demanada del serial
long setSECONDS = 0;                         // SEGUNDOS Seteados por demanda del serial
long setMILISECONDS = 0;                         // SEGUNDOS Seteados por demanda del serial
long currentMS;
Adafruit_MLX90614 mlx = Adafruit_MLX90614(); //Para leer datos de temperatura con mlx.

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);

  tiempo_de_muestreo= millis();      //Define timing inicial

  mlx.begin(); //Inicia el sensor

  pinMode(D4, OUTPUT); // Seteo como salida
  pinMode(D3, OUTPUT); // Seteo como salida
  
  pinMode(CNY, INPUT); //Sensor de vueltas declarado como entrada
  attachInterrupt(digitalPinToInterrupt(CNY), CNY70, RISING); // Interrupcion sensor de vueltas
  Serial.println("Iniciando....");
}


void loop() {
  // put your main code here, to run repeatedly:

        // Start: ESCUCHANDO SERIAL //
        while (funcion == 0) {        // Si esta en funcion = 0 -> Enscuchando serial
            leer_puerto_serie(); 
        }
        // End: ESCUCHANDO SERIAL //

        // Start: ENSAYANDO //
        while (funcion == 1) {        // Si esta en funcion = 1 -> Ensayando

              // Setear Inicio
              if (btinicio == false){ tinicio = millis(); btinicio = true;}   // Define el tiempo de inicio, que se corre solo una vez
              
              // CSV HEADER
              if (headerSent == false) {
                Serial.print("tiempoMs,tempAmbC,tempObjC,vueltas,celdaCarga");     // Setear headers CSV
                Serial. print('\n');              // New Line
                headerSent = true;
              }

              // CSV INFO
              if(millis()>tiempo_de_muestreo+12.5)   //AUMENTAR TIEMPO DE MUESTRO +30ms (Envia datos cada 12.5ms = 1000/80 SPS-> Menor delay posible por limitaciones del HX711)
              {     
                      
                  tiempo_de_muestreo= millis();                            // Tiempo transcurrido en milisegundos  
        
                  
                  // TIEMPO
                  currentMS=(millis()-tinicio);                         // Imprimir el tiempo
                  dataRowToSend = currentMS;
                  dataRowToSend=dataRowToSend+",";                          // Agregar coma separadora
        
                  // TEMPERATURA AMBIENTE       
                  dataRowToSend=dataRowToSend+"20.16";                       // Linea de codigo para testear
                  //dataRowToSend=dataRowToSend+(mlx.readAmbientTempC());  // Codigo para temperatura ambiente del MLX90614  
                  dataRowToSend=dataRowToSend+",";                          // Agregar coma separadora
        
                  // TEMPERATURA OBJETO
                  float temp = 22.3 + float(currentMS)/(2000+currentMS) + float(random(0,10))/100;                // Linea de codigo para testear         Parto de 22.3 grados, le agrego un aumento de temperatura y un ruido
                  dataRowToSend=dataRowToSend + temp;                       // Linea de codigo para testear
                  //dataRowToSend=dataRowToSend+(mlx.readObjectTempC());   // Codigo para temperatura objeto del MLX90614  
                  dataRowToSend=dataRowToSend+",";                          // Agregar coma separadora
        
                  // VUELTAS DEL EJE       
                  VTEJE = int(setRPM * float(currentMS) / 60000);                        // Linea de codigo para testear   EX: vtEje++;    
                  dataRowToSend=dataRowToSend+VTEJE;                        // Codigo para vueltas totales en el EJE  
                  dataRowToSend=dataRowToSend+",";                          // Agregar coma separadora
        
                  // CELDA DE CARGA       
                  dataRowToSend=dataRowToSend+random(720- (currentMS/1000), 740 - (currentMS/1000));                       // Linea de codigo para testear
                  // dataRowToSend=dataRowToSend+(hx711.read());            // Codigo para celda de carga del HX711
                  // dataRowToSend=dataRowToSend+",";                       // Agregar coma separadora (NO en el ultimo, formato CSV)
        
        
                  // ENVIAR DATOS POR EL SERIAL
                  Serial.print(dataRowToSend);
                  Serial. print('\n');              // New Line
        


              // CHECKEAR SI PASO EL TIEMPO                  
             if(currentMS > setMILISECONDS)     // Si paso el tiempo (segundos x 1000)
              {  
                 Serial.print("TESTEND");             // Enviar señal de finalizado
                 Serial. print('\n');                 // New Line
                 funcion = 0;                         // Volver a funcion de escucha de Serial
                   
              }            

             // LEER EL PUERTO SERIE   ( ES NECESARIO SOLO SI SE QUIERE REALIZAR CAMBIOS DURANTE LA EJECUCION DEL ENSAYO)
             leer_puerto_serie();   
             

       
             }

              
        }
        // End: ENSAYANDO //



      
}
// FIN DEL VOID LOOP




// FUNCION DE LECTURA PUERTO SERIE
void leer_puerto_serie(){ 

    if (Serial.available() > 0) { dataReadFromSerial = Serial.readString(); Serial.flush();
    
    Serial.println(dataReadFromSerial);
    }    // Leer puerto serie
                                                                                                //Serial.print(dataReadFromSerial);                                                     
    // Estados según la lectura del puerto serie //
//    if (Leido.toInt() == 10000000) {  Estado = 1;}       // ENSAYANDO
//    if (Leido.toInt() == 20000000) {  Estado = 2;}       // FINALIZADO
//    if (Leido.toInt() == 30000000) {  Estado = 3;}       // CALIBRACIÓN
//    if (Leido.toInt() < 256) {  velmot = Leido.toInt();}

    
    

// --- COMENZAR ENSAYO --- //
    
    if (dataReadFromSerial.substring(0,9) == "TESTSTART")
      {
        btinicio = false;                                         // Setear bandera de tiempo de inicio en cero
        funcion = 1;                                              // Cambiar funcion para empezar el ensayo
        headerSent = false;                                       // Reset Header Flag
        setRPM = dataReadFromSerial.substring(10,16).toInt();     // RPM formato: "TESTSTART-##RPM#-##SEC#"  // EJ: 850 RPM, 15 SEG "TESTSTART-000800-000015"
        setSECONDS = dataReadFromSerial.substring(18,24).toInt(); // SEGUNDOS Seteados por demanda del serial
        setMILISECONDS = setSECONDS*1000;                         // Seconds to Miliseconds
        Freq = (setRPM * 17.2) / 100;                             // DEV* Calculo de RPM para variador
        digitalWrite(D4, LOW);                                    //DEV* Motor Encendido
        analogWrite(D3, Freq);                                       //DEV* Frecuencia a valor RPM
                                                                  //Serial.print(setRPM);       // Debug
                                                                  //Serial.print(setSECONDS);   // Debug
        dataReadFromSerial = "";
      }
    


// --- DETENER ENSAYO --- //
    
    if (dataReadFromSerial.substring(0,8) == "TESTSTOP")
      { 
         Serial.print("TESTSTOPPED");                           // Enviar señal de detenido por usuario
         Serial. print('\n');                                   // New Line
         digitalWrite(D4, HIGH);                                // DEV* Motor apagado
         analogWrite(D3, 0);                                    // DEV* Seteo frec a valor cero
         funcion = 0;                                           // Volver a funcion de escucha de Serial
      }  



// --- COMPROBAR CONEXION A MAQUINA POD --- //
    
    if (dataReadFromSerial.substring(0,15) == "CHECKCONNECTION")
      { 
         Serial.print("PODCONNECTED");                          // Enviar señal de maquina POD conectada
         Serial. print('\n');                                   // New Line
         funcion = 0;                                           // Volver a funcion de escucha de Serial
      }  




// --- CALIBRACION --- //
    
    if (dataReadFromSerial.substring(0,19) == "CALIBRACIONMEDICION")
      { 
         Serial.print("CALIBRACIONSTART");                     // Enviar señal de maquina POD conectada
         Serial. print('\n');                                  // New Line

         for (int i = 0; i < 60; i++) {                        // Loop de 60 mediciones ( 3 segundos @ 50 ms delay)
           
         //Serial.print(hx711.read());                         // Imprimir valor de celda de carga
           Serial. print(random(350,365));                     // *DEV: Imprimir valor de celda de carga
           Serial. print('\n');                                // New Line
           delay(50);                                          // Delay de 50 ms
         }
         
         Serial. print("CALIBRACIONEND");                       // Fin de la calibracion
         Serial. print('\n');                                   // New Line Necesaria para evitar error
         
         funcion = 0;                                           // Volver a funcion de escucha de Serial
      }  







      dataReadFromSerial = "";
    // FIN Estados según la lectura del puerto serie //
}

void CNY70() {
  VTEJE++;
  }
