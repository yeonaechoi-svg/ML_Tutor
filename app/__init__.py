from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/ml_tutor.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '로그인이 필요합니다.'

    from app.auth import auth_bp
    from app.student import student_bp
    from app.teacher import teacher_bp
    from app.ai_tutor import ai_tutor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(ai_tutor_bp)

    app.jinja_env.globals['enumerate'] = enumerate

    @app.context_processor
    def inject_stage_nav():
        from flask_login import current_user
        if not current_user.is_authenticated or current_user.role != 'student':
            return dict(nav_current_stage=None, nav_completed_stages=set())
        from app.models import Progress
        # 단계 완료 기준: 해당 단계의 마지막 서브스텝 완료 여부
        stage_last_substep = {1: 7, 2: 3}
        completed_stages = set()
        for stage, last_sub in stage_last_substep.items():
            p = Progress.query.filter_by(
                user_id=current_user.id, stage=stage,
                substep=last_sub, status='completed'
            ).first()
            if p:
                completed_stages.add(stage)
        current_stage = next((s for s in range(1, 8) if s not in completed_stages), 7)
        return dict(nav_current_stage=current_stage, nav_completed_stages=completed_stages)

    with app.app_context():
        from app import models
        db.create_all()

    return app
