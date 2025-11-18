# app/challenges/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField # Only imports needed for SolveForm
from wtforms.validators import DataRequired

class SolveForm(FlaskForm):
    solution = StringField('Your Solution (Flag Format)', validators=[DataRequired()])
    submit = SubmitField('Submit Solution')
