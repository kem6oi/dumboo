# app/admin/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField # FileField if uploading data
from wtforms.validators import DataRequired, Length, ValidationError, Optional # Import Optional validator
from app.models import User # Keep User import
from flask import current_app as app # Import current_app to access config


class CreateChallengeForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=1000)])
    difficulty = SelectField('Difficulty', choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], validators=[DataRequired()])

    # Category SelectField (choices set dynamically in route)
    category = SelectField('Category', validators=[DataRequired()])

    # Flag field (required for all challenges)
    flag = TextAreaField('Flag (Solution)', validators=[DataRequired(), Length(min=1)])

    # Challenge Data field (optional, type-dependent - e.g., ciphertext, URL, file content)
    # Consider making this required if category is Cryptography, or for specific other types.
    # Using Optional validator for now as it's nullable in the model.
    challenge_data = TextAreaField('Challenge Data/Instructions', validators=[Optional(), Length(max=5000)])

    # Encryption Type (only used for Cryptography category)
    # Set choices dynamically in the route. Use Optional validator.
    encryption_type = SelectField('Encryption Type', validators=[Optional()])

    # Config JSON (optional, type-dependent - e.g., Crypto Key/IV, ports, usernames)
    config_json = TextAreaField('Configuration (JSON or Text)', validators=[Optional(), Length(max=2000)]) # Limit length

    # Optional: File upload field if you want to handle binary/other file challenges
    # challenge_file = FileField('Challenge File', validators=[Optional(), FileAllowed(['bin', 'pcap', 'jpg', 'zip', etc.])]) # Requires FileField and FileAllowed imports


    submit = SubmitField('Create Challenge')

    # Add custom validation if needed, e.g., encryption_type required if category is Crypto
    def validate(self, *args, **kwargs):
        if not super(CreateChallengeForm, self).validate(*args, **kwargs):
            return False
        # Custom validation for Cryptography specific fields
        if self.category.data == 'Cryptography':
            if not self.encryption_type.data:
                self.encryption_type.errors.append('Encryption Type is required for Cryptography challenges.')
                return False
            # You might also check if challenge_data and config_json are present for crypto depending on your admin workflow
        return True


# ManageUserForm remains unchanged
class ManageUserForm(FlaskForm):
    user_role = SelectField('User Role', choices=[
        ('enthusiast', 'Enthusiast'),
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
        ('inactive', 'Deactivate User')
    ], validators=[DataRequired()])
    submit = SubmitField('Update User')