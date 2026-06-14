from flask import render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app.teacher import teacher_bp
from app.models import User, Progress, QuizResult
from app import db
from werkzeug.utils import secure_filename
import openpyxl
import os


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
