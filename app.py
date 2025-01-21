import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, flash
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

from helper import login_required

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB

ARTICLE_TYPES = ["Politics", "Business", "Health", "Entertainment", "Style", "Travel", "Sports"]
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

types = {
    "Politics" : "red",
    "Business" : "yellow",
    "Health" : "green",
    "Entertainment": "blue",
    "Style": "pink",
    "Travel": "orange",
    "Sports": "rgba(68, 217, 150, 0.643)"
}

app.config["SESSION PERMANENT"] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

db = SQL("sqlite:///news.db")

@app.route("/")
def index():
    try:
        articles = db.execute("SELECT * FROM articles")
    except:
        flash("FAILED TO FETCH ARTICLES FROM THE DATABASE")
        return redirect("/")
    return render_template("index.html", articles = articles, article_types = ARTICLE_TYPES)


@app.route("/login", methods = ["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            flash("Username is required!", "error")
            return redirect("/login")
        elif not password:
            flash("Password is required!", "error")
            return redirect("/login")

        try:
            users = db.execute("SELECT * FROM users WHERE username = ?", (username, ))
            if len(users) != 1 or not check_password_hash(users[0]["hash"], password):
                flash("Incorrect username or/and password")
                return redirect("/login")
            
            session["user_id"] = users[0]["id"]

            return redirect("/admin")
        except:
            return redirect("/login")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()  
    return redirect("/")      

@app.route("/register", methods = ["POST", "GET"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username:
            flash("Username is required!")
            return redirect("/register")
        elif not password:
            flash("Password is required!")
            return redirect("/register")
        elif password != confirmation:
            flash("Passwords do not match!")
            return redirect("/register")

        hashed_password = generate_password_hash(password)
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hashed_password)
            return redirect("/login")
        except Exception as e:
            print(e)
            flash("Failed registering an user!")
            return redirect("/register")
    else:
        return render_template("register.html")

@app.route("/admin", methods = ["POST", "GET"])
@login_required
def admin():
    try:
        articles = db.execute("SELECT * FROM articles LIMIT 10")
    except:
        return redirect("/")
    return render_template("admin.html", articles=articles, types=types)
        
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/add_news", methods = ["POST", "GET"])
@login_required
def add_news():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        article_type = request.form.get("news_type")
        content = request.form.get("news_content")
        image = request.files["news_image"]
        if not title:
            flash("You must enter a title!")
            return redirect("/add_news")
        elif not description:
            flash("You must enter a description!")
            return redirect("/add_news")
        elif not article_type:
            flash("You must enter an article type / INVALID ARTICLE TYPE!")
            return redirect("/add_news")
        elif not content:
            flash("You must enter the article's content!")
            return redirect("/add_news")
        elif not image:
            flash("You must upload an image!")
            return redirect("/add_news")
        elif not allowed_file(image.filename):
            flash("Invalid image format! Allowed formats: png, jpg, jpeg, gif.")
            return redirect("/add_news")
        elif request.content_length > app.config['MAX_CONTENT_LENGTH']:
            flash("File size exceeds limit!")
            return redirect("/add_news")

        filename = secure_filename(image.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        image.save(image_path)

        try:
            db.execute("INSERT INTO articles (title, description, type, content, image_path, date) VALUES (?, ?, ?, ?, ?, ?)", title, description, article_type, content, image_path, datetime.now())
            return redirect("/admin")
        except Exception as e:
            import logging
            logging.basicConfig(filename='error.log', level=logging.ERROR)
            logging.error(f"Database error: {e}")
            flash("Failed adding an article into the database!")
            return redirect("/add_news")
    else:
        return render_template("add_news.html", article_types=ARTICLE_TYPES)

@app.route("/delete_news", methods = ["POST"])
@login_required
def delete_news():
    article_id = request.form.get("article_id")
    if article_id:
        try:
            db.execute("DELETE FROM articles WHERE id=?", article_id)
        except:
            flash("FAILED TO DELETE THIS ARTICLE")
    return redirect("/admin")

@app.route("/news/<int:article_id>")
def view_news(article_id):
    article = db.execute("SELECT * FROM articles WHERE id=?", article_id)
    if not article:
        return flash("Article not found"), 404
    return render_template("article_detail.html", article=article[0])