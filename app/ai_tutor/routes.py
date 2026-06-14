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

    question = cp['question']
    context = cp.get('context', '')

    user_message = (
        f"[학습 맥락]\n{context}\n\n"
        f"[체크포인트 질문]\n{question}\n\n"
        f"[학생 답변]\n{student_answer}"
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        message = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_message}]
        )
        feedback = message.content[0].text
    except anthropic.APIError as e:
        return jsonify({'error': f'AI 튜터 오류: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': 'AI 튜터에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.'}), 500

    try:
        log = ChatLog(
            user_id=current_user.id,
            stage=stage,
            substep=substep,
            question=question,
            answer=student_answer,
            feedback=feedback
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({'feedback': feedback})
