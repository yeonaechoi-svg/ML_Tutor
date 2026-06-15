from flask import request, jsonify
from flask_login import login_required, current_user
from app.ai_tutor import ai_tutor_bp
from app.ai_tutor.prompts import SYSTEM_PROMPT, get_checkpoint
from app.models import ChatLog
from app import db
import anthropic
import os


@ai_tutor_bp.route('/checkpoint', methods=['POST'])
@login_required
def checkpoint():
    data = request.get_json()
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    stage = data.get('stage')
    substep = data.get('substep')
    student_answer = data.get('student_answer', '').strip()

    if not stage or not substep or not student_answer:
        return jsonify({'error': '필수 항목이 누락되었습니다.'}), 400

    cp = get_checkpoint(stage, substep)
    if not cp:
        return jsonify({'error': '해당 체크포인트를 찾을 수 없습니다.'}), 404

    session_id = f"{current_user.id}_{stage}_{substep}"
    context = cp.get('context', '')
    question = cp.get('question', '')
    context_prefix = f"[학습 맥락]\n{context}\n\n[체크포인트 질문]\n{question}\n\n[학생 답변]\n"

    history = ChatLog.query.filter_by(
        user_id=current_user.id, stage=stage, substep=substep
    ).order_by(ChatLog.created_at).all()

    messages = []
    if not history:
        messages.append({'role': 'user', 'content': context_prefix + student_answer})
    else:
        first_user_injected = False
        for log in history:
            if log.role == 'user' and not first_user_injected:
                messages.append({'role': 'user', 'content': context_prefix + log.content})
                first_user_injected = True
            else:
                messages.append({'role': log.role, 'content': log.content})
        messages.append({'role': 'user', 'content': student_answer})

    try:
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        feedback = response.content[0].text
    except anthropic.APIError as e:
        return jsonify({'error': f'AI 튜터 오류: {str(e)}'}), 500
    except Exception:
        return jsonify({'error': 'AI 튜터에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.'}), 500

    try:
        db.session.add(ChatLog(
            user_id=current_user.id, stage=stage, substep=substep,
            session_id=session_id, role='user', content=student_answer
        ))
        db.session.add(ChatLog(
            user_id=current_user.id, stage=stage, substep=substep,
            session_id=session_id, role='assistant', content=feedback
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({'feedback': feedback})


@ai_tutor_bp.route('/suggest-problems', methods=['POST'])
@login_required
def suggest_problems():
    data = request.get_json()
    interest_field = (data.get('interest_field') or '').strip()
    if not interest_field:
        return jsonify({'error': '관심 분야를 먼저 입력해주세요.'}), 400

    prompt = (
        f"관심 분야: {interest_field}\n\n"
        "고등학생이 위 관심 분야에서 기계학습 프로젝트로 다룰 수 있는 "
        "실제적이고 공감 가능한 문제 상황 5가지를 제시해주세요.\n"
        "각 항목은 한 문장으로, 구체적인 불편함이나 궁금증을 담아주세요.\n"
        "반드시 JSON 배열만 반환하세요. 다른 설명 없이:\n"
        '[\"문제 상황 1\", \"문제 상황 2\", \"문제 상황 3\", \"문제 상황 4\", \"문제 상황 5\"]'
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=600,
            system="당신은 고등학교 기계학습 수업의 AI 튜터입니다. 요청한 형식(JSON 배열)만 반환하세요.",
            messages=[{'role': 'user', 'content': prompt}]
        )
        import json
        text = response.content[0].text.strip()
        # JSON 배열 추출
        start = text.find('[')
        end = text.rfind(']') + 1
        problems = json.loads(text[start:end]) if start != -1 else []
        return jsonify({'problems': problems})
    except Exception as e:
        return jsonify({'error': f'AI 오류: {str(e)}'}), 500


@ai_tutor_bp.route('/suggest-definitions', methods=['POST'])
@login_required
def suggest_definitions():
    data = request.get_json()
    ml_problem = (data.get('ml_problem') or '').strip()
    if not ml_problem:
        return jsonify({'error': '기계학습으로 해결할 문제를 먼저 입력해주세요.'}), 400

    prompt = (
        f"기계학습 문제: {ml_problem}\n\n"
        "위 기계학습 문제에 대해 아래 4가지 항목의 예시 답변을 작성해주세요.\n"
        "고등학생이 참고할 수 있도록 구체적이고 이해하기 쉽게 작성하세요.\n"
        "반드시 JSON 형태로만 반환하세요:\n"
        '{"current_state": "현재 상태 예시 (2~3문장)", '
        '"target_state": "목표 상태 예시 (2~3문장)", '
        '"key_elements": "핵심 요소 예시 (쉼표로 구분된 변수 목록)", '
        '"sub_problems": "작은 문제 예시 (① → ② → ③ 형태)"}'
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=700,
            system="당신은 고등학교 기계학습 수업의 AI 튜터입니다. 요청한 JSON 형식만 반환하세요.",
            messages=[{'role': 'user', 'content': prompt}]
        )
        import json
        text = response.content[0].text.strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        result = json.loads(text[start:end]) if start != -1 else {}
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'AI 오류: {str(e)}'}), 500


@ai_tutor_bp.route('/suggest-ml-solutions', methods=['POST'])
@login_required
def suggest_ml_solutions():
    data = request.get_json()
    problem_situation = (data.get('problem_situation') or '').strip()
    if not problem_situation:
        return jsonify({'error': '문제 상황을 먼저 입력해주세요.'}), 400

    prompt = (
        f"문제 상황: {problem_situation}\n\n"
        "위 문제 상황에서 고등학생이 기계학습으로 해결할 수 있는 구체적인 접근 방법 5가지를 제시해주세요.\n"
        "각 항목은 '~을 예측한다', '~을 분류한다', '~을 그룹으로 나눈다' 형태로 한 문장으로 작성하세요.\n"
        "반드시 JSON 배열만 반환하세요. 다른 설명 없이:\n"
        '[\"해결 방법 1\", \"해결 방법 2\", \"해결 방법 3\", \"해결 방법 4\", \"해결 방법 5\"]'
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=600,
            system="당신은 고등학교 기계학습 수업의 AI 튜터입니다. 요청한 형식(JSON 배열)만 반환하세요.",
            messages=[{'role': 'user', 'content': prompt}]
        )
        import json
        text = response.content[0].text.strip()
        start = text.find('[')
        end = text.rfind(']') + 1
        solutions = json.loads(text[start:end]) if start != -1 else []
        return jsonify({'solutions': solutions})
    except Exception as e:
        return jsonify({'error': f'AI 오류: {str(e)}'}), 500


@ai_tutor_bp.route('/history', methods=['GET'])
@login_required
def history():
    stage = request.args.get('stage', type=int)
    substep = request.args.get('substep', type=int)

    if not stage or not substep:
        return jsonify({'error': '필수 항목이 누락되었습니다.'}), 400

    logs = ChatLog.query.filter_by(
        user_id=current_user.id, stage=stage, substep=substep
    ).order_by(ChatLog.created_at).all()

    messages = [{'role': log.role, 'content': log.content} for log in logs]
    return jsonify({'messages': messages})
