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

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function applyInline(str) {
    return str.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function markdownToHtml(text) {
    var html = '';
    text.split('\n').forEach(function(line) {
        var esc = escapeHtml(line);
        if (/^## /.test(esc)) {
            html += '<div class="chat-md-h2">' + applyInline(esc.slice(3)) + '</div>';
        } else if (/^### /.test(esc)) {
            html += '<div class="chat-md-h3">' + applyInline(esc.slice(4)) + '</div>';
        } else if (/^[-*] /.test(esc)) {
            html += '<div class="chat-md-li">' + applyInline(esc.slice(2)) + '</div>';
        } else if (esc.trim() === '') {
            html += '<div style="height:5px"></div>';
        } else {
            html += '<div class="chat-md-p">' + applyInline(esc) + '</div>';
        }
    });
    return html;
}

function appendFeedback(chatBoxId, content) {
    var chatBox = document.getElementById(chatBoxId);
    if (!chatBox) return;
    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble assistant';
    bubble.innerHTML = markdownToHtml(content);
    chatBox.appendChild(bubble);
    chatBox.scrollTop = chatBox.scrollHeight;
}

/* ── AI Code Help Sidebar ── */
var SIDEBAR_STAGE = 0;
var SIDEBAR_STEP = 0;

function toggleSidebar() {
    var sidebar = document.getElementById('ai-code-sidebar');
    var toggle = document.getElementById('ai-sidebar-toggle');
    if (!sidebar || !toggle) return;
    sidebar.classList.toggle('open');
    if (sidebar.classList.contains('open')) {
        toggle.style.right = '360px';
        toggle.innerHTML = '✕ 닫기';
        toggle.style.writingMode = 'horizontal-tb';
        toggle.style.padding = '10px 8px';
        toggle.style.borderRadius = '10px 0 0 10px';
    } else {
        toggle.style.right = '0';
        toggle.innerHTML = '💬\nAI\n도우미';
        toggle.style.writingMode = 'vertical-rl';
        toggle.style.padding = '16px 9px';
    }
}

function submitSidebarChat() {
    var input = document.getElementById('sidebar-input');
    if (!input) return;
    var question = input.value.trim();
    if (!question) { alert('질문을 입력해주세요.'); return; }

    var chatBox = document.getElementById('sidebar-chat-box');
    var sendBtn = document.getElementById('sidebar-send-btn');

    var userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user';
    userBubble.textContent = question;
    chatBox.appendChild(userBubble);
    chatBox.scrollTop = chatBox.scrollHeight;

    input.value = '';
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span class="spinner"></span> AI 응답 중...';

    fetch('/ai-tutor/code-help', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage: SIDEBAR_STAGE, step: SIDEBAR_STEP, question: question })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '전송하기';
        if (data.answer) {
            appendFeedback('sidebar-chat-box', data.answer);
        } else {
            appendFeedback('sidebar-chat-box', '오류가 발생했습니다: ' + (data.error || '다시 시도해주세요.'));
        }
    })
    .catch(function() {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '전송하기';
        appendFeedback('sidebar-chat-box', '네트워크 오류가 발생했습니다. 다시 시도해주세요.');
    });
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
