#----------------------------------------------Eckdaten---------------------------------------------

# Erstellungsdatum: 22.04.2025
# Änderungsdatum: 06.05.2025
# Änderungsnummer: 2.1
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

"""Im folgenden Programm wird ein TFT-Display angesteuert.
Welches die Ausgewerteten Sensorwert vom ENS160 in ppm,
AHT21 in °C und des Capacitive Soil MoistureV2 in ein Prozentwert,
auf dem TFT-Display ausgibt.
Sobald bestimmte CO²-Werte erreicht sind, wird dies farblich auf dem
TFT-Display deutlich (Grün = alles Gut; Gelb = Langsam mal Lüften;
Rot = Schlecht, dringend Lüften).
Im nachfolgenden werden die Sensordaten über ein Netzwerk zu einem Broker (MQTT) gesendet.
Über Node-red werden die Sensordaten vom MQTT Brokervabgerufen und weiter verarbeitet.
Zudem werden drei verschiedene Topic`s vom MQTT in diesem Code subscribe.
Zwei Topic`s sind die für das erhalten der Grenzwerte für die Bodenfeuchtigkeit.
Das dritte Topic ist für die Manuelle ansteuerung der Pumpe.

Die Sensordaten werden alle 2 Sekunden zum MQTT gesendet um ein ca. Echtzeitwerden zu bilden.
Alle 30 Sekunden werden diese Sensordaten für die Datenbank erneut gesendet"""

#----------------------------------------------------------------------------------------------------

#--------------------------------------------Bibliotheken--------------------------------------------

from machine import Pin, SPI, SoftI2C,ADC				 # Zugriff auf GPIO, SPI, I2C, ADC
import st7789py as st7789								 # Bibliothek für ST7789 TFT-Display
import vga2_16x32 as font								 # Schriftart für das Display
from ahtx0 import AHT20									 # Bibliothek für AHT21 (Temperatur)
from ens_160 import ENS160								 # Bibliothek für ENS160 (Luftqualität)
import time												 # Zeitsteuerung
import json												 # Umwandeln auf JSON-Objekte 
import network											 # Zugriff auf Netzwerkfunktionen
from umqtt.simple import MQTTClient						 # Zugriff auf MQTT

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
    reset = Pin(37,Pin.OUT),			 # Reset-Pin
    cs = Pin(39, Pin.OUT),				 # Chip-Select
    dc = Pin(38, Pin.OUT),				 # Daten-/Command-Pin
    backlight = Pin(0, Pin.OUT),		 # Hintergrundbeleuchtung
    rotation = 4)						 # Anzeigeausrichtung

# -I2C-Bus für ENS160 und AHT21

i2c = SoftI2C(scl=Pin(7), sda=Pin(6))	 # Software-I2C
sensor_ens160 = ENS160(i2c)				 # Initialisieren des ENS160 Sensors
sensor_aht21 = AHT20(i2c)				 # Initialisieren des AHT21 Sensors

# -ADC Capacitive Soil Moisture Sensor V2

soil = ADC(Pin(10))						 # Variabel für den PIN 5 Eingang mit ADC (Analog-Digital-Converter)
soil.atten(ADC.ATTN_11DB)				 # Lässt den Spannungsbereich 0 - 3.3V auf dem PIN 4 zu
soil.width(ADC.WIDTH_12BIT)				 # Die Analogwerte werden in 12 Bit Auflösung: 0 - 4095

# -Variabel für Pumpe

pumpe = Pin(8,Pin.OUT)					 # Pin für High(1) bzw Low(0) für die Pumpe

pumpen_status = 'Kein Zustand vorhanden'

# -Globale Variabeln

oberergrenzwert = 0						 # Globale Variabel Wert 0 geben 
unterergrenzwert = 0					 # Globale Variabel Wert 0 geben  
pumpe_on = False						 # Globale Variabel auf False setzen

# WLAN-Verbindung herstellen
SSID = "XXXX"				 # Wlan "Name"
PASSWORD = "XXXX"		 # Passwort des Wlan

wlan = network.WLAN(network.STA_IF)		 # Wlan-Client erzeugen
wlan.active(False)						 # Wlan Reset
wlan.active(True)						 # Wlan einschalten

if not wlan.isconnected():				 # Testen der WLAN Verbindung
    wlan.connect(SSID, PASSWORD)		 # Mit dem Wlan verbinden
    while not wlan.isconnected():
        print("Verbinde mit WLAN...")	 # Wenn noch keine Verbindung hergestellt ist
        time.sleep(1)


print("WLAN verbunden:", wlan.ifconfig()) # Konfigurationsdaten vom Wlan

# MQTT-Konfiguration
BROKER = "192.168.178.122"  			 # IP-Adresse des Brokers (Laptop,PC)
PORT = 1883								 # Port definieren
CLIENT_ID = "JLB"						 # Client-Id vom MQTT
TOPIC1 = "Pflanze/Auto/Bewaesserung"	 # Topic für Sensordaten "Echtzeit"
TOPIC3 = "Datenbank/Sensoren/Werte"					 # Topic für Sensordaten für die Datenbank
TOPIC4 = b"Untererschwellenwert"		 # Topic für Grenzwert Bodenfeuchtigkeit 
TOPIC5 = b"Obererschwellenwert"			 # Topic für Grenzwert Bodenfeuchtigkeit
TOPIC2 = b"Pumpe/EIN/AUS"				 # Topic für manuelle Ansteuerung

#----------------------------------------------Funktionen---------------------------------------------

# -Funktion für callback der Topic`s
#  vergleichen vom MQTT topic und den Variabeln TOPIC

def mqtt_callback(topic, msg):			 # Funktion definieren
    
    if topic == TOPIC5:
        sub_oberergrenzwert(topic, msg)
        
    elif topic == TOPIC2:
        sub_pumpe(topic, msg)
        
    elif topic == TOPIC4:
        sub_untergrenzwert(topic, msg)

# -Funktion zur Auswertung der MQTT-Message vom Topic Pumpe/EIN/AUS

def sub_pumpe(topic, msg):				 # Funktion definieren
    
    daten = json.loads(msg)				 # msg in JSON-Format wandeln
    print(daten)
    schalter = daten.get('Schalter')	 # Wert "ON" aus der Variabel "daten" erhalten
    print(schalter)
    if schalter == 'ON':				 # Pumpe einschalten     
 
        global pumpe_on					 # Globale Variable definieren 
         
        pumpe_on = True					 # Globale Variable auf True setzen

    else:								 # sonst ausschalten
        global pumpe_on
        
        pumpe_on = False 				 # Globale Variable aus False setzen

# -Funktion zur Auswertung der MQTT-Message vom Topic Obererschwellenwert

def sub_oberergrenzwert(topic, msg):	 # Funktion definieren
    
    daten = json.loads(msg)				 # msg in JSON-Format wandeln
    print(daten)
    wert = daten.get('oberergrenzwert')	 # Wert aus der Variabel daten erhalten
    print("Wert:",wert)
    
    global oberergrenzwert				 # Globale Variable definieren
    
    oberergrenzwert = wert				 # Globale Variabel nimmt den Wert von der Variabel Wert an

# -Funktion zur Auswertung der MQTT-Message vom Topic Untererschwellenwert

def sub_untergrenzwert(topic, msg):		 # Funktion definieren
    
    daten = json.loads(msg)				 # msg in JSON-Format wandeln
    print(daten)
    wert = daten.get('unterergrenzwert') # Wert aus der Variabel daten erhalten 
    print("Wert:",wert)
    
    global unterergrenzwert				 # Globale Variable definieren
    
    unterergrenzwert = wert				 # Globale Variabel nimmt den Wert von der Variabel Wert an

# -Funktion Spannung in Prozent umrechnen
#  Eingabe: Spannung in Volt
#  Rückgabe: Prozentualer Wert für die Feuchtigkeit (zwischen 0% und 100%)

def prozentualerbereich(spannung, nass = 1.0, trocken = 2.7):			 # Bedinung für die Funktion definieren
    prozent_spannung = (trocken - spannung) / (trocken - nass) * 100	 # Rechnung für den Prozentwert
    return max(0, min(100, prozent_spannung))							 # Begrezung des Prozentwerts zwischen 0%-100%

# -Funktionen zum Ein/Ausschalten der Pumpe

def pumpe_ein():						 # Funktion definieren
    pumpe.value(1)						 # Variable pumpe auf 1 setzen

def pumpe_aus():						 # Funktion definieren
    pumpe.value(0)						 # Variable pumpe auf 0 setzen

# -Funktion für Displayfarbe und Displaytext 

def display_farbe(st_farbe, temp, co2, prozent):									 # Funktion definieren
    
    tft.fill(st_farbe)
    tft.text(font, "Werte:", 10, 40, st7789.BLACK, st_farbe)
    tft.text(font, "Temp:{} C".format(temp), 10, 80, st7789.BLACK, st_farbe)
    tft.text(font, "Luft:{} ppm".format(co2), 10, 120, st7789.BLACK, st_farbe)
    
    tft.fill_rect(10, 160, 200, 32, st_farbe)										 # Löscht den alten Textbereich
    tft.text(font, "Boden:{} %".format(prozent), 10, 160, st7789.BLACK, st_farbe)

# MQTT-Client einrichten

client = MQTTClient(CLIENT_ID, BROKER, PORT, keepalive = 30)
client.set_callback(mqtt_callback)
client.connect()
print("Mit MQTT-Broker verbunden.")

client.subscribe(TOPIC2)
client.subscribe(TOPIC5)
client.subscribe(TOPIC4)



#---------------------------------------------Hauptprogramm--------------------------------------------

startzeit = time.ticks_ms()										 # Zeitstartpunkt für Time Ticks deffinieren
startzeit2 = time.ticks_ms()									 # Zeitstartpunkt für Time Ticks deffinieren

tft.fill(st7789.WHITE)											 # Hintergrund des TFT-Displays weiß leuchten lassen

while True:														 # Dauerschleife zur regelmäßigen Datenerfassung    
    client.check_msg() 											 # Warten, bis eine neue Nachricht vorliegt.

    aktuellezeit = time.ticks_ms()
    #------- Abfragen der Sensoren-------
    spannung = soil.read() / 4095 * 3.3								 # Bodenfeuchtigkeit in Volt umrechnen        
    prozent = round (prozentualerbereich(spannung),0)				 # Umrechnung in Prozent        
    co2 = sensor_ens160.get_eco2()									 # CO²-Messung (eCO²) vom ENS160        
    temp = round(sensor_aht21.temperature,0)						 # Temperatur vom AHT21
    
    #--------Daten für MQTT bereit machen und senden--------
        
    sensor_daten = {"Bodenfeuchtigkeit": prozent, "Luftqualitaet": co2, "Temperatur": temp, "Pumpe": pumpen_status}	 # Sensor daten für JSON vorbereiten
        
    json_string = json.dumps(sensor_daten)														 # Json-String erstellen
    
    #--------Pumpe EIN/AUS Automatisch oder Manuell--------
            
    if pumpe_on is False :											 # Bedingung der globalen Variabel
        
        if prozent >= oberergrenzwert:								 # Bodenfeuchtigkeit über 60%
            pumpe_aus()												 # pumpe auf 0 setzen
            pumpen_status = 'Pumpe ist Ausgeschaltet'
    
        elif prozent < unterergrenzwert:							 # Vergleichen von prozent und Unterergrenzwert 
            pumpe_ein()												 # pumpe auf 1 setzen
            pumpen_status = 'Pumpe ist Eingeschaltet'    
    else:															 # Sonst andere Bedingungen
        if pumpe_on:
            pumpe_ein()												 # Funktion ausführen
            pumpen_status = 'Pumpe ist Eingeschaltet'
            
        else:
            pumpe_aus()												 # Funktion ausführen
            pumpen_status = 'Pumpe ist Ausgeschaltet'
            
    #--------Senden der Sensordaten für die Datenbank------
    
    if time.ticks_diff(aktuellezeit, startzeit2) >= 60000:			 # Zeit festlegen 60 Sekunden
        
        # Versuch von daten als JSON Format zum Brokker zu senden  
        try:
            
            client.publish(TOPIC3, json_string)						 # Nachricht an MQTT senden
            print(f"Nachricht gesendet Datenbank: {json_string}")
        
        # Fehlermeldung beim Senden der MQTT-Nachricht ausgeben
        
        except OSError as e:
            print("Fehler beim Senden der MQTT-Nachricht:", e)
            
            #Versuch eine erneute Verbindung zum Brokker herzustellen
            
            try:
                client.connect()
                print("Erneut mit MQTT-Broker verbunden.")
                
            except:
                print("Wiederverbindung zum Broker fehlgeschlagen.")
            
        startzeit2 = aktuellezeit									 # Startzeit zurücksetzen
                
    #--------Senden der Sensordaten für die Echtzeitanzeige------
    
    if time.ticks_diff(aktuellezeit, startzeit) >= 1000:			 # Messung jede Sekunden ausführen
    
        print("Luftqualität",co2,"%","Temperatur", temp,"°C","Spannung",
              round(spannung,2),"V","Bodenfeuchte",round (prozent,2),"%")	 # Werte zur Kontrolle in der Kommandozeile ausgeben
        print("")															 # Leere Spalte in Komandozeile einfügen
        
        #--------Displayfarbe bestimmen--------
        
        if co2 < 600:														 # CO²-Wertebereich bis 600ppm            
            display_farbe(st7789.GREEN, temp, co2, prozent)					 # Displayfarbe Grün (CO²-Wert ist Gut)
            
        elif co2 < 1000:													 # CO²-Wertebereich von 601 bis 1000ppm
            display_farbe(st7789.YELLOW, temp, co2, prozent)				 # Displayfarbe Gelb (CO²-Wert ist Okay)
            
        else:																 # CO²-Wertebereich über 1000ppm
            display_farbe(st7789.RED, temp, co2, prozent)					 # Displayfarbe Rot (CO²-Wert ist Schlecht)

         
        # Versuch von daten als JSON Format zum Brokker zu senden  
        try:
            
            client.publish(TOPIC1, json_string)						 # Nachricht an MQTT senden
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
        
        startzeit = aktuellezeit									 # Startzeit zurücksetzen