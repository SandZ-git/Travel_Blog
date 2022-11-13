from flask import Flask, render_template, redirect, url_for, flash, request
from flask_ckeditor import CKEditor
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, DateTime, desc, asc, or_, join
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, SearchForm, SortForm
from flask_gravatar import Gravatar
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
import pycountry
import os
from werkzeug.utils import secure_filename

# posts = requests.get("https://api.npoint.io/c31c07e83376e3a912b9").json()

UPLOAD_FOLDER = "static/uploads"
ROWS_PER_PAGE = 4


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False,
                    base_url=None)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Connect to DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel-blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///travel-blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

today_date = date.today()
current_year = date.today().year


# TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.DateTime(timezone=True), server_default=func.now())
    body = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(250), nullable=True)

    # Foreign Keys
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    country_id = db.Column(db.Integer, db.ForeignKey("countries.id"))

    # References
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")
    country = relationship("Country", back_populates="posts")


class Country(db.Model):
    __tablename__ = "countries"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(5))
    name = db.Column(db.String(100))

    # References
    posts = relationship("BlogPost", back_populates="country")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # References
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # Foreign Keys
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))

    # References
    comment_author = relationship("User", back_populates="comments")
    parent_post = relationship("BlogPost", back_populates="comments")


# only required once, when creating DB.
# db.create_all()

# only once, to populate countries
# for country in pycountry.countries:
#     new_country = Country(
#         code=country.alpha_2,
#         name=country.name
#     )
#     db.session.add(new_country)
#     db.session.commit()


@app.route('/')
def home():
    posts = BlogPost.query.order_by(desc(BlogPost.date)).limit(3).all()
    return render_template("index.html", current_year=current_year, all_posts=posts, current_user=current_user)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # user email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )

        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hash_and_salted_password
        )
        db.session.add(new_user)
        db.session.commit()
        # authenticate user with Flask-Login
        login_user(new_user)
        return redirect(url_for("home"))

    return render_template("register.html", form=form, current_user=current_user, current_year=current_year)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))

    return render_template("login.html", form=form, current_user=current_user, current_year=current_year)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/user')
@login_required
def user():
    return render_template("user.html", date=current_year, current_user=current_user)


@app.route('/about')
def about():
    return render_template("about.html", date=current_year)


@app.route('/contact', methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        data = request.form
        print(data["name"])
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False, current_year=current_year)


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    post_comments = Comment.query.filter_by(post_id=post_id).order_by(desc(Comment.date))
    form = CommentForm()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post,
            date=today_date
        )

        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, current_year=current_year, form=form,
                           current_user=current_user, comments=post_comments)


@app.route("/new-post", methods=["GET", "POST"])
def add_new_post():
    form = CreatePostForm()
    form.country.choices = [(country.code, country.name) for country in Country.query.all()]
    country = Country.query.filter_by(code=form.country.data).first()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to post blog.")
            return redirect(url_for("login"))

        filename = ''
        file = form.image.data
        if file is not None:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            country=country,
            image=filename,
            author=current_user,
            date=today_date
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("new-edit-post.html", form=form, current_user=current_user, current_year=current_year)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    post_country = Country.query.filter_by(id=post.country.id).first()

    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        country=post_country.code,
        # author=post.author,
        body=post.body
    )
    edit_form.country.choices = [(country.code, country.name) for country in Country.query.all()]

    if edit_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to edit blog.")
            return redirect(url_for("login"))

        filename = ''
        file = edit_form.image.data
        if file is not None:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.image = filename

        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("new-edit-post.html", form=edit_form, current_user=current_user)


@app.route('/explore', methods=["GET", "POST"])
def explore():
    # Set the pagination configuration
    page = request.args.get('page', 1, type=int)

    posts = BlogPost.query.order_by(desc(BlogPost.date)).paginate(page=page, per_page=ROWS_PER_PAGE)
    form = SearchForm()
    order = SortForm()
    if form.validate_on_submit():
        searched = form.searched.data
        posts = BlogPost.query.join(Country, BlogPost.country_id == Country.id).filter(
            or_(BlogPost.title.ilike('%' + searched + '%'), BlogPost.subtitle.ilike('%' + searched + '%'),
                BlogPost.body.ilike('%' + searched + '%'), Country.name.ilike('%' + searched + '%'))).paginate(page=page, per_page=ROWS_PER_PAGE)
    if order.validate_on_submit():
        order_dir = order.sort_type.data
        if order_dir == 'asc':
            posts = BlogPost.query.order_by(asc(BlogPost.date)).paginate(page=page, per_page=ROWS_PER_PAGE)
        else:
            posts = BlogPost.query.order_by(desc(BlogPost.date)).paginate(page=page, per_page=ROWS_PER_PAGE)
    return render_template("explore.html", form=form, all_posts=posts, current_user=current_user, order=order)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
