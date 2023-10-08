from flask import Flask, render_template, request, url_for, flash, redirect
from PIL import Image
from inky import Inky_Impressions_7

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

@app.route('/', methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        img = request.files['img']
        change_image(img)
        return render_template('done.html')
    return render_template('index.html')

@app.route('/done')
def done():
    return render_template('done.html')

def change_image(img):
    inky = Inky_Impressions_7()
    saturation = 0.5
    image = Image.open(img)

    img_asp_rat = image.width /image.height
    if(img_asp_rat < 800 / 480):
        multiplier = image.width / 800
        new_height = 480 * multiplier
        diff = image.height - new_height
        diff = int(diff/2)
        crop_image = image.crop([0, diff , image.width , diff + new_height])
    else:
        multiplier = image.height / 480
        new_width = 800 * multiplier
        diff = image.width - new_width
        diff = int(diff/2)
        crop_image = image.crop([diff, 0, diff + new_width, image.height])

    resizedimage = crop_image.resize(inky.resolution)
    inky.set_image(resizedimage, saturation=saturation)
    inky.show()