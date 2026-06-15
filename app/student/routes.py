from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.student import student_bp
from app.models import Progress, QuizResult, ProjectIdea, User
from app import db
from datetime import datetime


def save_progress(stage, substep, status='completed'):
    try:
        progress = Progress.query.filter_by(
            user_id=current_user.id, stage=stage, substep=substep
        ).first()
        if not progress:
            progress = Progress(
                user_id=current_user.id,
                stage=stage,
                substep=substep,
                status=status
            )
            db.session.add(progress)
        else:
            progress.status = status
            progress.updated_at = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()


def get_completed_substeps(stage):
    rows = Progress.query.filter_by(
        user_id=current_user.id, stage=stage, status='completed'
    ).all()
    return {r.substep for r in rows}


@student_bp.route('/dashboard')
@login_required
def dashboard():
    completed_s1 = get_completed_substeps(1)
    completed_s2 = get_completed_substeps(2)
    completed_s3 = get_completed_substeps(3)
    completed_s4 = get_completed_substeps(4)
    completed_s5 = get_completed_substeps(5)
    completed_s6 = get_completed_substeps(6)
    quiz_result = QuizResult.query.filter_by(
        user_id=current_user.id, stage=1
    ).order_by(QuizResult.created_at.desc()).first()
    idea = ProjectIdea.query.filter_by(user_id=current_user.id).first()

    s1_done = len(completed_s1) >= 7
    s2_done = len(completed_s2) >= 3
    s3_done = len(completed_s3) >= 3
    s4_done = len(completed_s4) >= 2
    s5_done = len(completed_s5) >= 3
    s6_done = len(completed_s6) >= 3
    if s6_done:
        current_stage = 7
    elif s5_done:
        current_stage = 6
    elif s4_done:
        current_stage = 5
    elif s3_done:
        current_stage = 4
    elif s2_done:
        current_stage = 3
    elif s1_done:
        current_stage = 2
    else:
        current_stage = 1

    return render_template(
        'student/dashboard.html',
        completed=completed_s1,
        completed_s1=completed_s1,
        completed_s2=completed_s2,
        completed_s3=completed_s3,
        completed_s4=completed_s4,
        completed_s5=completed_s5,
        completed_s6=completed_s6,
        current_stage=current_stage,
        quiz_result=quiz_result,
        idea=idea
    )


@student_bp.route('/stage1')
@login_required
def stage1():
    completed = get_completed_substeps(1)
    if not completed:
        return redirect(url_for('student.stage1_step', step=1))
    next_step = max(completed) + 1
    if next_step >= 7:
        return redirect(url_for('student.stage1_quiz'))
    return redirect(url_for('student.stage1_step', step=next_step))


@student_bp.route('/stage1/step/<int:step>', methods=['GET', 'POST'])
@login_required
def stage1_step(step):
    if step not in range(1, 7):
        return redirect(url_for('student.stage1_step', step=1))

    completed = get_completed_substeps(1)

    if request.method == 'POST':
        save_progress(1, step)
        next_step = step + 1
        if next_step >= 7:
            return redirect(url_for('student.stage1_quiz'))
        return redirect(url_for('student.stage1_step', step=next_step))

    template_map = {
        1: 'student/stage1/step1.html',
        2: 'student/stage1/step2.html',
        3: 'student/stage1/step3.html',
        4: 'student/stage1/step4.html',
        5: 'student/stage1/step5.html',
        6: 'student/stage1/step6.html',
    }

    return render_template(
        template_map[step],
        step=step,
        completed=completed,
        already_completed=(step in completed)
    )


QUIZ_QUESTIONS = [
    {
        'question': '기온과 습도 데이터를 이용해 아이스크림 일별 판매량을 예측하는 모델을 만들려고 합니다. 어떤 기계학습 유형이 가장 적합한가요?',
        'choices': [
            '분류(Classification) — 스팸/정상처럼 카테고리를 구별하는 문제이다',
            '회귀(Regression) — 연속적인 수치 값을 예측하는 문제이다',
            '군집(Clustering) — 데이터를 유사한 그룹으로 묶는 문제이다',
            '강화학습 — 보상을 통해 행동을 학습하는 문제이다'
        ],
        'answer': 1,
        'explanation': '판매량은 연속적인 수치입니다. 결과가 "얼마인가?"(수치 예측)이면 회귀를 사용합니다. 아이스크림 매출 예측은 교과서 대표 회귀 사례입니다.'
    },
    {
        'question': '이메일 내용을 분석하여 "스팸" 또는 "정상"으로 구별하는 모델에 적합한 기계학습 유형은?',
        'choices': [
            '회귀(Regression) — 판매량이나 가격처럼 수치를 예측한다',
            '분류(Classification) — 미리 정해진 카테고리로 구별한다',
            '군집(Clustering) — 정해진 답 없이 유사한 것끼리 묶는다',
            '비지도학습 — 레이블 없이 패턴을 찾는다'
        ],
        'answer': 1,
        'explanation': '분류는 입력 데이터를 미리 정의된 카테고리(스팸/정상, 합격/불합격 등)로 구별할 때 사용합니다. 정답 레이블이 있는 지도학습의 대표적인 유형입니다.'
    },
    {
        'question': '편의점 체인이 고객들의 구매 패턴 데이터(구매 시간대, 구매 품목, 지출 금액)를 분석하여 유사한 고객들을 그룹으로 나누고자 합니다. 어떤 기계학습 유형이 적합한가요?',
        'choices': [
            '회귀(Regression) — 고객의 다음 구매 금액을 예측한다',
            '분류(Classification) — 고객을 VIP/일반으로 구별한다',
            '군집(Clustering) — 정해진 답 없이 유사한 고객끼리 자동으로 묶는다',
            '지도학습 — 정답이 있는 데이터로 학습한다'
        ],
        'answer': 2,
        'explanation': '군집(K-평균)은 정해진 정답 없이 데이터의 유사성을 기준으로 그룹을 형성합니다. 고객 세분화처럼 "어떤 그룹이 있을까?"를 탐색할 때 비지도학습인 군집을 사용합니다.'
    },
    {
        'question': '자동차의 엔진 크기, 무게, 실린더 수 데이터로 CO₂ 배출량을 예측하는 모델을 만들려고 합니다. 사용할 알고리즘으로 가장 적합한 것은?',
        'choices': [
            '선형 회귀(Linear Regression) — 연속 수치 예측에 적합하다',
            '의사결정나무(Decision Tree) — 카테고리 분류에 적합하다',
            'K-평균(K-Means) — 그룹을 찾는 데 적합하다',
            'KNN — 가장 가까운 이웃의 카테고리를 참고한다'
        ],
        'answer': 0,
        'explanation': 'CO₂ 배출량은 연속 수치이므로 회귀를 사용합니다. 특히 선형 회귀는 입력 변수(엔진 크기 등)와 출력(CO₂)의 선형 관계를 학습합니다. 이는 교과서 실습 A의 핵심 예제입니다.'
    },
    {
        'question': '평균기온, 강수량, 일조시간 데이터를 입력받아 "봄/여름/가을/겨울" 중 어느 계절인지 판별하는 모델에 적합한 기계학습 유형은?',
        'choices': [
            '회귀(Regression) — 기온을 수치로 예측하는 문제이다',
            '군집(Clustering) — 계절별로 데이터를 4개 그룹으로 묶는 문제이다',
            '분류(Classification) — 미리 정의된 4개 계절 중 하나로 판별하는 문제이다',
            '비지도학습 — 정답 없이 패턴을 찾는 문제이다'
        ],
        'answer': 2,
        'explanation': '계절 판별은 4개의 미리 정의된 카테고리(봄/여름/가을/겨울) 중 하나를 선택하는 문제이므로 분류를 사용합니다. "어느 그룹에 속하는가?" → 분류, "얼마인가?" → 회귀, "어떤 그룹이 있는가?" → 군집으로 구분하세요.'
    }
]


@student_bp.route('/stage1/quiz', methods=['GET', 'POST'])
@login_required
def stage1_quiz():
    completed = get_completed_substeps(1)

    if request.method == 'POST':
        score = 0
        results = []
        for i, q in enumerate(QUIZ_QUESTIONS):
            raw = request.form.get(f'q{i}')
            if raw is None:
                results.append({
                    'question': q['question'],
                    'choices': q['choices'],
                    'user_answer': None,
                    'correct_answer': q['answer'],
                    'is_correct': False,
                    'explanation': q['explanation']
                })
                continue
            user_answer = int(raw)
            is_correct = user_answer == q['answer']
            if is_correct:
                score += 1
            results.append({
                'question': q['question'],
                'choices': q['choices'],
                'user_answer': user_answer,
                'correct_answer': q['answer'],
                'is_correct': is_correct,
                'explanation': q['explanation']
            })

        try:
            quiz_result = QuizResult(
                user_id=current_user.id,
                stage=1,
                score=score,
                total=len(QUIZ_QUESTIONS)
            )
            db.session.add(quiz_result)
            save_progress(1, 7)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return render_template(
            'student/stage1/quiz_result.html',
            results=results,
            score=score,
            total=len(QUIZ_QUESTIONS)
        )

    existing_result = QuizResult.query.filter_by(
        user_id=current_user.id, stage=1
    ).order_by(QuizResult.created_at.desc()).first()

    return render_template(
        'student/stage1/quiz.html',
        questions=QUIZ_QUESTIONS,
        completed=completed,
        existing_result=existing_result
    )


# ── 2단계: 아이디어 구상 및 문제 정의 ──

@student_bp.route('/stage2')
@login_required
def stage2():
    completed = get_completed_substeps(2)
    if not completed:
        return redirect(url_for('student.stage2_step', step=1))
    next_step = min(max(completed) + 1, 3)
    return redirect(url_for('student.stage2_step', step=next_step))


@student_bp.route('/stage2/step/<int:step>', methods=['GET', 'POST'])
@login_required
def stage2_step(step):
    if step not in range(1, 4):
        return redirect(url_for('student.stage2_step', step=1))

    completed = get_completed_substeps(2)
    idea = ProjectIdea.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        try:
            if not idea:
                idea = ProjectIdea(user_id=current_user.id)
                db.session.add(idea)

            if step == 1:
                idea.topic = request.form.get('topic', '').strip()
                idea.interest_field = request.form.get('interest_field', '').strip()
                idea.problem_situation = request.form.get('problem_situation', '').strip()
                idea.ml_problem = request.form.get('ml_problem', '').strip()
                idea.current_state = request.form.get('current_state', '').strip()
                idea.target_state = request.form.get('target_state', '').strip()
                idea.key_elements = request.form.get('key_elements', '').strip()
                idea.sub_problems = request.form.get('sub_problems', '').strip()
            elif step == 2:
                idea.ml_type = request.form.get('ml_type', '')
                idea.ml_reason = request.form.get('ml_reason', '').strip()
            elif step == 3:
                idea.problem_statement = request.form.get('problem_statement', '').strip()
                idea.input_data = request.form.get('input_data', '').strip()
                idea.output_target = request.form.get('output_target', '').strip()

            save_progress(2, step)
            db.session.commit()
        except Exception:
            db.session.rollback()

        if request.form.get('save_action') == 'save_only':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True})
            flash('저장되었습니다.', 'success')
            return redirect(url_for('student.stage2_step', step=step))

        if step < 3:
            return redirect(url_for('student.stage2_step', step=step + 1))
        flash('2단계를 완료했습니다! 수고했어요.', 'success')
        return redirect(url_for('student.dashboard'))

    template_map = {
        1: 'student/stage2/step1.html',
        2: 'student/stage2/step2.html',
        3: 'student/stage2/step3.html',
    }

    return render_template(
        template_map[step],
        step=step,
        completed=completed,
        already_completed=(step in completed),
        idea=idea
    )


# ── 4단계: 기계학습 유형과 알고리즘 선정 ──

@student_bp.route('/stage4')
@login_required
def stage4():
    completed = get_completed_substeps(4)
    if not completed:
        return redirect(url_for('student.stage4_step', step=1))
    next_step = min(max(completed) + 1, 2)
    return redirect(url_for('student.stage4_step', step=next_step))


@student_bp.route('/stage4/step/<int:step>', methods=['GET', 'POST'])
@login_required
def stage4_step(step):
    if step not in range(1, 3):
        return redirect(url_for('student.stage4_step', step=1))

    completed = get_completed_substeps(4)
    idea = ProjectIdea.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        try:
            if not idea:
                idea = ProjectIdea(user_id=current_user.id)
                db.session.add(idea)

            if step == 1:
                idea.algorithm = request.form.get('algorithm', '').strip()
            elif step == 2:
                idea.algorithm_reason = request.form.get('algorithm_reason', '').strip()

            save_progress(4, step)
            db.session.commit()
        except Exception:
            db.session.rollback()

        if request.form.get('save_action') == 'save_only':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True})
            flash('저장되었습니다.', 'success')
            return redirect(url_for('student.stage4_step', step=step))

        if step < 2:
            return redirect(url_for('student.stage4_step', step=step + 1))
        flash('4단계를 완료했습니다! 수고했어요.', 'success')
        return redirect(url_for('student.dashboard'))

    template_map = {
        1: 'student/stage4/step1.html',
        2: 'student/stage4/step2.html',
    }

    return render_template(
        template_map[step],
        step=step,
        completed=completed,
        already_completed=(step in completed),
        idea=idea
    )


# ── 6단계: 성능 평가 및 예측 ──

@student_bp.route('/stage6')
@login_required
def stage6():
    completed = get_completed_substeps(6)
    if not completed:
        return redirect(url_for('student.stage6_step', step=1))
    next_step = min(max(completed) + 1, 3)
    return redirect(url_for('student.stage6_step', step=next_step))


@student_bp.route('/stage6/step/<int:step>', methods=['GET', 'POST'])
@login_required
def stage6_step(step):
    if step not in range(1, 4):
        return redirect(url_for('student.stage6_step', step=1))

    completed = get_completed_substeps(6)
    idea = ProjectIdea.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        try:
            if not idea:
                idea = ProjectIdea(user_id=current_user.id)
                db.session.add(idea)

            if step == 3:
                idea.model_score = request.form.get('model_score', '').strip()
                idea.result_interpretation = request.form.get('result_interpretation', '').strip()

            save_progress(6, step)
            db.session.commit()
        except Exception:
            db.session.rollback()

        if request.form.get('save_action') == 'save_only':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True})
            flash('저장되었습니다.', 'success')
            return redirect(url_for('student.stage6_step', step=step))

        if step < 3:
            return redirect(url_for('student.stage6_step', step=step + 1))
        flash('6단계를 완료했습니다! 수고했어요.', 'success')
        return redirect(url_for('student.dashboard'))

    template_map = {
        1: 'student/stage6/step1.html',
        2: 'student/stage6/step2.html',
        3: 'student/stage6/step3.html',
    }

    return render_template(
        template_map[step],
        step=step,
        completed=completed,
        already_completed=(step in completed),
        idea=idea
    )


# ── 5단계: 기계학습을 통한 모델 생성 ──

@student_bp.route('/stage5')
@login_required
def stage5():
    completed = get_completed_substeps(5)
    if not completed:
        return redirect(url_for('student.stage5_step', step=1))
    next_step = min(max(completed) + 1, 3)
    return redirect(url_for('student.stage5_step', step=next_step))


@student_bp.route('/stage5/step/<int:step>', methods=['GET', 'POST'])
@login_required
def stage5_step(step):
    if step not in range(1, 4):
        return redirect(url_for('student.stage5_step', step=1))

    completed = get_completed_substeps(5)
    idea = ProjectIdea.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        try:
            if not idea:
                idea = ProjectIdea(user_id=current_user.id)
                db.session.add(idea)

            if step == 1:
                idea.df_varname = request.form.get('df_varname', 'df').strip() or 'df'
                idea.target_column = request.form.get('target_column', '').strip()
                idea.feature_columns = request.form.get('feature_columns', '').strip()
            elif step == 2:
                idea.test_size = request.form.get('test_size', '0.2').strip()
            elif step == 3:
                idea.model_params = request.form.get('model_params', '').strip()

            save_progress(5, step)
            db.session.commit()
        except Exception:
            db.session.rollback()

        if request.form.get('save_action') == 'save_only':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True})
            flash('저장되었습니다.', 'success')
            return redirect(url_for('student.stage5_step', step=step))

        if step < 3:
            return redirect(url_for('student.stage5_step', step=step + 1))
        flash('5단계를 완료했습니다! 수고했어요.', 'success')
        return redirect(url_for('student.dashboard'))

    template_map = {
        1: 'student/stage5/step1.html',
        2: 'student/stage5/step2.html',
        3: 'student/stage5/step3.html',
    }

    return render_template(
        template_map[step],
        step=step,
        completed=completed,
        already_completed=(step in completed),
        idea=idea
    )


# ── 3단계: 데이터 탐색과 전처리 ──

@student_bp.route('/stage3')
@login_required
def stage3():
    completed = get_completed_substeps(3)
    if not completed:
        return redirect(url_for('student.stage3_step', step=1))
    next_step = min(max(completed) + 1, 3)
    return redirect(url_for('student.stage3_step', step=next_step))


@student_bp.route('/stage3/step/<int:step>', methods=['GET', 'POST'])
@login_required
def stage3_step(step):
    if step not in range(1, 4):
        return redirect(url_for('student.stage3_step', step=1))

    completed = get_completed_substeps(3)
    idea = ProjectIdea.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        try:
            if not idea:
                idea = ProjectIdea(user_id=current_user.id)
                db.session.add(idea)

            if step == 1:
                idea.data_source = request.form.get('data_source', '').strip()
                idea.file_name   = request.form.get('file_name', '').strip()
            elif step == 2:
                idea.data_rows   = request.form.get('data_rows', '').strip()
                idea.data_cols   = request.form.get('data_cols', '').strip()
                idea.column_list = request.form.get('column_list', '').strip()
            elif step == 3:
                idea.missing_handling = request.form.get('missing_handling', '').strip()
                idea.outlier_handling = request.form.get('outlier_handling', '').strip()

            save_progress(3, step)
            db.session.commit()
        except Exception:
            db.session.rollback()

        if request.form.get('save_action') == 'save_only':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True})
            flash('저장되었습니다.', 'success')
            return redirect(url_for('student.stage3_step', step=step))

        if step < 3:
            return redirect(url_for('student.stage3_step', step=step + 1))
        flash('3단계를 완료했습니다! 수고했어요.', 'success')
        return redirect(url_for('student.dashboard'))

    template_map = {
        1: 'student/stage3/step1.html',
        2: 'student/stage3/step2.html',
        3: 'student/stage3/step3.html',
    }

    return render_template(
        template_map[step],
        step=step,
        completed=completed,
        already_completed=(step in completed),
        idea=idea
    )
