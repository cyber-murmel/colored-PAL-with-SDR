#! /usr/bin/env python3
"""
This is a simple program with the purpose of generating a IQ sample file containing a PAL signal.
Dokumentation of the PAL signal:
https://en.wikipedia.org/wiki/PAL
http://www.retroleum.co.uk/electronics-articles/pal-tv-timing-and-voltages/
http://trznadel.info/kuba/avr/index2.php
http://www.ni.com/white-paper/4750/de/
http://stjarnhimlen.se/tv/tv.html
https://en.wikipedia.org/wiki/576i
http://www.batsocks.co.uk/readme/video_timing.htm
"""

from PIL import Image
import struct
import sys
from math import pi, sqrt, sin, cos

### timing relevant values
SUBC_FREQ = 4.43361875e6        # subcarrier frquency
SAMP_RATE = 13.5e6              # sample rate
TIME_PS = 1/SAMP_RATE           # time per sample
TIME_FP = 1.65e-6               # front porch time
TIME_VIDEO = 51.95e-6           # video time
TIME_BP = 5.7e-6                # back porch time
TIME_LINE = TIME_FP + TIME_VIDEO + TIME_BP
TIME_H_SYNC = 4.7e-6
TIME_S_SYNC = 2.35e-6           # short sync pulse
TIME_L_SYNC = 4.7e-6            # long sync pulse
FPS_I = 50
### chroma burst relevant valuesh
BURST_CYCLES = 10
BURST_TIME = BURST_CYCLES/SUBC_FREQ
BURST_DELAY = 0.9e-6
BURST_AMP = 4/14
# lines
NUMBER_LINES = 625
VISIB_LINES = 576
VISIB_PIXELS = 702
TIME_PIXEL = TIME_VIDEO/VISIB_PIXELS
### signal levels
LEVEL_SYNC = 0.0
LEVEL_BLANK = 0.285
LEVEL_BLACK = 0.339
LEVEL_WHITE = 1.0
### luminance RGB composition
Y_ARR = [ 0.299,  0.587,  0.114]
U_ARR = [-0.147, -0.289,  0.436]
V_ARR = [ 0.615, -0.515, -0.100]

lum_arr = []
chrom_arr = []

def t2n(time):
    return int(round(time*SAMP_RATE))

def m2a(matrix):
    return [item for sublist in matrix for item in sublist]

def write_front_porch():
    global lum_arr, chrom_arr
    lum_arr += [[LEVEL_BLANK, 0]] * t2n(TIME_FP)
    chrom_arr += [[0, 0]] * t2n(TIME_FP)

def write_back_porch(even):
    global lum_arr, chrom_arr
    lum_arr += [[LEVEL_BLANK, 0]] * t2n(BURST_DELAY)
    chrom_arr += [[0, 0]] * t2n(BURST_DELAY)
    lum_arr += [[LEVEL_BLANK, 0]] * t2n(BURST_TIME)
    chrom_arr += [[-sqrt(1/2)*BURST_AMP, (1 if even else -1)*sqrt(1/2)*BURST_AMP]] * t2n(BURST_TIME)
    lum_arr += [[LEVEL_BLANK, 0]] * t2n(TIME_BP-BURST_DELAY)
    chrom_arr += [[0, 0]] * t2n(TIME_BP-BURST_DELAY)

def write_horiz_sync():
    global lum_arr, chrom_arr
    lum_arr += [[LEVEL_SYNC, 0]] * t2n(TIME_H_SYNC)
    chrom_arr += [[0, 0]] * t2n(TIME_H_SYNC)

def write_short_sync():
    global lum_arr, chrom_arr
    lum_arr += [[LEVEL_SYNC, 0]] * t2n(TIME_S_SYNC)
    chrom_arr += [[0, 0]] * t2n(TIME_S_SYNC)
    lum_arr += [[LEVEL_BLANK, 0]] * t2n((TIME_LINE/2)-TIME_S_SYNC)
    chrom_arr += [[0, 0]] * t2n((TIME_LINE/2)-TIME_S_SYNC)

def write_long_sync():
    global lum_arr, chrom_arr
    lum_arr += [[LEVEL_SYNC, 0]] * t2n((TIME_LINE / 2) - TIME_L_SYNC)
    chrom_arr += [[0, 0]] * t2n((TIME_LINE / 2) - TIME_L_SYNC)
    lum_arr += [[LEVEL_BLANK, 0]] * t2n(TIME_L_SYNC)
    chrom_arr += [[0, 0]] * t2n(TIME_L_SYNC)

def write_blank_line(even):
    global lum_arr, chrom_arr
    write_horiz_sync()
    write_back_porch(even)
    lum_arr += [[LEVEL_BLACK, 0]] * VISIB_PIXELS * t2n(TIME_PIXEL)
    chrom_arr += [[0, 0]] * VISIB_PIXELS * t2n(TIME_PIXEL)
    write_front_porch()

def write_pixel(rgb_arr, even):
    global lum_arr, chrom_arr
    rgb_arr = [val/255 for val in rgb_arr]
    Y = sum([a*b for (a,b) in zip(rgb_arr,Y_ARR) ])
    U = sum([a*b for (a,b) in zip(rgb_arr,U_ARR) ])
    V = sum([a*b for (a,b) in zip(rgb_arr,V_ARR) ])
    lum_arr += [[LEVEL_BLACK + Y * (LEVEL_WHITE - LEVEL_BLACK), 0]] * t2n(TIME_PIXEL)
    chrom_arr += [[U, (1 if even else -1)*V]] * t2n(TIME_PIXEL)

def write_video(im, line_num, even):
    for x in range(VISIB_PIXELS):
        pixel = im[int(round(x / VISIB_PIXELS * 760)), line_num]
        write_pixel(pixel, even)

def write_line(im, line_num, even):
    write_horiz_sync()
    write_back_porch(even)
    write_video(im, line_num, even)
    write_front_porch()

def write_frame(im):
    global lum_arr, chrom_arr
    even = True
    # Field 1
    for _ in range(5): write_long_sync()
    for _ in range(5): write_short_sync()
    for _ in range(17):
        write_blank_line(even)
        even = not even
    for i in range(0, 576, 2):
        write_line(im, i, even)
        even = not even
    for _ in range(5): write_short_sync()

    even = not even
    
    # Field 2
    for _ in range(5): write_long_sync()
    for _ in range(5): write_short_sync()
    lum_arr += [[LEVEL_BLACK, 0]] * t2n(TIME_LINE / 2) * t2n(TIME_PIXEL)
    chrom_arr += [[0, 0]] * t2n(TIME_LINE / 2) * t2n(TIME_PIXEL)
    for _ in range(17):
        write_blank_line(even)
        even = not even
    for i in range(1, 576, 2):
        write_line(im, i, even)
        even = not even
    write_horiz_sync()
    write_back_porch(even)
    even = not even
    lum_arr += [[LEVEL_BLACK, 0]] * t2n(TIME_LINE/2 - TIME_H_SYNC - TIME_BP) * t2n(TIME_PIXEL)
    chrom_arr += [[0, 0]] * t2n(TIME_LINE/2 - TIME_H_SYNC - TIME_BP) * t2n(TIME_PIXEL)
    for _ in range(5): write_short_sync()

# array to samples
def a2s(array):
    return struct.pack('f'*len(array), *array)

def main():
    global lum_arr, chrom_arr
    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " <input_filename> [output_filename]")
        return

    input_filename = sys.argv[1]

    write_frame(Image.open(input_filename).load())

    lum_arr = m2a(lum_arr)
    chrom_arr = m2a(chrom_arr)

    samples = a2s(lum_arr)
    with open("y.out", "wb") as f:
        f.write(samples)
    
    samples = a2s(chrom_arr)
    with open("uv.out", "wb") as f:
        f.write(samples)

    exit()

if __name__ == "__main__" :
    main()