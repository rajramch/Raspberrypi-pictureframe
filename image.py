#!/usr/bin/env python3

import sys

from PIL import Image

from inky import Inky_Impressions_7

inky = Inky_Impressions_7()
saturation = 0.5

if len(sys.argv) == 1:
    print("""
Usage: {file} image-file
""".format(file=sys.argv[0]))
    sys.exit(1)

image = Image.open(sys.argv[1])
resizedimage = image.resize(inky.resolution)

if len(sys.argv) > 2:
    saturation = float(sys.argv[2])

inky.set_image(resizedimage, saturation=saturation)
inky.show()