// Copy code block to clipboard
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('copy-btn')) {
        const block = e.target.closest('.code-block');
        const code = block.querySelector('pre').textContent;
        navigator.clipboard.writeText(code).then(function() {
            const orig = e.target.textContent;
            e.target.textContent = '복사됨!';
            setTimeout(function() { e.target.textContent = orig; }, 1500);
        });
    }
});

function loadChatHistory(stage, substep, chatBoxId) {
    fetch('/ai-tutor/history?stage=' + stage + '&substep=' + substep)
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (!data.messages || data.messages.length === 0) return;
        data.messages.forEach(function(msg) {
            if (msg.role === 'assistant') {
                appendFeedback(chatBoxId, msg.content);
            } else {
                var chatBox = document.getElementById(chatBoxId);
                if (!chatBox) return;
                var bubble = document.createElement('div');
                bubble.className = 'chat-bubble user';
                bubble.textContent = msg.content;
                chatBox.appendChild(bubble);
            }
        });
        var completeBtn = document.getElementById('complete_' + stage + '_' + substep);
        if (completeBtn) completeBtn.style.display = 'inline-block';
        var submitBtn = document.getElementById('submit_' + stage + '_' + substep);
        if (submitBtn) submitBtn.innerHTML = '추가 답변 제출';
        var chatBox = document.getElementById(chatBoxId);
        if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
    })
    .catch(function() {});
}

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

    var chatBox = document.getElementById(chatBoxId);
    if (chatBox) {
        var userBubble = document.createElement('div');
        userBubble.className = 'chat-bubble user';
        userBubble.textContent = answer;
        chatBox.appendChild(userBubble);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    fetch('/ai-tutor/checkpoint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage: stage, substep: substep, student_answer: answer })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        btn.disabled = false;
        btn.innerHTML = '추가 답변 제출';

        if (data.feedback) {
            appendFeedback(chatBoxId, data.feedback);
            if (textarea) textarea.value = '';
            var completeBtn = document.getElementById('complete_' + stage + '_' + substep);
            if (completeBtn) completeBtn.style.display = 'inline-block';
        } else {
            alert(data.error || 'AI 튜터 오류가 발생했습니다.');
        }
    })
    .catch(function() {
        alert('네트워크 오류가 발생했습니다. 다시 시도해주세요.');
        btn.disabled = false;
        btn.innerHTML = '추가 답변 제출';
    });
}

function appendFeedback(chatBoxId, content) {
    var chatBox = document.getElementById(chatBoxId);
    if (!chatBox) return;
    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble assistant';
    bubble.textContent = content;
    chatBox.appendChild(bubble);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function completeCheckpoint(stage, substep, nextBtnId) {
    var nextBtn = document.getElementById(nextBtnId);
    if (nextBtn) {
        nextBtn.disabled = false;
        nextBtn.style.display = 'inline-block';
    }
    var textarea = document.getElementById('answer_' + stage + '_' + substep);
    if (textarea) textarea.disabled = true;
    var submitBtn = document.getElementById('submit_' + stage + '_' + substep);
    if (submitBtn) submitBtn.disabled = true;
    var completeBtn = document.getElementById('complete_' + stage + '_' + substep);
    if (completeBtn) completeBtn.style.display = 'none';
}
