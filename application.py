import os
import requests
from flask import Flask, render_template, session, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required


app = Flask(__name__)
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
def index():
    """Landing Page"""
    session.clear()
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register User"""
    # Forget any previous registration attempts
    session.clear()

    if request.method == "POST":

        # Ensure username is entered
        if not request.form.get("username"):
            return render_template("error.html", error="Please enter username. Go back and try again!", back="/register")

        # Ensure password is entered
        elif not request.form.get("password"):
            return render_template("error.html", error="Please enter password. Go back and try again!", back="/register")

        # Ensure password matches
        elif request.form.get("password") != request.form.get("confirm_password"):
            return render_template("error.html", error="Passwords do not match! Go back and try again!", back="/register")

        # Check if username is already in database
        username = request.form.get("username")
        password = request.form.get("password")
        if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount != 0:
            return render_template("error.html", error="Sorry! Username already exists. Go back and try again!", back="/register")
        else:
            db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                       {"username": username, "password": generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)})
            db.commit()
            return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user In"""
    # Forget any previous registration attempts
    session.clear()

    if request.method == "POST":

        # Ensure username is entered
        if not request.form.get("username"):
            return render_template("error.html", error="Please enter username. Go back and try again!", back="/login")

        # Ensure password is entered
        if not request.form.get("password"):
            return render_tempalte("error.html", error="Please enter password. Go back and try again!", back="/login")

        # Query Database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": request.form.get("username")}).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]['password'], request.form.get("password")):
            return render_template("error.html", error="Username or password is incorrect! Go back and try again!", back="/login")

        # Remember which user has logged on
        session["user_id"] = rows[0]['id']
        username = request.form.get("username")

        # Return to homepage
        return render_template("search.html", username=username)

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Return to Homepage
    return redirect("/")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Display Search Results"""

    if request.method == "POST":
        search = request.form.get("search").lower()

        # Add wild card for LIKE operator
        search = "%" + search + "%"

        rows = db.execute("SELECT * FROM books WHERE isbn LIKE :search OR LOWER(author) LIKE :search OR LOWER(title) LIKE :search LIMIT 7",
                          {"search": search}).fetchall()
        db.commit()

        if len(rows) == 0:
            return render_template('error.html', error='Sorry there were no matches! Please Try again!', back="/search")

        return render_template('results.html', rows=rows)

    return render_template("search.html")


@app.route("/books/<isbn>", methods=["GET", "POST"])
@login_required
def books(isbn):
    """Navigate to Books Page"""

    if request.method == "POST":

        # Review, rating and session_user

        review = request.form.get("review")
        rating = int(request.form.get("rating"))
        user_id = session["user_id"]

        # Find ISBN to enter into reviews table in order to cross reference easier

        isbn_1 = db.execute("SELECT isbn FROM books WHERE isbn = :isbn",
                            {"isbn": isbn}).fetchone()

        isbn_1 = isbn_1[0]

        # Check if user has already submitted review

        check_review = db.execute("SELECT FROM reviews WHERE user_id = :user_id AND isbn = :isbn",
                                  {"user_id": user_id, "isbn": isbn}).fetchall()

        if len(check_review) == 1:
            return render_template("error.html", error="Sorry, you have already posted a review for this book!", back="/search")

        else:

            # Insert data into reviews table

            db.execute("INSERT INTO reviews (review, rating, isbn, user_id, time_t) VALUES (:review, :rating, :isbn, :user_id, current_timestamp)",
                       {"review": review, "rating": rating, "isbn": isbn_1, "user_id": user_id, })
            db.commit()

            return redirect("/books/" + isbn)

    else:

        # Select book that matches to ISBN
        rows = db.execute("SELECT * FROM books WHERE isbn = :isbn",
                          {"isbn": isbn}).fetchall()

        # API Call to Goodreads data
        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                           params={"key": "K22ISrFw4vvqjej8YPSr9Q", "isbns": isbn})

        # Access average_rating and count of ratings from JSON object
        data = res.json()
        data = data['books'][0]
        rating = data['average_rating']
        count = data['work_ratings_count']

        # Access reviews database
        reviews = db.execute("SELECT * FROM reviews JOIN users ON reviews.user_id = users.id WHERE isbn = :isbn ORDER BY time_t DESC LIMIT 5",
                             {"isbn": isbn}).fetchall()

        if len(reviews) == 0:
            review = False
        else:
            review = True

        return render_template("books.html", rows=rows, rating=rating, count=count, reviews=reviews, review=review)


@app.route("/api/<isbn>")
def api(isbn):
    """Return JSONIFY object from web application API"""

    # API Call to Goodreads data
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "K22ISrFw4vvqjej8YPSr9Q", "isbns": isbn})

    # Access average_rating and count of ratings from JSON object
    data = res.json()
    data = data['books'][0]
    rating = data['average_rating']
    count = data['work_ratings_count']

    # Access book details
    rows = db.execute("SELECT * FROM books WHERE isbn = :isbn",
                      {"isbn": isbn}).fetchall()

    for row in rows:

        title = row['title']
        author = row['author']
        year = row['year']
        isbn = row['isbn']

    # return jsonify object

    return jsonify({
        "title": title,
        "author": author,
        "year": year,
        "isbn": isbn,
        "review_count": count,
        "average_score": rating,
    })
