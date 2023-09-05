from flask import Flask, render_template, request, url_for, flash, redirect
from PIL import Image
from inky.auto import auto

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
        title = request.form['title']
        content = request.form['content']
        inky = auto(ask_user=True, verbose=True)
        saturation = 0.5
        

    return render_template('create.html')