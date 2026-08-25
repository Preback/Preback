// 상세 페이지 댓글 입력 - 내용이 있을 때만 "등록" 버튼 활성화
// 슬라이드 선택과 댓글 목록은 서버(SSR)에서 렌더링하므로 여기서는 다루지 않는다.

(function () {
    const body = document.getElementById('commentBody');
    const submit = document.getElementById('commentSubmit');

    if (!body || !submit) return;

    function sync() {
        submit.disabled = body.value.trim() === '';
    }

    body.addEventListener('input', sync);
    sync();
})();
