// 업로드 페이지 - 파일 선택 / 드래그 앤 드롭
// 파일이 선택돼야 "첨부하고 열기" 버튼이 활성화된다.

(function () {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileHint = document.getElementById('fileHint');
    const submitBtn = document.getElementById('submitBtn');
    const titleInput = document.getElementById('titleInput');

    if (!dropZone || !fileInput) return;

    const DEFAULT_HINT = fileHint.textContent;

    function showSelected() {
        const file = fileInput.files[0];
        const fileSize = file.size;
        const maxSize = 50 * 1024 * 1024;

        if (!file) {
            fileHint.textContent = DEFAULT_HINT;
            fileHint.classList.add('text-body-tertiary');
            submitBtn.disabled = true;
            return;
        }

        fileHint.textContent = file.name;
        fileHint.classList.remove('text-body-tertiary');
        submitBtn.disabled = false;

        // 제목을 파일명(확장자 제외)으로 채워준다.
        if (titleInput) {
            titleInput.value = file.name.replace(/\.[^.]+$/, '');
        }

        if (fileSize > maxSize) {
            alert('파일 용량이 50MB를 초과했습니다.');
            fileInput.value = '';
            titleInput.value = '';
            fileHint.textContent = DEFAULT_HINT;
            fileHint.classList.add('text-body-tertiary')
            submitBtn.disabled = true;
        }
    }

    fileInput.addEventListener('change', showSelected);

    ['dragenter', 'dragover'].forEach(function (type) {
        dropZone.addEventListener(type, function (e) {
            e.preventDefault();
            dropZone.classList.add('bg-body-tertiary');
        });
    });

    ['dragleave', 'drop'].forEach(function (type) {
        dropZone.addEventListener(type, function (e) {
            e.preventDefault();
            dropZone.classList.remove('bg-body-tertiary');
        });
    });

    dropZone.addEventListener('drop', function (e) {
        if (!e.dataTransfer.files.length) return;
        fileInput.files = e.dataTransfer.files;
        showSelected();
    });
})();
