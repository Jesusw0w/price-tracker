from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from app.config import template_dir, static_dir

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gpu_data_web.db'

db = SQLAlchemy(app)

posts = [{'author': 'Chonkito', 'title': 'Post1', 'content': 'First post cnt', 'date_posted': 'time1'},
         {'author': 'Senhor', 'title': 'Post2', 'content': 'Boas putos', 'date_posted': 'post2'}]


class User(db.Model):
    # id of each entry
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    # content = db.Column(db.String(200), nullable=False)
    # date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}','{self.image_file}')"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"


@app.route('/')  # , methods=['POST', 'GET'])
def gpu_scrapper_app():
    return "<h1>hello</h1>"  # render_template('index.html')


@app.route("/home")
def home():
    return render_template('home.html', posts=posts)


@app.route("/data_analyzer")
def data_analyzer():
    return render_template('data_analyzer.html')


if __name__ == '__main__':
    app.run(debug=True)

"""def index():
    if request.method == 'POST':
        task_content = request.form['content']
        new_task = User(content=task_content)

        try:
            db.session.add(new_task)
            db.session.commit()
            # return redirect('/')
        except:
            return 'There was an issue with the task'
    else:
        posts = Post.query.order_by(Post.date_posted).all()
        return render_template('index.html', task=posts)"""
