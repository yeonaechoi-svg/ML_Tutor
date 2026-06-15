from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    class_name = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='student')
    is_first_login = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    progresses = db.relationship('Progress', backref='user', lazy=True)
    chat_logs = db.relationship('ChatLog', backref='user', lazy=True)
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_current_stage(self):
        completed = Progress.query.filter_by(
            user_id=self.id, status='completed'
        ).order_by(Progress.stage.desc(), Progress.substep.desc()).first()
        if completed:
            return completed.stage
        return 1

    def get_current_substep(self):
        in_progress = Progress.query.filter_by(
            user_id=self.id, status='in_progress'
        ).order_by(Progress.updated_at.desc()).first()
        if in_progress:
            return in_progress.substep
        last = Progress.query.filter_by(
            user_id=self.id, status='completed', stage=1
        ).order_by(Progress.substep.desc()).first()
        if last:
            return last.substep + 1
        return 1


class Progress(db.Model):
    __tablename__ = 'progresses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stage = db.Column(db.Integer, nullable=False)
    substep = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='in_progress')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatLog(db.Model):
    __tablename__ = 'chat_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stage = db.Column(db.Integer, nullable=False)
    substep = db.Column(db.Integer, nullable=False)
    session_id = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class QuizResult(db.Model):
    __tablename__ = 'quiz_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stage = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PeerReview(db.Model):
    __tablename__ = 'peer_reviews'

    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    checklist_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviews_given')
    reviewee = db.relationship('User', foreign_keys=[reviewee_id], backref='reviews_received')


class ProjectIdea(db.Model):
    __tablename__ = 'project_ideas'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    topic = db.Column(db.String(200))
    interest_field = db.Column(db.Text)      # 관심 분야
    problem_situation = db.Column(db.Text)   # 문제 상황
    ml_problem = db.Column(db.Text)          # 기계학습으로 해결할 문제
    current_state = db.Column(db.Text)       # 현재 상태
    target_state = db.Column(db.Text)        # 목표 상태
    key_elements = db.Column(db.Text)        # 핵심 요소
    sub_problems = db.Column(db.Text)        # 작은 문제로 분해
    problem_statement = db.Column(db.Text)
    input_data = db.Column(db.String(500))
    output_target = db.Column(db.String(200))
    ml_type = db.Column(db.String(50))
    ml_reason = db.Column(db.Text)
    # 3단계: 데이터 탐색과 전처리
    data_source = db.Column(db.Text)        # 데이터 출처 URL
    file_name = db.Column(db.String(200))   # 파일명
    data_rows = db.Column(db.String(50))    # 행 수
    data_cols = db.Column(db.String(50))    # 열 수
    column_list = db.Column(db.Text)        # 컬럼 목록
    missing_handling = db.Column(db.Text)   # 결측치 처리 방법
    outlier_handling = db.Column(db.Text)   # 이상치 처리 방법
    # 4단계: 알고리즘 선정
    algorithm = db.Column(db.String(50))    # linear_regression / decision_tree / random_forest / knn / kmeans
    algorithm_reason = db.Column(db.Text)   # 선정 이유
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('project_idea', uselist=False))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
