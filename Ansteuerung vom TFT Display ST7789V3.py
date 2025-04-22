#----------------------Eckdaten------------------------

# Datum: 10.04.2025
# Programm: Ansteuern eines TFT Displays
# Programmierer: Benkens Jan-Luca

# ---------------------Hardware------------------------

# - ESP 32
# - TFT Display IC: ST7789V3

#----------------------Software------------------------

# - Thonny
# - GitHub

#--------------------Beschreibung----------------------

# Im folgenden Programm wird ein TFT-Display angesteuert.
# Welches zum Test nur paar Beispiel anzeigen hat.

#------------------------------------------------------

#---------------------Bibliotheken---------------------
from machine import Pin, SPI, SoftI2C
import st7789py as st7789
import vga2_16x32 as font
import time
#------------------------------------------------------

#---------------------Initialisieren-------------------

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

#--------------------Hauptprogramm---------------------

while True:
    
    tft.fill(st7789.WHITE)
    tft.text(font, "Werte", 10, 40, st7789.BLUE, st7789.WHITE)
    tft.text(font, "Temp", 10, 80, st7789.BLUE, st7789.WHITE)
    tft.text(font, "Luft", 10, 140, st7789.BLUE, st7789.WHITE)
    
    time.sleep(5)