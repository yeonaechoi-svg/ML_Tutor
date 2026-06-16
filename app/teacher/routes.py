from flask import render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app.teacher import teacher_bp
from app.models import User, Progress, QuizResult, PeerReview, ProjectIdea
from app import db
from werkzeug.utils import secure_filename
import openpyxl
import os
import json


def teacher_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('교사 권한이 필요합니다.', 'error')
            return redirect(url_for('auth.teacher_login'))
        return f(*args, **kwargs)
    return decorated


@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    students = User.query.filter_by(role='student').order_by(
        User.class_name, User.student_id
    ).all()

    stage_counts = {}
    for stage in range(1, 8):
        stage_counts[stage] = 0

    student_info = []
    for s in students:
        completed = Progress.query.filter_by(
            user_id=s.id, status='completed'
        ).order_by(Progress.stage.desc(), Progress.substep.desc()).first()
        current_stage = completed.stage if completed else 0
        last_access = completed.updated_at if completed else s.created_at
        if current_stage > 0:
            stage_counts[current_stage] = stage_counts.get(current_stage, 0) + 1
        student_info.append({
            'user': s,
            'current_stage': current_stage,
            'last_access': last_access
        })

    return render_template(
        'teacher/dashboard.html',
        students=student_info,
        stage_counts=stage_counts,
        total_students=len(students)
    )


@teacher_bp.route('/students')
@login_required
@teacher_required
def students():
    class_filter = request.args.get('class_name', '')
    query = User.query.filter_by(role='student')
    if class_filter:
        query = query.filter_by(class_name=class_filter)
    students = query.order_by(User.class_name, User.student_id).all()

    all_classes = db.session.query(User.class_name).filter_by(
        role='student'
    ).distinct().order_by(User.class_name).all()
    class_list = [c[0] for c in all_classes]

    student_info = []
    for s in students:
        completed = Progress.query.filter_by(
            user_id=s.id, status='completed'
        ).order_by(Progress.stage.desc(), Progress.substep.desc()).first()
        quiz = QuizResult.query.filter_by(
            user_id=s.id, stage=1
        ).order_by(QuizResult.created_at.desc()).first()
        student_info.append({
            'user': s,
            'current_stage': completed.stage if completed else 0,
            'quiz_score': f"{quiz.score}/{quiz.total}" if quiz else '-'
        })

    return render_template(
        'teacher/students.html',
        students=student_info,
        class_list=class_list,
        class_filter=class_filter
    )


@teacher_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@teacher_required
def upload():
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('파일을 선택해주세요.', 'error')
            return render_template('teacher/upload.html')

        file = request.files['excel_file']
        if file.filename == '':
            flash('파일을 선택해주세요.', 'error')
            return render_template('teacher/upload.html')

        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.', 'error')
            return render_template('teacher/upload.html')

        filename = secure_filename(file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        added = 0
        skipped = 0
        errors = []

        try:
            wb = openpyxl.load_workbook(filepath)
            ws = wb.active

            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if not row or not any(row):
                    continue
                try:
                    class_name = str(row[0]).strip() if row[0] else ''
                    student_id = str(row[1]).strip() if row[1] else ''
                    name = str(row[2]).strip() if row[2] else ''

                    if not class_name or not student_id or not name:
                        errors.append(f"행 {row_num}: 빈 항목이 있습니다.")
                        continue

                    existing = User.query.filter_by(student_id=student_id).first()
                    if existing:
                        skipped += 1
                        continue

                    user = User(
                        name=name,
                        student_id=student_id,
                        class_name=class_name,
                        role='student',
                        is_first_login=True
                    )
                    user.set_password('1234')
                    db.session.add(user)
                    added += 1
                except Exception as e:
                    errors.append(f"행 {row_num}: 처리 오류 ({str(e)})")

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'파일 처리 오류: {str(e)}', 'error')
            return render_template('teacher/upload.html')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

        msg = f'{added}명 등록 완료'
        if skipped:
            msg += f', {skipped}명 중복 건너뜀'
        if errors:
            msg += f', {len(errors)}건 오류'
        flash(msg, 'success' if added > 0 else 'error')

        if errors:
            for err in errors[:5]:
                flash(err, 'error')

        return redirect(url_for('teacher.students'))

    return render_template('teacher/upload.html')


@teacher_bp.route('/student/<int:student_id>')
@login_required
@teacher_required
def student_detail(student_id):
    student = User.query.get_or_404(student_id)
    if student.role != 'student':
        return redirect(url_for('teacher.students'))

    # 진도 정보
    completed = Progress.query.filter_by(
        user_id=student.id, status='completed'
    ).order_by(Progress.stage.desc(), Progress.substep.desc()).first()
    current_stage = completed.stage if completed else 0

    quiz = QuizResult.query.filter_by(
        user_id=student.id, stage=1
    ).order_by(QuizResult.created_at.desc()).first()

    # 프로젝트 아이디어
    idea = ProjectIdea.query.filter_by(user_id=student.id).first()

    # 자기평가 파싱
    self_checked = []
    if idea and idea.self_checklist:
        try:
            self_checked = json.loads(idea.self_checklist)
        except Exception:
            pass

    # 받은 동료 평가
    reviews_received = PeerReview.query.filter_by(reviewee_id=student.id).all()

    parsed_reviews = []
    for r in reviews_received:
        reviewer = User.query.get(r.reviewer_id)
        try:
            data = json.loads(r.checklist_json)
            items = data.get('items', [])
            comment = data.get('comment', '')
            score = sum(1 for v in items if v)
        except Exception:
            items, comment, score = [], '', 0
        parsed_reviews.append({
            'reviewer': reviewer,
            'checks': items,
            'comment': comment,
            'score': score,
        })

    # 평균 점수 및 항목별 동의율
    n = len(parsed_reviews)
    avg_score = round(sum(r['score'] for r in parsed_reviews) / n, 2) if n else None
    item_agree = []
    if n:
        for i in range(5):
            agree_count = sum(1 for r in parsed_reviews if i < len(r['checks']) and r['checks'][i])
            item_agree.append(round(agree_count / n * 100))

    # 내가 한 동료 평가 수
    given_count = PeerReview.query.filter_by(reviewer_id=student.id).count()

    SELF_ITEMS = [
        "프로젝트 주제와 기계학습 유형을 적절히 연결했다",
        "데이터 수집과 전처리 과정을 이해하며 진행했다",
        "알고리즘 선택 이유를 논리적으로 설명할 수 있다",
        "모델 훈련과 성능 평가 코드를 직접 작성했다",
        "성능 결과의 의미를 스스로 해석할 수 있다",
        "전체 프로젝트 과정을 처음부터 다시 설명할 수 있다",
    ]
    PEER_ITEMS = [
        "프로젝트 주제가 명확하고 기계학습으로 해결 가능하다",
        "데이터와 알고리즘 선택이 주제에 적합하다",
        "모델 성능이 프로젝트 목적에 비추어 합리적이다",
        "결과 해석이 논리적이고 이해하기 쉽다",
        "전반적으로 프로젝트가 성실하게 수행되었다",
    ]

    return render_template(
        'teacher/student_detail.html',
        student=student,
        current_stage=current_stage,
        quiz=quiz,
        idea=idea,
        self_items=SELF_ITEMS,
        self_checked=self_checked,
        peer_items=PEER_ITEMS,
        reviews_received=parsed_reviews,
        avg_score=avg_score,
        item_agree=item_agree,
        given_count=given_count,
        total_classmates=User.query.filter_by(
            class_name=student.class_name, role='student'
        ).filter(User.id != student.id).count(),
    )


@teacher_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@login_required
@teacher_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'teacher':
        flash('교사 계정은 초기화할 수 없습니다.', 'error')
        return redirect(url_for('teacher.students'))
    try:
        user.set_password('1234')
        user.is_first_login = True
        db.session.commit()
        flash(f'{user.name} 학생의 비밀번호가 1234로 초기화되었습니다.', 'success')
    except Exception:
        db.session.rollback()
        flash('오류가 발생했습니다.', 'error')
    return redirect(url_for('teacher.students'))
