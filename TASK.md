# 작업지시서 v3 — AI 튜터 대화형 구조로 변경

> 반드시 CLAUDE.md를 먼저 읽고 프로젝트 맥락을 파악한 뒤 작업하세요.
> 기존 코드 구조를 최대한 유지하면서 수정합니다.

---

## 문제 정의

현재 AI 튜터는 아래 흐름으로 동작한다.

```
학생 답변 제출
    ↓
AI 피드백 1회 표시
    ↓
textarea 비활성화 + 제출 버튼 숨김  ← 문제!
    ↓
끝 (대화 불가)
```

피드백을 받고 나서 대화를 이어갈 수 없어 스캐폴딩이 제대로 작동하지 않는다.
학생이 AI 피드백을 읽고 추가 답변을 입력할 수 있어야 하고,
AI는 이전 대화 맥락을 유지하면서 이어서 피드백을 줘야 한다.

---

## 목표 흐름

```
[AI 체크포인트 질문 표시]
    ↓
학생이 답변 입력 → 제출
    ↓
AI 피드백 표시 (대화창에 누적)
    ↓
학생이 추가 답변 입력 가능 (textarea 유지)
    ↓
AI가 이전 대화 맥락을 포함해서 이어서 피드백
    ↓
(반복 — 학생이 충분히 이해할 때까지)
    ↓
"이해했습니다" 버튼 클릭 → 다음 단계로 이동
```

---

## 작업 1. ChatLog 모델 수정 (models.py)

현재 ChatLog는 단일 질문-답변-피드백을 저장한다.
대화형으로 변경하기 위해 대화 세션 개념을 추가한다.

```python
class ChatLog(db.Model):
    __tablename__ = 'chat_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stage = db.Column(db.Integer, nullable=False)
    substep = db.Column(db.Integer, nullable=False)
    session_id = db.Column(db.String(50), nullable=False)  # 추가: 대화 세션 구분
    role = db.Column(db.String(10), nullable=False)        # 추가: 'user' 또는 'assistant'
    content = db.Column(db.Text, nullable=False)           # 추가: 대화 내용
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

기존 question, answer, feedback 컬럼 대신
role + content 구조로 변경하여 대화 히스토리를 순서대로 저장한다.

session_id는 같은 체크포인트 내의 대화를 묶는 키로 사용한다.
형식: f"{user_id}_{stage}_{substep}"

---

## 작업 2. AI 튜터 라우트 수정 (app/ai_tutor/routes.py)

### 2-1. 기존 /checkpoint 엔드포인트 수정

대화 히스토리를 DB에서 불러와 Claude API에 전달하도록 수정한다.

```python
@ai_tutor_bp.route('/checkpoint', methods=['POST'])
@login_required
def checkpoint():
    data = request.get_json()
    stage = data.get('stage')
    substep = data.get('substep')
    student_answer = data.get('student_answer', '').strip()

    if not stage or not substep or not student_answer:
        return jsonify({'error': '필수 항목이 누락되었습니다.'}), 400

    cp = get_checkpoint(stage, substep)
    if not cp:
        return jsonify({'error': '해당 체크포인트를 찾을 수 없습니다.'}), 404

    session_id = f"{current_user.id}_{stage}_{substep}"

    # 1. 기존 대화 히스토리 불러오기
    history = ChatLog.query.filter_by(
        user_id=current_user.id,
        stage=stage,
        substep=substep,
        session_id=session_id
    ).order_by(ChatLog.created_at.asc()).all()

    # 2. Claude API messages 배열 구성
    messages = []

    # 첫 번째 대화라면 체크포인트 질문을 첫 user 메시지로 포함
    if not history:
        context = cp.get('context', '')
        question = cp['question']
        first_message = (
            f"[학습 맥락]\n{context}\n\n"
            f"[체크포인트 질문]\n{question}\n\n"
            f"[학생 첫 번째 답변]\n{student_answer}"
        )
        messages.append({'role': 'user', 'content': first_message})
    else:
        # 기존 대화 히스토리 복원
        for log in history:
            messages.append({'role': log.role, 'content': log.content})
        # 새 학생 답변 추가
        messages.append({'role': 'user', 'content': student_answer})

    # 3. Claude API 호출
    try:
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        feedback = response.content[0].text
    except Exception as e:
        return jsonify({'error': 'AI 튜터에 연결할 수 없습니다.'}), 500

    # 4. 대화 내용 DB 저장 (학생 답변 + AI 피드백)
    try:
        # 첫 대화면 초기 질문도 저장
        if not history:
            db.session.add(ChatLog(
                user_id=current_user.id,
                stage=stage, substep=substep,
                session_id=session_id,
                role='user',
                content=messages[0]['content']
            ))
        else:
            db.session.add(ChatLog(
                user_id=current_user.id,
                stage=stage, substep=substep,
                session_id=session_id,
                role='user',
                content=student_answer
            ))
        db.session.add(ChatLog(
            user_id=current_user.id,
            stage=stage, substep=substep,
            session_id=session_id,
            role='assistant',
            content=feedback
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({'feedback': feedback})
```

### 2-2. 대화 히스토리 조회 엔드포인트 추가

페이지 새로고침 시 기존 대화 내용을 복원하기 위한 API 추가.

```python
@ai_tutor_bp.route('/history', methods=['GET'])
@login_required
def history():
    stage = request.args.get('stage', type=int)
    substep = request.args.get('substep', type=int)
    session_id = f"{current_user.id}_{stage}_{substep}"

    logs = ChatLog.query.filter_by(
        user_id=current_user.id,
        stage=stage,
        substep=substep,
        session_id=session_id
    ).order_by(ChatLog.created_at.asc()).all()

    return jsonify({
        'history': [
            {'role': log.role, 'content': log.content}
            for log in logs
        ]
    })
```

---

## 작업 3. 프론트엔드 수정 (app/static/js/main.js)

기존 submitCheckpoint 함수를 대화형으로 완전히 교체한다.

### 3-1. 대화창 초기화 함수 추가

```javascript
// 페이지 로드 시 기존 대화 히스토리 복원
function loadChatHistory(stage, substep, chatBoxId) {
    fetch('/ai-tutor/history?stage=' + stage + '&substep=' + substep)
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.history && data.history.length > 0) {
            data.history.forEach(function(msg) {
                if (msg.role === 'assistant') {
                    appendFeedback(chatBoxId, msg.content);
                } else {
                    // user 메시지는 표시하지 않음 (질문이 이미 표시됨)
                }
            });
            // 이미 대화한 경우 "이해했습니다" 버튼 활성화
            var completeBtn = document.getElementById('complete_' + stage + '_' + substep);
            if (completeBtn) completeBtn.style.display = 'inline-block';
        }
    });
}
```

### 3-2. submitCheckpoint 함수 교체

```javascript
function submitCheckpoint(stage, substep, btnId, chatBoxId, nextBtnId) {
    var textarea = document.getElementById('answer_' + stage + '_' + substep);
    var answer = textarea ? textarea.value.trim() : '';

    if (!answer) {
        alert('답변을 입력해주세요.');
        return;
    }

    var btn = document.getElementById(btnId);
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> AI 튜터가 피드백을 작성 중입니다...';

    fetch('/ai-tutor/checkpoint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage: stage, substep: substep, student_answer: answer })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.feedback) {
            // 대화창에 피드백 누적 표시
            appendFeedback(chatBoxId, data.feedback);

            // textarea 초기화 (재입력 가능)
            textarea.value = '';
            textarea.disabled = false;
            textarea.placeholder = 'AI 튜터의 피드백을 읽고 추가 답변을 입력하세요...';
            textarea.focus();

            // 제출 버튼 복원
            btn.disabled = false;
            btn.innerHTML = '추가 답변 제출';

            // "이해했습니다" 버튼 표시
            var completeBtn = document.getElementById('complete_' + stage + '_' + substep);
            if (completeBtn) completeBtn.style.display = 'inline-block';

        } else {
            alert(data.error || 'AI 튜터 오류가 발생했습니다.');
            btn.disabled = false;
            btn.innerHTML = '제출하기';
        }
    })
    .catch(function() {
        alert('네트워크 오류가 발생했습니다. 다시 시도해주세요.');
        btn.disabled = false;
        btn.innerHTML = '제출하기';
    });
}

// 피드백을 대화창에 누적 표시
function appendFeedback(chatBoxId, content) {
    var chatBox = document.getElementById(chatBoxId);
    if (!chatBox) return;

    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble assistant';
    bubble.textContent = content;
    chatBox.appendChild(bubble);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// "이해했습니다" 버튼 클릭 → 다음 단계 활성화
function completeCheckpoint(stage, substep, nextBtnId) {
    var nextBtn = document.getElementById(nextBtnId);
    if (nextBtn) {
        nextBtn.disabled = false;
        nextBtn.style.display = 'inline-block';
    }
    // textarea와 제출 버튼 비활성화
    var textarea = document.getElementById('answer_' + stage + '_' + substep);
    var submitBtn = document.getElementById('submit_' + stage + '_' + substep);
    if (textarea) textarea.disabled = true;
    if (submitBtn) submitBtn.style.display = 'none';

    var completeBtn = document.getElementById('complete_' + stage + '_' + substep);
    if (completeBtn) completeBtn.style.display = 'none';
}
```

---

## 작업 4. HTML 템플릿 수정

체크포인트가 있는 모든 step HTML 파일의 체크포인트 섹션을 아래 구조로 교체한다.
(step2.html 예시 — 나머지 step도 동일한 패턴 적용)

```html
<!-- AI 체크포인트 -->
<div class="checkpoint-box">
    <div class="checkpoint-title">AI 체크포인트</div>
    <div class="checkpoint-question">{{ 질문 내용 }}</div>

    {% if already_completed %}
        <div class="chat-box" id="chat_1_2"></div>
        <div class="checkpoint-feedback visible">이미 완료한 단계입니다.</div>
        <div class="step-nav">
            <a href="{{ url_for('student.stage1_step', step=1) }}" class="btn btn-secondary">← 이전</a>
            <a href="{{ url_for('student.stage1_step', step=3) }}" class="btn btn-primary">다음 →</a>
        </div>
    {% else %}
        <!-- 대화창 (피드백 누적 표시) -->
        <div class="chat-box" id="chat_1_2"></div>

        <!-- 답변 입력 -->
        <textarea
            id="answer_1_2"
            class="form-control"
            rows="4"
            placeholder="여기에 답변을 작성해주세요...">
        </textarea>

        <div style="margin-top:12px; display:flex; gap:10px; flex-wrap:wrap;">
            <!-- 제출 버튼 -->
            <button
                id="submit_1_2"
                class="btn btn-success"
                onclick="submitCheckpoint(1, 2, 'submit_1_2', 'chat_1_2', 'next_1_2')">
                제출하기
            </button>

            <!-- 이해했습니다 버튼 (첫 제출 후 표시) -->
            <button
                id="complete_1_2"
                class="btn btn-secondary"
                style="display:none"
                onclick="completeCheckpoint(1, 2, 'next_1_2')">
                ✓ 이해했습니다
            </button>
        </div>

        <form method="POST" id="form_1_2">
            <div class="step-nav" style="margin-top:16px;">
                <a href="{{ url_for('student.stage1_step', step=1) }}" class="btn btn-secondary">← 이전</a>
                <button
                    type="submit"
                    id="next_1_2"
                    class="btn btn-primary"
                    disabled
                    style="display:none">
                    다음: 기계학습 유형 →
                </button>
            </div>
        </form>

        <!-- 페이지 로드 시 기존 대화 복원 -->
        <script>
            loadChatHistory(1, 2, 'chat_1_2');
        </script>
    {% endif %}
</div>
```

---

## 작업 5. CSS 추가 (app/static/css/main.css)

대화창 스타일을 추가한다.

```css
/* 대화창 */
.chat-box {
    max-height: 400px;
    overflow-y: auto;
    padding: 12px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-bottom: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

/* AI 피드백 말풍선 */
.chat-bubble.assistant {
    background: #eff6ff;
    border: 1px solid #93c5fd;
    border-radius: 12px 12px 12px 2px;
    padding: 12px 16px;
    font-size: 14px;
    color: #1e3a5f;
    line-height: 1.7;
    white-space: pre-wrap;
    max-width: 90%;
}
```

---

## 작업 6. DB 마이그레이션

ChatLog 모델이 변경되므로 기존 DB를 삭제하고 새로 생성한다.

```bash
# instance 폴더의 DB 파일 삭제
del instance\ml_tutor.db

# 서버 재실행 시 새 구조로 자동 생성
python run.py
```

---

## 작업 7. GitHub 커밋 및 푸시

```bash
git add .
git commit -m "AI 튜터 대화형 구조로 변경 — 멀티턴 대화 지원"
git push origin master
```

---

## 완료 기준

- [ ] 체크포인트에서 AI 피드백 후 textarea가 초기화되어 추가 입력 가능
- [ ] 대화창에 피드백이 누적 표시됨
- [ ] AI가 이전 대화 맥락을 포함하여 이어서 피드백 제공
- [ ] "이해했습니다" 버튼 클릭 후 다음 단계 버튼 활성화
- [ ] 페이지 새로고침 후 기존 대화 내용 복원
- [ ] python run.py 실행 후 오류 없이 동작 확인
