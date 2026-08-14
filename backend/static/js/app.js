// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }
}

initTheme();

document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        });
    }

    // Sidebar Toggle Logic (Desktop Collapse + Mobile Overlay)
    const mobileToggle = document.getElementById('mobileNavToggle');
    const closeSidebarBtn = document.getElementById('closeSidebarBtn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (mobileToggle && sidebar && overlay) {
        // Main hamburger button
        mobileToggle.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                // Mobile behavior
                sidebar.classList.add('open');
                overlay.style.display = 'block';
            } else {
                // Desktop behavior
                document.body.classList.toggle('sidebar-collapsed');
            }
        });

        // Close/collapse action
        const closeSidebar = () => {
            if (window.innerWidth <= 768) {
                // Mobile behavior
                sidebar.classList.remove('open');
                overlay.style.display = 'none';
            } else {
                // Desktop behavior
                document.body.classList.add('sidebar-collapsed');
            }
        };

        overlay.addEventListener('click', closeSidebar);
        if (closeSidebarBtn) closeSidebarBtn.addEventListener('click', closeSidebar);
    }

    // Paper Chat Logic
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const sendBtn = document.getElementById('sendBtn');
    const paperIdEl = document.getElementById('paperId');
    let isGenerating = false;

    if (chatForm && chatInput && chatMessages && paperIdEl) {
        const paperId = paperIdEl.value;

        // Load History
        if (paperId) {
            fetch(`/api/chat/${paperId}`)
                .then(res => res.json())
                .then(data => {
                    if (data.history && data.history.length > 0) {
                        chatMessages.innerHTML = ''; // clear default greeting
                        data.history.forEach(msg => {
                            if (msg.role === 'user') {
                                chatMessages.innerHTML += `
                                    <div class="chat-msg user">
                                        <div class="msg-bubble">${escapeHTML(msg.content)}</div>
                                    </div>
                                `;
                            } else {
                                let sourcesHtml = '';
                                if (msg.sources && msg.sources.length > 0) {
                                    const uniquePages = [...new Set(msg.sources.map(s => s.page))].sort((a,b)=>a-b);
                                    sourcesHtml = `
                                        <div class="msg-sources">
                                            <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem;">SOURCES</div>
                                            <div style="display:flex; flex-wrap:wrap; gap:0.375rem;">
                                                ${uniquePages.map(p => `<span class="source-pill">Page ${p}</span>`).join('')}
                                            </div>
                                        </div>
                                    `;
                                }
                                chatMessages.innerHTML += `
                                    <div class="chat-msg ai">
                                        <div class="msg-bubble">
                                            ${formatAnswer(msg.content)}
                                            ${sourcesHtml}
                                        </div>
                                    </div>
                                `;
                            }
                        });
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                });
        }

        // Shift+Enter to newline, Enter to send
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!isGenerating && chatInput.value.trim() !== '') {
                    chatForm.dispatchEvent(new Event('submit'));
                }
            }
        });

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isGenerating) return;

            const question = chatInput.value.trim();
            const paperId = document.getElementById('paperId').value;
            
            if (!question || !paperId) return;

            // Lock UI
            isGenerating = true;
            chatInput.disabled = true;
            sendBtn.disabled = true;
            chatInput.value = '';

            // Render User Message
            chatMessages.innerHTML += `
                <div class="chat-msg user">
                    <div class="msg-bubble">${escapeHTML(question)}</div>
                </div>
            `;
            
            // Render Loading Indicator
            const loadingId = 'loading-' + Date.now();
            chatMessages.innerHTML += `
                <div class="chat-msg ai" id="${loadingId}">
                    <div class="msg-bubble" style="color:var(--text-muted); display:flex; gap:0.5rem; align-items:center;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin" style="animation: spin 1s linear infinite;">
                            <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                        </svg>
                        ResearchAI is analyzing the paper...
                    </div>
                </div>
            `;
            chatMessages.scrollTop = chatMessages.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ paper_id: paperId, question })
                });

                const data = await res.json();
                document.getElementById(loadingId).remove();

                if (!res.ok || !data.success) {
                    const errorMsg = data.error || 'Something went wrong while processing your question. Please try again.';
                    chatMessages.innerHTML += `
                        <div class="chat-msg ai">
                            <div class="msg-bubble" style="border-color:var(--danger); background:rgba(239, 68, 68, 0.05); color:var(--danger);">
                                ${escapeHTML(errorMsg)}
                            </div>
                        </div>
                    `;
                } else {
                    let sourcesHtml = '';
                    if (data.sources && data.sources.length > 0) {
                        const uniquePages = [...new Set(data.sources.map(s => s.page))].sort((a,b)=>a-b);
                        sourcesHtml = `
                            <div class="msg-sources">
                                <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem;">SOURCES</div>
                                <div style="display:flex; flex-wrap:wrap; gap:0.375rem;">
                                    ${uniquePages.map(p => `<span class="source-pill">Page ${p}</span>`).join('')}
                                </div>
                            </div>
                        `;
                    }

                    chatMessages.innerHTML += `
                        <div class="chat-msg ai">
                            <div class="msg-bubble">
                                ${formatAnswer(data.answer)}
                                ${sourcesHtml}
                            </div>
                        </div>
                    `;
                }
            } catch (err) {
                document.getElementById(loadingId).remove();
                chatMessages.innerHTML += `
                    <div class="chat-msg ai">
                        <div class="msg-bubble" style="border-color:var(--danger); background:rgba(239, 68, 68, 0.05); color:var(--danger);">
                            Network error. Please verify the backend is running.
                        </div>
                    </div>
                `;
            }

            // Unlock UI
            isGenerating = false;
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    // Global Chat Logic
    const globalChatForm = document.getElementById('globalChatForm');
    const globalChatInput = document.getElementById('globalChatInput');
    const globalChatMessages = document.getElementById('globalChatMessages');
    const globalSendBtn = document.getElementById('globalSendBtn');
    const globalPaperSelect = document.getElementById('globalPaperSelect');
    
    if (globalChatForm && globalPaperSelect) {
        // Load papers
        fetch('/api/papers')
            .then(res => res.json())
            .then(data => {
                if(data.papers) {
                    data.papers.forEach(p => {
                        const opt = document.createElement('option');
                        opt.value = p.paper_id;
                        opt.textContent = p.filename;
                        globalPaperSelect.appendChild(opt);
                    });

                    // Preselect if query param exists
                    const urlParams = new URLSearchParams(window.location.search);
                    const pid = urlParams.get('paper');
                    if(pid) {
                        globalPaperSelect.value = pid;
                        globalPaperSelect.dispatchEvent(new Event('change'));
                    }
                }
            });

        globalPaperSelect.addEventListener('change', () => {
            const hasPaper = globalPaperSelect.value !== '';
            globalChatInput.disabled = !hasPaper;
            globalSendBtn.disabled = !hasPaper;
            document.getElementById('globalChatStatus').innerHTML = hasPaper 
                ? '<span style="width:8px; height:8px; border-radius:50%; background:var(--success); display:inline-block;"></span> Ready'
                : '<span style="width:8px; height:8px; border-radius:50%; background:var(--border); display:inline-block;"></span> Select a paper to start';
            
            if (hasPaper) {
                globalChatInput.focus();
                const emptyState = document.getElementById('globalEmptyState');
                if (emptyState) emptyState.remove();
                
                // Clear previous messages
                globalChatMessages.innerHTML = '';
                
                // Fetch History
                fetch(`/api/chat/${globalPaperSelect.value}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.history && data.history.length > 0) {
                            data.history.forEach(msg => {
                                if (msg.role === 'user') {
                                    globalChatMessages.innerHTML += `
                                        <div class="chat-msg user">
                                            <div class="msg-bubble">${escapeHTML(msg.content)}</div>
                                        </div>
                                    `;
                                } else {
                                    let sourcesHtml = '';
                                    if (msg.sources && msg.sources.length > 0) {
                                        const uniquePages = [...new Set(msg.sources.map(s => s.page))].sort((a,b)=>a-b);
                                        sourcesHtml = `
                                            <div class="msg-sources">
                                                <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem;">SOURCES</div>
                                                <div style="display:flex; flex-wrap:wrap; gap:0.375rem;">
                                                    ${uniquePages.map(p => `<span class="source-pill">Page ${p}</span>`).join('')}
                                                </div>
                                            </div>
                                        `;
                                    }
                                    globalChatMessages.innerHTML += `
                                        <div class="chat-msg ai">
                                            <div class="msg-bubble">
                                                ${formatAnswer(msg.content)}
                                                ${sourcesHtml}
                                            </div>
                                        </div>
                                    `;
                                }
                            });
                            globalChatMessages.scrollTop = globalChatMessages.scrollHeight;
                        }
                    });
            } else {
                // Restore empty state if no paper selected
                globalChatMessages.innerHTML = `
                    <div class="chat-msg ai" id="globalEmptyState">
                        <div class="msg-bubble" style="text-align: center; background:transparent; border:none; color:var(--text-muted); margin-top: 4rem;">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="margin:0 auto 1rem auto; display:block;">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                            </svg>
                            <h3 style="margin-bottom: 0.5rem; color:var(--text);">Ask questions across your research library</h3>
                            <p>Select a paper from the dropdown above to start researching.</p>
                        </div>
                    </div>
                `;
            }
        });

        globalChatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!isGenerating && globalChatInput.value.trim() !== '') {
                    globalChatForm.dispatchEvent(new Event('submit'));
                }
            }
        });

        globalChatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isGenerating) return;

            const question = globalChatInput.value.trim();
            const paperId = globalPaperSelect.value;
            
            if (!question || !paperId) return;

            // Remove empty state
            const emptyState = document.getElementById('globalEmptyState');
            if (emptyState) emptyState.remove();

            isGenerating = true;
            globalChatInput.disabled = true;
            globalSendBtn.disabled = true;
            globalPaperSelect.disabled = true;
            globalChatInput.value = '';

            globalChatMessages.innerHTML += `
                <div class="chat-msg user">
                    <div class="msg-bubble">${escapeHTML(question)}</div>
                </div>
            `;
            
            const loadingId = 'loading-' + Date.now();
            globalChatMessages.innerHTML += `
                <div class="chat-msg ai" id="${loadingId}">
                    <div class="msg-bubble" style="color:var(--text-muted); display:flex; gap:0.5rem; align-items:center;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin" style="animation: spin 1s linear infinite;">
                            <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                        </svg>
                        ResearchAI is querying Ollama...
                    </div>
                </div>
            `;
            globalChatMessages.scrollTop = globalChatMessages.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ paper_id: paperId, question })
                });

                const data = await res.json();
                document.getElementById(loadingId).remove();

                if (!res.ok || !data.success) {
                    const errorMsg = data.error || 'Something went wrong while processing your question.';
                    globalChatMessages.innerHTML += `
                        <div class="chat-msg ai">
                            <div class="msg-bubble" style="border-color:var(--danger); background:rgba(239, 68, 68, 0.05); color:var(--danger);">
                                ${escapeHTML(errorMsg)}
                            </div>
                        </div>
                    `;
                } else {
                    let sourcesHtml = '';
                    if (data.sources && data.sources.length > 0) {
                        const uniquePages = [...new Set(data.sources.map(s => s.page))].sort((a,b)=>a-b);
                        sourcesHtml = `
                            <div class="msg-sources">
                                <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); margin-bottom:0.25rem;">SOURCES</div>
                                <div style="display:flex; flex-wrap:wrap; gap:0.375rem;">
                                    ${uniquePages.map(p => `<span class="source-pill">Page ${p}</span>`).join('')}
                                </div>
                            </div>
                        `;
                    }

                    globalChatMessages.innerHTML += `
                        <div class="chat-msg ai">
                            <div class="msg-bubble">
                                ${formatAnswer(data.answer)}
                                ${sourcesHtml}
                            </div>
                        </div>
                    `;
                }
            } catch (err) {
                document.getElementById(loadingId).remove();
                globalChatMessages.innerHTML += `
                    <div class="chat-msg ai">
                        <div class="msg-bubble" style="border-color:var(--danger); background:rgba(239, 68, 68, 0.05); color:var(--danger);">
                            Network error. Please verify the backend is running.
                        </div>
                    </div>
                `;
            }

            isGenerating = false;
            globalChatInput.disabled = false;
            globalSendBtn.disabled = false;
            globalPaperSelect.disabled = false;
            globalChatInput.focus();
            globalChatMessages.scrollTop = globalChatMessages.scrollHeight;
        });
    }
});

// Utils
function handleFileSelect(input) {
    if (input.files && input.files[0]) {
        const dropZoneContent = document.getElementById('dropZoneContent');
        if (dropZoneContent) {
            dropZoneContent.innerHTML = `
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin: 0 auto 1rem auto; display:block;">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <h3 style="margin-bottom: 0.5rem;">${escapeHTML(input.files[0].name)}</h3>
                <p class="text-muted text-sm" style="margin-bottom:1.5rem;">Ready for analysis</p>
                <button type="button" class="btn" style="width:100%; max-width:200px;" onclick="event.stopPropagation(); document.getElementById('uploadForm').submit();">Analyze Paper</button>
            `;
        }
    }
}

function askSuggested(question) {
    const chatInput = document.getElementById('chatInput');
    const chatForm = document.getElementById('chatForm');
    if (chatInput && chatForm) {
        chatInput.value = question;
        chatForm.dispatchEvent(new Event('submit'));
    }
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag])
    );
}

function formatAnswer(text) {
    // Basic markdown-like formatting for bold and paragraphs
    if (!text) return '';
    let formatted = escapeHTML(text);
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\n\n/g, '<br><br>');
    return formatted;
}
