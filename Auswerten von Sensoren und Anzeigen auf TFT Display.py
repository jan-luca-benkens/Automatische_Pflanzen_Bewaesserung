#----------------------------------------------Eckdaten---------------------------------------------

# Erstellungsdatum: 22.04.2025
# Änderungsdatum: 28.04.2025
# Änderungsnummer: 1.3
# Programm: Auswerten von Sensoren und Ansteuerung des TFT Displays
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

#----------------------------------------------------------------------------------------------------

#--------------------------------------------Bibliotheken--------------------------------------------

from machine import Pin, SPI, SoftI2C,ADC				 # Zugriff auf GPIO, SPI, I2C, ADC
import st7789py as st7789								 # Bibliothek für ST7789 TFT-Display
import vga2_16x32 as font								 # Schriftart für das Display
from ahtx0 import AHT20									 # Bibliothek für AHT21 (Temperatur)
from ens_160 import ENS160								 # Bibliothek für ENS160 (Luftqualität)
import time												 # Zeitsteuerung

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

#----------------------------------------------Funktionen---------------------------------------------

# -Funktion Spannung in Prozent umrechnen
# -Eingabe: Spannung in Volt
# -Rückgabe: Prozentualer Wert für die Feuchtigkeit (zwischen 0% und 100%)

def prozentualerbereich(spannung, nass = 1.0, trocken = 2.7):			 # Bedinung für die Funktion definieren
    prozent_spannung = (trocken - spannung) / (trocken - nass) * 100	 # Rechnung für den Prozentwert
    return max(0, min(100, prozent_spannung))							 # Begrezung des Prozentwerts zwischen 0%-100%

#---------------------------------------------Hauptprogramm--------------------------------------------

startzeit = time.ticks_ms()										 # Zeitstartpunkt für Time Ticks deffinieren

tft.fill(st7789.WHITE)											 # Hintergrund des TFT-Displays weiß leuchten lassen

while True:														 # Dauerschleife zur regelmäßigen Datenerfassung
    
    aktuellezeit = time.ticks_ms()
    
    if time.ticks_diff(aktuellezeit, startzeit) >= 5000:				 # Messung alle 5 Sekunden ausführen
    
        spannung = soil.read() / 4095 * 3.3								 # Bodenfeuchtigkeit in Volt umrechnen
        
        prozent = prozentualerbereich(spannung)							 # Umrechnung in Prozent
        
        co2 = sensor_ens160.get_eco2()									 # CO²-Messung (eCO²) vom ENS160
        
        temp = round(sensor_aht21.temperature,0)						 # Temperatur vom AHT21    
        
        print(co2, temp, round(spannung,2), round (prozent,2))			 # Werte zur Kontrolle in der Kommandozeile ausgeben
        
        #--------Daten auf dem TFT-Display anzeigen lassen--------
        
        if co2 < 600:													 # CO²-Wert ist gut; man muss nicht Lüften
            
            tft.fill(st7789.GREEN)
            tft.text(font, "Werte:", 10, 40, st7789.BLACK, st7789.GREEN)
            tft.text(font, "Temp:{} C".format(temp), 10, 80, st7789.BLACK, st7789.GREEN)
            tft.text(font, "Luft:{} ppm".format(co2), 10, 120, st7789.BLACK, st7789.GREEN)
            
            tft.fill_rect(10, 160, 200, 32, st7789.GREEN)				 # Löscht den alten Textbereich
            tft.text(font, "Boden:{} %".format(round(prozent,0)), 10, 160, st7789.BLACK, st7789.GREEN)
            
        elif 600< co2 <1000:											 # CO²-Wert ist OK; man sollte langsam lüften
            
            tft.fill(st7789.YELLOW)
            tft.text(font, "Werte:", 10, 40, st7789.BLACK, st7789.YELLOW)
            tft.text(font, "Temp:{} C".format(temp), 10, 80, st7789.BLACK, st7789.YELLOW)
            tft.text(font, "Luft:{} ppm".format(co2), 10, 120, st7789.BLACK, st7789.YELLOW)
            
            tft.fill_rect(10, 160, 200, 32, st7789.YELLOW)				 # Löscht den alten Textbereich
            tft.text(font, "Boden:{} %".format(round(prozent,0)), 10, 160, st7789.BLACK, st7789.YELLOW)
            
        elif co2 <1000:													 # CO²-Wert ist schlecht; dringend Lüften!
            
            tft.fill(st7789.RED)
            tft.text(font, "Werte:", 10, 40, st7789.BLACK, st7789.RED)
            tft.text(font, "Temp:{} C".format(temp), 10, 80, st7789.BLACK, st7789.RED)
            tft.text(font, "Luft:{} ppm".format(co2), 10, 120, st7789.BLACK, st7789.RED)
            
            tft.fill_rect(10, 160, 200, 32, st7789.RED)				 # Löscht den alten Textbereich
            tft.text(font, "Boden:{} %".format(round(prozent,0)), 10, 160, st7789.BLACK, st7789.RED)
            

        
        startzeit = aktuellezeit									 # Startzeit zurücksetzen
    
    


