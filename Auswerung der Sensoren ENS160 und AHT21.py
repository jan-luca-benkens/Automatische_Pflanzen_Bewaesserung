#----------------------Eckdaten------------------------

# Datum: 09.04.2025
# Programm: Auswerten des ens160+aht21
# Programmierer: Benkens Jan-Luca

# ---------------------Hardware------------------------

# - ESP 32
# - Sensor ens160+aht21

#----------------------Software------------------------

# - Thonny
# - GitHub

#--------------------Beschreibung----------------------

# Im folgenden Programm werden die Sensordaten eines
# ens160 (Äquivalent CO²) und ein aht21 ermittelt.
# In der Kommandozeile wird die Temperatur in °C angegeben
# und das brechnete Äquivalent der CO²-Messung in
# ppm (parts per million) angegeben.

#------------------------------------------------------

#---------------------Bibliotheken---------------------

from machine import SoftI2C, Pin # Hardwareanschlüsse
import time					 # Zeit für Warteschleifen
from ahtx0 import AHT20
from ens_160 import ENS160
#------------------------------------------------------

#---------------------Initialisieren-------------------

i2c = SoftI2C(scl=Pin(4), sda=Pin(7))		 # Initialisieren des I2C

sensor_ens160 = ENS160(i2c)					 # Initialisieren des ENS160 Sensors

sensor_aht21 = AHT20(i2c)					 # Initialisieren des AHT21 Sensors

#------------------------------------------------------

#--------------------Hauptprogramm---------------------
while True:
    
    co2 = sensor_ens160.get_eco2()				 # Variabel erstellen
    
    temp = round(sensor_aht21.temperature,0)	 # Variabelerstellen

    print(temp, "°C")
    
    print(co2, "ppm")

    time.sleep(5)



