from flask import Blueprint

marketplace = Blueprint('marketplace', __name__, url_prefix='/marketplace')

from . import routes
