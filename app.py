import os

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_socketio import SocketIO, send
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config


app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=True,
    engineio_logger=True
)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please login first."


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )
with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class SignupForm(FlaskForm):

    username = StringField(
        "Username",
        validators=[DataRequired()]
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password")
        ]
    )

    submit = SubmitField("Sign Up")


class LoginForm(FlaskForm):

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )

    submit = SubmitField("Login")


@socketio.on("message")
def handle_message(message):
    print("Received:", message)
    print("Authenticated:", current_user.is_authenticated)

    if current_user.is_authenticated:
        print("Username:", current_user.username)

        if message.strip():
            send(
                f"{current_user.username}: {message}",
                broadcast=True
            )


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("chat"))

    return render_template("home.html")
@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()

    if form.validate_on_submit():

        existing_email = User.query.filter_by(
            email=form.email.data
        ).first()

        if existing_email:
            flash("Email already registered.", "danger")
            return redirect(url_for("signup"))

        existing_username = User.query.filter_by(
            username=form.username.data
        ).first()

        if existing_username:
            flash("Username already exists.", "danger")
            return redirect(url_for("signup"))

        hashed_password = generate_password_hash(
            form.password.data
        )

        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        flash(
            "Account created successfully! Please login.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template(
        "signup.html",
        form=form
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    form = LoginForm()
    print("Method:", request.method)

    print("Validate:", form.validate_on_submit())
    print("Errors:", form.errors)


    if form.validate_on_submit():

        user = User.query.filter_by(
            email=form.email.data
        ).first()

        if user and check_password_hash(
            user.password,
            form.password.data
        ):
            login_user(user)
            return redirect(url_for("chat"))

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template(
        "login.html",
        form=form
    )
@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )