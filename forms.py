from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, FileField, SelectField
from wtforms.validators import DataRequired, URL
from flask_wtf.file import FileField, FileAllowed
from flask_ckeditor import CKEditorField

# WTForms


class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    country = SelectField("Country", choices=[], validators=[DataRequired()])
    image = FileField("Upload Image", validators=[FileAllowed(['jpg', 'jpeg', 'png', 'svg'], 'Images only!')])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")


class CommentForm(FlaskForm):
    comment_text = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")
