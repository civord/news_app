import os

import random
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, flash, url_for
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

def validate_input(title, description, article_type, content, image):
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
    elif not allowed_file(image.filename):
        flash("Invalid image format! Allowed formats: png, jpg, jpeg, gif.")
        return redirect("/add_news")
    elif request.content_length > app.config['MAX_CONTENT_LENGTH']:
        flash("File size exceeds limit!")
        return redirect("/add_news")

@app.route("/")
def index():
    try:
        articles = db.execute("SELECT * FROM articles")
        featured_articles = db.execute("SELECT * FROM articles")
        main_news = db.execute("SELECT * FROM articles ORDER BY date DESC LIMIT 9")
        main_news_ids = [article["id"] for article in main_news]
        existing_article_types = db.execute("SELECT type FROM articles GROUP BY type HAVING COUNT(type) >= 2")
        types_list = [row["type"] for row in existing_article_types]
        weekend_reads_left = db.execute("SELECT * FROM articles WHERE type=? ORDER BY date DESC LIMIT 1", random.choice(types_list))
        weekend_reads_right = db.execute("SELECT * FROM articles WHERE type=? ORDER BY date DESC LIMIT 1", random.choice(types_list))
        if main_news_ids:
            placeholders = ",".join(["?"] * len(main_news_ids))  # Create a string like "?, ?, ?" for SQL
            articles = db.execute(
                f"SELECT * FROM articles WHERE id NOT IN ({placeholders}) ORDER BY date DESC",
                *main_news_ids
            )
        else:
            articles = db.execute("SELECT * FROM articles ORDER BY date")

        articles_by_type = {}
        for article in featured_articles:
            if article['type'] not in articles_by_type:
                articles_by_type[article['type']] = []
            articles_by_type[article['type']].append(article)

        print(articles_by_type)
        left_news = main_news[:3]
        center_news = main_news[3:6]
        right_news = main_news[6:9]
    except:
        return redirect("/")
        
    return render_template("index.html", articles = articles, article_types = ARTICLE_TYPES, 
        left_news=left_news,
        center_news=center_news,
        right_news=right_news,
        weekend_reads_left = weekend_reads_left,
        weekend_reads_right = weekend_reads_right,
        articles_by_type = articles_by_type,
        main=True)


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
        
        validate_input(title, description, article_type, content, image)

        if not image:
            flash("You must upload an image!")
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

@app.route("/edit_news/<int:article_id>", methods = ["GET", "POST"])
@login_required
def edit_news(article_id):
    article = db.execute("SELECT * FROM articles WHERE id=?", (article_id,))[0]
    if not article:
        return flash("Article Not Found"), 404
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        article_type = request.form.get("news_type")
        content = request.form.get("news_content")
        image = request.files["news_image"]

        validate_input(title, description, article_type, content, image)
        
        if not image:
            image_path = article["image_path"]
        else:
            filename = secure_filename(image.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image.save(image_path)

        try:
            db.execute("UPDATE articles SET title = ?, description = ?, type = ?, content = ?, image_path = ? WHERE id= ?", title, description, article_type, content, image_path, article_id)
            return redirect(url_for('view_news', article_id=article_id))
        except:
            flash("Unable to update the article!")
            return redirect(url_for("admin", article_id = article_id))
    return render_template("edit_articles.html", article = article, article_types = ARTICLE_TYPES)
        

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

@app.route("/news/<category>")
def more_news(category):
    articles = db.execute("SELECT * FROM articles WHERE type=?", category)
    return render_template("more_news.html", articles=articles, category=category, article_types = ARTICLE_TYPES)
