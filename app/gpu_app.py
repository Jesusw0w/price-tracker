from flask import Flask, render_template, url_for
from flask_sqlalchemy import SQLAlchemy
from config import template_dir,static_dir

app = Flask(__name__, template_folder=template_dir,static_folder=static_dir)


@app.route('/')
def gpu_scrapper_app():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
