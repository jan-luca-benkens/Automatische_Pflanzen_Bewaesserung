#----------------------------------------------Eckdaten---------------------------------------------

# Erstellungsdatum: 22.04.2025
# Änderungsdatum: 24.04.2025
# Änderungsnummer: 1.1
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
# AHT21 in °C und des Capacitive Soil MoistureV2 in Bit-Format bzw als V.

#----------------------------------------------------------------------------------------------------

#--------------------------------------------Bibliotheken--------------------------------------------

from machine import Pin, SPI, SoftI2C,ADC
import st7789py as st7789
import vga2_16x32 as font
from ahtx0 import AHT20
from ens_160 import ENS160
import time

#------------------------------------------------------------------------------------------------------

#--------------------------------------------Initialisieren--------------------------------------------

# -TFT-Display ST7789V3

spi = SPI(1,
          baudrate = 20000000,
          polarity = 0,
          phase = 0,
          sck = Pin(35),			 # SCL Pin
          mosi = Pin(36),			 # SDA Pin
          miso = Pin(0))			 # BLK Pin

tft = st7789.ST7789(
    spi,
    240,
    320,
    reset = Pin(38,Pin.OUT),
    cs = Pin(40, Pin.OUT),
    dc = Pin(42, Pin.OUT),
    backlight = Pin(0, Pin.OUT),
    rotation = 4)

# -ENS160 und AHT21

i2c = SoftI2C(scl=Pin(4), sda=Pin(7))		 # Initialisieren des I2C

sensor_ens160 = ENS160(i2c)					 # Initialisieren des ENS160 Sensors

sensor_aht21 = AHT20(i2c)					 # Initialisieren des AHT21 Sensors

# -Capacitive Soil Moisture Sensor V2

soil = ADC(Pin(5))					 # Variabel für den PIN 4 Eingang mit ADC (Analog-Digital-Converter)
soil.atten(ADC.ATTN_11DB)			 # Lässt den Spannungsbereich 0 - 3.3V auf dem PIN 4 zu
soil.width(ADC.WIDTH_12BIT)			 # Die Analogwerte werden in 12 Bit Auflösung: 0 - 4095

#--------------------------------------------Hauptprogramm--------------------------------------------

# -Funktion Spannung in Prozent umrechnen

def prozentualerbereich(spannung, nass = 1.0, trocken = 2.7):			 # Bedinung für die Funktion definieren
    prozent_spannung = (trocken - spannung) / (trocken - nass) * 100	 # Rechnung für den Prozentwert
    return max(0, min(100, prozent_spannung))							 # Begrezung des Prozentwerts zwischen 0%-100%
    
# Zeitstartpunkt für Time Ticks deffinieren

startzeit = time.ticks_ms()

# Hintergrund des TFT-Displays weiß leuchten lassen

tft.fill(st7789.WHITE)

#--------------------------------------------while Schleife--------------------------------------------

while True:
    
    aktuellezeit = time.ticks_ms() 
    
    if time.ticks_diff(aktuellezeit, startzeit) >= 5000:
    
        volt = soil.read() / 4095 * 3.3 
        
        prozent = prozentualerbereich(volt)
        
        co2 = sensor_ens160.get_eco2() 
        
        temp = round(sensor_aht21.temperature,0)    
        
        print(co2, temp, round(volt,2), round (prozent,2))
        
       
        tft.text(font, "Werte:", 10, 40, st7789.BLUE, st7789.WHITE)
        tft.text(font, "Temp:{} C".format(temp), 10, 80, st7789.BLUE, st7789.WHITE)
        tft.text(font, "Luft:{} ppm".format(co2), 10, 120, st7789.BLUE, st7789.WHITE)
        
        tft.fill_rect(10, 160, 200, 32, st7789.WHITE)		 # Löscht den alten Textbereich
        tft.text(font, "Boden:{} %".format(round(prozent,0)), 10, 160, st7789.BLUE, st7789.WHITE)
            
        
        startzeit = aktuellezeit
    
    
