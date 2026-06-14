from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.models import User
from app import db
import os


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        class_name = request.form.get('class_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(
            student_id=student_id,
            class_name=class_name,
            name=name,
            role='student'
        ).first()

        if user and user.check_password(password):
            login_user(user)
            if user.is_first_login:
                return redirect(url_for('auth.change_password'))
            return redirect(url_for('student.dashboard'))

        flash('반, 학번, 이름 또는 비밀번호가 올바르지 않습니다.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        teacher_code = request.form.get('teacher_code', '').strip()

        if teacher_code == os.environ.get('TEACHER_CODE', ''):
            teacher = User.query.filter_by(role='teacher').first()
            if not teacher:
                teacher = User(
                    name='선생님',
                    student_id='teacher001',
                    class_name='교사',
                    role='teacher',
                    is_first_login=False
                )
                teacher.set_password(teacher_code)
                try:
                    db.session.add(teacher)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    flash('오류가 발생했습니다.', 'error')
                    return render_template('auth/teacher_login.html')
            login_user(teacher)
            return redirect(url_for('teacher.dashboard'))

        flash('교사 코드가 올바르지 않습니다.', 'error')

    return render_template('auth/teacher_login.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if len(new_password) < 4:
            flash('비밀번호는 4자 이상이어야 합니다.', 'error')
        elif new_password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.', 'error')
        else:
            try:
                current_user.set_password(new_password)
                current_user.is_first_login = False
                db.session.commit()
                flash('비밀번호가 변경되었습니다.', 'success')
                if current_user.role == 'teacher':
                    return redirect(url_for('teacher.dashboard'))
                return redirect(url_for('student.dashboard'))
            except Exception:
                db.session.rollback()
                flash('오류가 발생했습니다. 다시 시도해주세요.', 'error')

    return render_template('auth/change_password.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
