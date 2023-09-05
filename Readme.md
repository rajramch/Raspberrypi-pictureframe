This project is to create a e-ink colored pictureframe using a raspberry pi.

This uses flask server based on python.

This will also have a future expansion by using the gpio buttons on the screen to use it to control room lights using the python-kasa library.

Steps to run

sudo su
export FLASK_ENV=development
export FLASK_APP=app
flask run -h 0.0.0.0 -p 80