from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError
from werkzeug.security import check_password_hash
from models import User


class Unique(object):
    """A General Class that checks if an object is unique in its model"""
    def __init__(self, model, field, message=u'This element already exists.'):
        self.model = model
        self.field = field

    def __call__(self, form, field):
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            raise ValidationError(self.message)


def invalid_credentials(form, field):
    """ Username and password checker """

    password = field.data
    username = form.username.data

    # Check username is invalid
    user_data = User.query.filter_by(username=username).first()
    if user_data is None or not check_password_hash(
                user_data.password, password):
        raise ValidationError("Username or password is incorrect")


class LoginForm(FlaskForm):
    """Login Form"""
    username = StringField('username', validators=[
        InputRequired(message="Must provide Username")
        ])
    password = PasswordField('password', validators=[
        InputRequired(message="Must provide password"),
        invalid_credentials])


class RegistrationForm(FlaskForm):
    """Registration Form"""
    username = StringField('username', validators=[
        InputRequired(message="Username required"),
        Length(min=4, max=25,
               message="Username must be between 4 and 25 characters"),
        Unique(
            User,
            User.username,
            message='There is already an account with that username.'
            )
        ])

    password = PasswordField('password', validators=[
        InputRequired(message="Password required"),
        Length(min=4, max=25,
               message="Password must be between 4 and 25 characters")
        ])

    confirm_password = PasswordField('confirm_password', validators=[
        InputRequired(message="Password required"),
        EqualTo('password', message="Passwords must match")
        ])
