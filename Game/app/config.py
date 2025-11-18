# app/config.py

import os

class Config:
    # Generate a secure random secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///ctf_marketplace.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Challenge configuration
    CHALLENGES_PER_PAGE = 10
    EASY_CHALLENGES_REQUIRED_FOR_BUYER = 3
    HARD_CHALLENGES_REQUIRED_FOR_SELLER = 5

    # Challenge Categories (keep as defined previously)
    CHALLENGE_CATEGORIES = [
        'Cryptography',
        'Web',
        'Reverse Engineering',
        'Binary Exploitation',
        'Forensics',
        'Miscellaneous',
        'Programming/Scripting',
    ]
    # Add Encryption Types (can be useful elsewhere)
    ENCRYPTION_TYPES = ['aes', 'vigenere', 'rsa']


    # Upload folder for product images
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Example extensions, might need more for challenges

    # Maximum content length for file uploads (5MB)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

   # ======================== M-Pesa Configuration (Placeholders) ========================
# !!! WARNING: Replace with actual secure environment variables in production !!!
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', 'YOUR_MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', 'YOUR_MPESA_CONSUMER_SECRET')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '174379') # Paybill/Till Number - Use test sandbox ones initially
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', 'bfb279f914b717b9719790ddee50b7a7e63b0997dae17a78a9f8810fd6f1a66c') # LNM Online Passkey - Use test sandbox one
MPESA_CALLBACK_URL = os.environ.get('MPESA_CALLBACK_URL', 'YOUR_PUBLIC_URL/marketplace/mpesa_callback') # MUST be publicly accessible URL
MPESA_API_URL = os.environ.get('MPESA_API_URL', 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest') # Sandbox URL
# MPESA_API_AUTH_URL = os.environ.get('MPESA_API_AUTH_URL', 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials') # Sandbox Auth URL
# MPESA_TRANSACTION_TYPE = os.environ.get('MPESA_TRANSACTION_TYPE', 'CustomerBuyGoodsOnline') # Or CustomerPayBillOnline

# Minimum amount for STK Push is typically 1 KES
MPESA_MIN_AMOUNT = 1.00

# Add a simulated expected M-Pesa confirmation code for verification (for demonstration)
# In a real system, you'd verify against M-Pesa's API or await a callback.
SIMULATED_MPESA_CONFIRMATION_CODE = os.environ.get('SIMULATED_MPESA_CONFIRMATION_CODE', "ABC123XYZ") 