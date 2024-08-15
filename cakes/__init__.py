from flask import Flask 

def fyncakes_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'aroncakes' 

    return app