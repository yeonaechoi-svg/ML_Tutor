from flask import Blueprint

ai_tutor_bp = Blueprint('ai_tutor', __name__, url_prefix='/ai-tutor')

from app.ai_tutor import routes
