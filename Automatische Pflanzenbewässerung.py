#----------------------------------------------Eckdaten---------------------------------------------

# Erstellungsdatum: 22.04.2025
# Änderungsdatum: 02.05.2025
# Änderungsnummer: 1.5
# Programm: Automatische Pflanzenbewässerung
# Programmierer: Benkens Jan-Luca

# ---------------------------------------------Hardware----------------------------------------------

# - ESP 32
# - TFT Display IC: ST7789V3
# - ENS160 und AHT21
# - Capacitive Soil Moisture Sensor V2

#----------------------------------------------Software----------------------------------------------

# - Thonny
# - GitHub

#--------------------------------------------Beschreibung--------------------------------------------

# Im folgenden Programm wird ein TFT-Display angesteuert.
# Welches die Ausgewerteten Sensorwert vom ENS160 in ppm,
# AHT21 in °C und des Capacitive Soil MoistureV2 in ein Prozentwert,
# auf dem TFT-Display ausgibt.
# Sobald bestimmte CO²-Werte erreicht sind, wird dies farblich auf dem
# TFT-Display deutlich (Grün = alles Gut; Gelb = Langsam mal Lüften;
# Rot = Schlecht, dringend Lüften).
# Im nachfolgenden werden die Sensordaten über ein Netzwerk zu einem Broker (MQTT) geschickt.
# Der Broker (MQTT) dient als Schnittstelle, wodurch die Sensordaten durch abonnieren des Brokkers
# abgefragt werden können.

#----------------------------------------------------------------------------------------------------

#--------------------------------------------Bibliotheken--------------------------------------------

from machine import Pin, SPI, SoftI2C,ADC				 # Zugriff auf GPIO, SPI, I2C, ADC
import st7789py as st7789								 # Bibliothek für ST7789 TFT-Display
import vga2_16x32 as font								 # Schriftart für das Display
from ahtx0 import AHT20									 # Bibliothek für AHT21 (Temperatur)
from ens_160 import ENS160								 # Bibliothek für ENS160 (Luftqualität)
import time												 # Zeitsteuerung
import json												 # Script
import network											 # Zugriff auf Netzwerkfunktionen
from umqtt.simple import MQTTClient						 # zugriff auf MQTT

#------------------------------------------------------------------------------------------------------

#--------------------------------------------Initialisieren--------------------------------------------

# -TFT-Display ST7789V3

spi = SPI(1,
          baudrate = 20000000,
          polarity = 0,
          phase = 0,
          sck = Pin(35),			 # SCL Pin
          mosi = Pin(36),			 # SDA Pin; Mosi: Datenleitung zum Display
          miso = Pin(0))			 # BLK Pin; MISO: wird nicht benutzt

tft = st7789.ST7789(
    spi,
    240, 320,							 # Auflösung des Displays
    reset = Pin(38,Pin.OUT),			 # Reset-Pin
    cs = Pin(40, Pin.OUT),				 # Chip-Select
    dc = Pin(42, Pin.OUT),				 # Daten-/Command-Pin
    backlight = Pin(0, Pin.OUT),		 # Hintergrundbeleuchtung
    rotation = 4)						 # Anzeigeausrichtung

# -I2C-Bus für ENS160 und AHT21

i2c = SoftI2C(scl=Pin(4), sda=Pin(7))		 # Software-I2C
sensor_ens160 = ENS160(i2c)					 # Initialisieren des ENS160 Sensors
sensor_aht21 = AHT20(i2c)					 # Initialisieren des AHT21 Sensors

# -ADC Capacitive Soil Moisture Sensor V2

soil = ADC(Pin(5))					 # Variabel für den PIN 5 Eingang mit ADC (Analog-Digital-Converter)
soil.atten(ADC.ATTN_11DB)			 # Lässt den Spannungsbereich 0 - 3.3V auf dem PIN 4 zu
soil.width(ADC.WIDTH_12BIT)			 # Die Analogwerte werden in 12 Bit Auflösung: 0 - 4095

# -Variabel für Pumpe

pumpe = Pin(8,Pin.OUT)						 # Pin für High(1) bzw Low(0) für die Pumpe
pumpe_on = False

# WLAN-Verbindung herstellen
SSID = "Holzmodem1884"					 # Wlan "Name"
PASSWORD = "Lassmichein123"				 # Passwort des Wlan

wlan = network.WLAN(network.STA_IF)		 # Wlan-Client erzeugen
wlan.active(False)						 # Wlan Reset
wlan.active(True)						 # Wlan einschalten

if not wlan.isconnected():				 # Testen der WLAN Verbindung
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        print("Verbinde mit WLAN...")
        time.sleep(1)


print("WLAN verbunden:", wlan.ifconfig()) # Konfigurationsdaten vom Wlan

# MQTT-Konfiguration
BROKER = "192.168.178.78"  				 # IP-Adresse des Brokers (Laptop,PC)
PORT = 1883								 # Port definieren
CLIENT_ID = "JLB"						 # Client-Id vom MQTT
TOPIC1 = "Pflanze/Auto/Bewaesserung"	 # Topic des MQTT Broker
TOPIC2 = "Pump/EIN/AUS"					 # Topic 

print("Mit MQTT-Broker verbunden.")


#----------------------------------------------Funktionen---------------------------------------------

# -Funktion zur Auswertung der MQTT-Message

def sub_pumpe(topic, msg):
    
    daten = json.loads(msg)
    print(daten)
    schalter = daten.get('Schalter')# Alternativ: schalter = (daten['Schalter']) 
    print(schalter)
    if schalter == 'ON':# Pumpe einschalten     
 
        global pumpe_on					 # Wichtig: Globale Variable nutzen und keine neue Variable erzeugen
         
        pumpe_on = True

    else:								 # sonst ausschalten
        global pumpe_on 
        pumpe_on = False 

# -Funktion Spannung in Prozent umrechnen
#  Eingabe: Spannung in Volt
#  Rückgabe: Prozentualer Wert für die Feuchtigkeit (zwischen 0% und 100%)

def prozentualerbereich(spannung, nass = 1.0, trocken = 2.7):			 # Bedinung für die Funktion definieren
    prozent_spannung = (trocken - spannung) / (trocken - nass) * 100	 # Rechnung für den Prozentwert
    return max(0, min(100, prozent_spannung))							 # Begrezung des Prozentwerts zwischen 0%-100%

# -Funktionen zum Ein/Ausschalten der Pumpe

def pumpe_ein():
    pumpe.value(1)

def pumpe_aus():
    pumpe.value(0)

# -Funktion für Displayfarbe und Displaytext 

def display_farbe(st_farbe, temp, co2, prozent):
    
    tft.fill(st_farbe)
    tft.text(font, "Werte:", 10, 40, st7789.BLACK, st_farbe)
    tft.text(font, "Temp:{} C".format(temp), 10, 80, st7789.BLACK, st_farbe)
    tft.text(font, "Luft:{} ppm".format(co2), 10, 120, st7789.BLACK, st_farbe)
    
    tft.fill_rect(10, 160, 200, 32, st_farbe)				 # Löscht den alten Textbereich
    tft.text(font, "Boden:{} %".format(prozent,0), 10, 160, st7789.BLACK, st_farbe)
    

# MQTT-Client einrichten
client = MQTTClient(CLIENT_ID, BROKER, PORT, keepalive = 30)
client.set_callback(sub_pumpe) 
time.sleep(1)
client.connect()
client.subscribe(TOPIC2) 

#---------------------------------------------Hauptprogramm--------------------------------------------

startzeit = time.ticks_ms()										 # Zeitstartpunkt für Time Ticks deffinieren

tft.fill(st7789.WHITE)											 # Hintergrund des TFT-Displays weiß leuchten lassen

while True:														 # Dauerschleife zur regelmäßigen Datenerfassung    
    
    aktuellezeit = time.ticks_ms()
    
    if time.ticks_diff(aktuellezeit, startzeit) >= 5000:				 # Messung alle 5 Sekunden ausführen
    
        spannung = soil.read() / 4095 * 3.3								 # Bodenfeuchtigkeit in Volt umrechnen        
        prozent = round (prozentualerbereich(spannung),0)				 # Umrechnung in Prozent        
        co2 = sensor_ens160.get_eco2()									 # CO²-Messung (eCO²) vom ENS160        
        temp = round(sensor_aht21.temperature,0)						 # Temperatur vom AHT21    
        
        print("Luftqualität",co2,"%","Temperatur", temp,"°C","Spannung",
              round(spannung,2),"V","Bodenfeuchte",round (prozent,2),"%") # Werte zur Kontrolle in der Kommandozeile ausgeben
        print("")														  # Leere Spalte in Komandozeile einfügen
        
        #--------Daten auf dem TFT-Display anzeigen lassen--------
        
        if co2 < 600:            
            display_farbe(st7789.GREEN, temp, co2, prozent)
        elif co2 < 1000:
            display_farbe(st7789.YELLOW, temp, co2, prozent)
        else:
            display_farbe(st7789.RED, temp, co2, prozent)

        
        #--------Daten für MQTT bereit machen und senden--------
        
        sensor_daten = {"Bodenfeuchtigkeit": prozent, "Luftqualitaet": co2, "Temperatur": temp}	 # Sensor daten für JSON vorbereiten
        
        json_string = json.dumps(sensor_daten)														 # Json-String erstellen
         
        # Versuch von daten als JSON Format zum Brokker zu senden  
        try:
            
            client.publish(TOPIC1, json_string)
            print(f"Nachricht gesendet: {json_string}")
        
        # Fehlermeldung beim Senden der MQTT-Nachricht ausgeben
        
        except OSError as e:
            print("Fehler beim Senden der MQTT-Nachricht:", e)
            
            #Versuch eine erneute Verbindung zum Brokker herzustellen
            
            try:
                client.connect()
                print("Erneut mit MQTT-Broker verbunden.")
                
            except:
                print("Wiederverbindung zum Broker fehlgeschlagen.")
                
        #--------Pumpe EIN/AUS schalten bei bestimmten Grenzwerten--------
                
        if pumpe_on is False :
            
            if prozent > 60:											 # Bodenfeuchtigkeit über 60%
                pumpe_aus()												 # pumpe auf 0 setzen
        
            elif prozent < 40:											 # Bodenfeuchtigkeit unter 40%
                pumpe_ein()												 # pumpe auf 1 setzen
                    
        else:
            if pumpe_on:
                pumpe_ein()
            
            else:
                pumpe_aus()
                
        client.check_msg() 											 # Warten, bis eine neue Nachricht vorliegt.
        
        startzeit = aktuellezeit									 # Startzeit zurücksetzen
         
        
        
    
    





