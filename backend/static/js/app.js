document.addEventListener('DOMContentLoaded', () => {
    // Theme toggling
    const themeToggleBtn = document.getElementById('themeToggle');
    if (themeToggleBtn) {
        // Load preference
        const currentTheme = localStorage.getItem('theme') || 'theme-light';
        document.body.className = currentTheme;

        themeToggleBtn.addEventListener('click', () => {
            if (document.body.classList.contains('theme-light')) {
                document.body.classList.remove('theme-light');
                document.body.classList.add('theme-dark');
                localStorage.setItem('theme', 'theme-dark');
            } else {
                document.body.classList.remove('theme-dark');
                document.body.classList.add('theme-light');
                localStorage.setItem('theme', 'theme-light');
            }
        });
    }

    // Sidebar toggling for mobile
    const hamburger = document.getElementById('hamburger');
    const sidebar = document.getElementById('sidebar');
    if (hamburger && sidebar) {
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
    }

    // Upload zone interactions
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');

    if (uploadZone && fileInput) {
        uploadZone.addEventListener('click', () => fileInput.click());
        
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                handleFileUpload();
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                handleFileUpload();
            }
        });
    }

    function handleFileUpload() {
        if (!uploadForm) return;
        const uploadStatus = document.getElementById('uploadStatus');
        if (uploadStatus) {
            uploadStatus.style.display = 'block';
            uploadStatus.innerHTML = `
                <div class="loading-state">
                    <div class="spinner"></div>
                    <div class="loading-steps">
                        <div><span class="check">✓</span> PDF uploaded</div>
                        <div class="active">● Extracting text and indexing...</div>
                    </div>
                </div>
            `;
        }
        uploadForm.submit();
    }
});
