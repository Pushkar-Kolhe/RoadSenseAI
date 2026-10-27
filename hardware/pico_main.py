"""MicroPython for Raspberry Pi Pico 2 (copy to the Pico as main.py with Thonny).
NOT TESTED on real hardware - written from standard wiring; verify pins on your board.

Wiring (typical):
  GPS NEO-6M  : TX -> GP1 (UART0 RX), RX -> GP0 (UART0 TX), VCC 3.3V, GND
  MPU-6050 IMU: SDA -> GP4, SCL -> GP5 (I2C0), VCC 3.3V, GND
The Pico prints one JSON line per event over USB serial; the PC bridge forwards it to Flask.
The Pico has no real-time clock: the PC stamps the time when the line arrives.
"""
import json
import time
from machine import I2C, UART, Pin
from math import sqrt

SPIKE_G = 0.6              # vibration threshold above gravity (tune on a real road)
MPU = 0x68

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
i2c.writeto_mem(MPU, 0x6B, b"\x00")           # wake MPU-6050
gps = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
lat = lon = None


def read_g():
    d = i2c.readfrom_mem(MPU, 0x3B, 6)
    vals = []
    for k in range(0, 6, 2):
        v = (d[k] << 8) | d[k + 1]
        vals.append((v - 65536 if v > 32767 else v) / 16384.0)   # +/-2g range
    return sqrt(vals[0] ** 2 + vals[1] ** 2 + vals[2] ** 2)


def nmea_to_deg(value, hemi):
    deg = int(float(value) / 100)
    minutes = float(value) - deg * 100
    out = deg + minutes / 60
    return -out if hemi in ("S", "W") else out


def parse_gps(line):
    global lat, lon
    p = line.split(",")
    if p[0].endswith("RMC") and len(p) > 6 and p[2] == "A":      # A = valid fix
        lat, lon = nmea_to_deg(p[3], p[4]), nmea_to_deg(p[5], p[6])


buf = b""
last_event = 0
while True:
    if gps.any():
        buf += gps.read()
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            try:
                parse_gps(line.decode().strip())
            except Exception:
                pass
    peak = abs(read_g() - 1.0)                 # deviation from 1 g at rest
    now = time.ticks_ms()
    if peak > SPIKE_G and time.ticks_diff(now, last_event) > 1000:
        last_event = now
        print(json.dumps({"peak_g": round(peak, 3), "latitude": lat, "longitude": lon}))
    time.sleep_ms(10)
