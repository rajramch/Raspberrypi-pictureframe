from flask import Flask, render_template, request, url_for, flash, redirect
from PIL import Image
from inky import Inky_Impressions_7

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

messages = [{'title': 'Message One',
             'content': 'Message One Content'},
            {'title': 'Message Two',
             'content': 'Message Two Content'}
            ]

@app.route('/')
def index():
    return render_template('index.html', messages=messages)

@app.route('/create/', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        img = request.form['img']
        change_image(img)
    return render_template('create.html')

def change_image(img):
    inky = Inky_Impressions_7()
    saturation = 0.5
    image = Image.open(img)
    resizedimage = image.resize(inky.resolution)
    inky.set_image(resizedimage, saturation=saturation)
    inky.show()