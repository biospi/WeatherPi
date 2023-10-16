#!/usr/bin/env python3

import os
import time
from datetime import datetime
import csv
import subprocess
import sys
import math
import pathlib
import weather

# os.chdir("/home/pi/weatherhat-python/examples")

import signal
import RPi.GPIO as GPIO
import ST7789
import yaml
from fonts.ttf import ManropeBold as UserFont
from PIL import Image, ImageDraw, ImageFont

import weatherhat
from weatherhat import history

collecting_data = False
power_saving = None
weather_app = False
weather_app_p = None

# Create a WeatherHat instance
sensor = weatherhat.WeatherHAT()

# Create csv file for data collection
file_path = '/home/pi/weatherdata.csv'
## Definitions
# Adjust this value based on your needs
# -17.5oC is an estimated error of having the HAT attached directly to the RPi that gets hot when turned on
OFFSET = 0  # Note: this is an estimate, you may need to adjust this value based on your needs

# Display settings
FPS = 10

SPI_SPEED_MHZ = 80

# Create LCD class instance.
disp = ST7789.ST7789(
    rotation=90,
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)

# Initialize display.
disp.begin()

# Width and height to calculate text position.
WIDTH = disp.width
HEIGHT = disp.height

# New canvas to draw on.
img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# Text settings.
font_size = 15
font = ImageFont.truetype(UserFont, font_size)
text_colour = (255, 255, 255)
back_colour = (0, 170, 170)

message = "A: Record data. \nTurn off to stop. \nB: Display data (30 secs). \nY: Energy saving mode."
size_x = 200
size_y = 80
# Calculate text position
x = (WIDTH - size_x) / 2
y = (HEIGHT / 2) - (size_y / 2)

# Draw background rectangle and write text.
draw.rectangle((0, 0, WIDTH, HEIGHT), back_colour)
draw.text((x, y), message, font=font, fill=text_colour)
disp.display(img)

# The buttons on Weather HAT are connected to pins 5, 6, 16 and 24
BUTTONS = [5, 6, 16, 24]

# These correspond to buttons A, B, X and Y respectively
LABELS = ['A', 'B', 'X', 'Y']

# Set up RPi.GPIO with the "BCM" numbering scheme
GPIO.setmode(GPIO.BCM)

# Buttons connect to ground when pressed, so we should set them up
# with a "PULL UP", which weakly pulls the input signal to 3.3V.
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def start_weather_app():
    print("Starting weather app...")
    # Code to execute when button B is pressed
    process = subprocess.Popen(["python3", "/home/pi/weatherhat-python/examples/weather.py"])
    # Wait for 10 seconds
    time.sleep(5)
    # Terminate the process after 30 seconds
    process.terminate()
    global weather_app
    weather_app = False


def collect_data():
    # Check if the file already exists
    if not os.path.exists(file_path):
        # If not, create it and write the header
        with open(file_path, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(
                ['Date', 'Time', 'Compensated Temperature', 'Uncompensated Temperature', 'Relative Humidity',
                 'Humidity', 'Pressure', 'Light (Lux)'])

    # Data collection loop
    sensor.temperature_offset = OFFSET
    sensor.update(
        interval=60.0)  # This can be adjusted (in seconds) to meet your needs. Note: you must also adjust the time.sleep on line 51
    timestamp = datetime.now()

    with open(file_path, mode="a", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            timestamp.strftime("%Y-%m-%d"),
            timestamp.strftime("%H:%M:%S"),
            sensor.temperature,
            sensor.device_temperature,
            sensor.relative_humidity,
            sensor.humidity,
            sensor.pressure,
            sensor.lux
        ])
    print("Data collected")


# "handle_button" will be called every time a button is pressed
# It receives one argument: the associated input pin.
def handle_button(pin):
    global collecting_data
    global weather_app
    global power_saving
    label = LABELS[BUTTONS.index(pin)]
    print("Button press detected on pin: {} label: {}".format(pin, label))

    if label == 'A':
        collecting_data = not collecting_data
        weather_app = False

    elif label == 'B':
        weather_app = True
        collecting_data = False

    elif label == 'Y':
        # Code to execute when button Y is pressed
        # Turn off backlight on Press Y
        power_saving = True

    elif label == 'X':
        # Code to execute when button X is pressed
        # Turn off backlight on Press X
        power_saving = False


# Loop through out buttons and attach the "handle_button" function to each
# We're watching the "FALLING" edge (transition from 3.3V to Ground) and
# picking a generous bouncetime of 100ms to smooth out button presses.
for pin in BUTTONS:
    GPIO.add_event_detect(pin, GPIO.FALLING, handle_button, bouncetime=500)

while True:

    print(f"status weather_app={weather_app} collecting_data={collecting_data} power_saving={power_saving}")

    if collecting_data:
        message = "Data collection started! \nA: Record data. \nY: Energy saving mode"
        # Redraw the screen with the new message
        size_x, size_y = 200, 80
        x = (WIDTH - size_x) / 2
        y = (HEIGHT / 2) - (size_y / 2)
        draw.rectangle((0, 0, WIDTH, HEIGHT), back_colour)
        draw.text((x, y), message, font=font, fill=text_colour)
        disp.display(img)
        collect_data()

    if not collecting_data:
        message = "A: Record data. \nTurn off to stop. \nB: Display data (30 secs). \nY: Energy saving mode."
        size_x = 200
        size_y = 80
        # Calculate text position
        x = (WIDTH - size_x) / 2
        y = (HEIGHT / 2) - (size_y / 2)
        # Draw background rectangle and write text.
        draw.rectangle((0, 0, WIDTH, HEIGHT), back_colour)
        draw.text((x, y), message, font=font, fill=text_colour)
        disp.display(img)

    if weather_app:
        weather_app_p = start_weather_app()

    if power_saving:
        disp.set_backlight(0)

    if not power_saving:
        disp.set_backlight(12)

    time.sleep(2.0)
