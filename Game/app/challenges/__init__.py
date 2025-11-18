from flask import Blueprint

challenges = Blueprint('challenges', __name__, url_prefix='/challenges')

from . import routes
