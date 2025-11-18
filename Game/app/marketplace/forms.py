from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField, FloatField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=1000)])
    price = FloatField('Price ($)', validators=[DataRequired(), NumberRange(min=0.01)])
    image = FileField('Product Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'])])
    submit = SubmitField('Create Product')

class PurchaseForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Purchase')

class AddToCartForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Add to Cart')

# Optional: Form for updating quantity in cart view
class UpdateCartItemForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Update')

# Optional: Form for removing item from cart view
class RemoveCartItemForm(FlaskForm):
    submit = SubmitField('Remove')

# Optional: Form for initiating checkout (might not need fields, just a button)
class CheckoutForm(FlaskForm):
    submit = SubmitField('Proceed to M-Pesa Payment')

class VerifyMpesaForm(FlaskForm):
    mpesa_code = StringField('M-Pesa Confirmation Code', validators=[DataRequired(), Length(min=9, max=15)]) # Typical length is around 10-15 chars
    submit = SubmitField('Verify Payment')