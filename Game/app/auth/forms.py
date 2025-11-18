from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', 
                         validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password', 
                           validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                    validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[
        ('enthusiast', 'Enthusiast - Practice challenges only'),
        ('buyer', 'Buyer - Solve challenges to access marketplace'),
        ('seller', 'Seller - Sell products in marketplace after solving challenges')
    ], validators=[DataRequired()])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose another one.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use another one.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class AdminRegistrationForm(FlaskForm):
    username = StringField('Username', 
                         validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password', 
                           validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password',
                                    validators=[DataRequired(), EqualTo('password')])
    admin_key = PasswordField('Admin Registration Key', validators=[DataRequired()])
    submit = SubmitField('Register as Admin')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose another one.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use another one.')
