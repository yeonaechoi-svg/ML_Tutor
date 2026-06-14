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

// AI Checkpoint submit
function submitCheckpoint(stage, substep, btnId, feedbackId, nextBtnId) {
    const textarea = document.getElementById('answer_' + stage + '_' + substep);
    const answer = textarea ? textarea.value.trim() : '';

    if (!answer) {
        alert('답변을 입력해주세요.');
        return;
    }

    const btn = document.getElementById(btnId);
    const feedbackEl = document.getElementById(feedbackId);

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
            feedbackEl.textContent = data.feedback;
            feedbackEl.classList.add('visible');
            if (nextBtnId) {
                const nextBtn = document.getElementById(nextBtnId);
                if (nextBtn) {
                    nextBtn.disabled = false;
                    nextBtn.style.display = 'inline-block';
                }
            }
            btn.style.display = 'none';
            textarea.disabled = true;
            feedbackEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
