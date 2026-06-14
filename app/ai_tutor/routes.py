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
