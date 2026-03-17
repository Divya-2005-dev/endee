// Global variables
let uploadedFiles = [];
let chatSessions = {};
let currentSessionId = null;
let currentTheme = localStorage.getItem('theme') || 'dark';
let isStreaming = false;

// DOM elements
const fileInput = document.getElementById('pdf-file');
const fileList = document.getElementById('file-list');
const uploadBtn = document.getElementById('upload-btn');
const uploadStatus = document.getElementById('upload-status');
const uploadProgress = document.getElementById('upload-progress');
const progressFill = document.querySelector('.progress-fill');
const progressText = document.querySelector('.progress-text');
const questionInput = document.getElementById('question');
const chatHistory = document.getElementById('chat-history');
const sessionSelect = document.getElementById('session-select');
const typingIndicator = document.getElementById('typing-indicator');
const documentsList = document.getElementById('documents-list');
const docSearch = document.getElementById('doc-search');
const docFilter = document.getElementById('doc-filter');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    setupTheme();
    setupDragAndDrop();
    setupKeyboardShortcuts();
    loadDocuments();
    loadSessions();
    loadAnalytics();
    showTab('upload'); // Default tab
}

// Theme management
function setupTheme() {
    document.documentElement.setAttribute('data-theme', currentTheme);
    const themeBtn = document.getElementById('theme-toggle');
    themeBtn.textContent = currentTheme === 'dark' ? '🌙' : '☀️';
}

function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    localStorage.setItem('theme', currentTheme);
    const themeBtn = document.getElementById('theme-toggle');
    themeBtn.textContent = currentTheme === 'dark' ? '🌙' : '☀️';
}

// Tab management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName + '-section').classList.add('active');
    event.target.classList.add('active');

    // Load tab-specific data
    if (tabName === 'chat') {
        loadChatHistory();
    } else if (tabName === 'documents') {
        loadDocuments();
    } else if (tabName === 'analytics') {
        loadAnalytics();
    }
}

// Drag and drop functionality
function setupDragAndDrop() {
    const uploadArea = document.querySelector('.upload-area');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('drag-over');
        }, false);
    });

    uploadArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
}

// File handling
fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

function handleFiles(files) {
    [...files].forEach(file => {
        if (isValidFile(file)) {
            uploadedFiles.push(file);
        } else {
            showStatus(`File ${file.name} is not supported or too large (max 50MB)`, 'error');
        }
    });
    updateFileList();
}

function isValidFile(file) {
    const allowedTypes = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/markdown', 'text/html'];
    const maxSize = 50 * 1024 * 1024; // 50MB

    return allowedTypes.includes(file.type) && file.size <= maxSize;
}

function updateFileList() {
    fileList.innerHTML = '';
    uploadedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div>
                <span class="file-name">${file.name}</span>
                <span class="file-size">${formatFileSize(file.size)}</span>
                <span class="file-type">${getFileType(file.type)}</span>
            </div>
            <button onclick="removeFile(${index})">❌</button>
        `;
        fileList.appendChild(fileItem);
    });
    uploadBtn.disabled = uploadedFiles.length === 0;
}

function getFileType(mimeType) {
    const types = {
        'application/pdf': 'PDF',
        'text/plain': 'TXT',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
        'text/markdown': 'MD',
        'text/html': 'HTML'
    };
    return types[mimeType] || 'FILE';
}

function removeFile(index) {
    uploadedFiles.splice(index, 1);
    updateFileList();
}

function clearFileList() {
    uploadedFiles = [];
    updateFileList();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Upload files
async function uploadFiles() {
    if (uploadedFiles.length === 0) return;

    uploadBtn.disabled = true;
    uploadBtn.textContent = '🚀 Uploading...';
    uploadProgress.style.display = 'block';
    showStatus('Uploading files...', 'loading');

    try {
        let uploadedCount = 0;
        const totalFiles = uploadedFiles.length;

        for (const file of uploadedFiles) {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Upload failed');
            }

            uploadedCount++;
            updateProgress(uploadedCount / totalFiles * 100);
        }

        showStatus(`Successfully uploaded ${uploadedFiles.length} file(s)!`, 'success');
        uploadedFiles = [];
        updateFileList();
        loadDocuments();
        updateProgress(0);
        uploadProgress.style.display = 'none';

    } catch (error) {
        showStatus(`Upload failed: ${error.message}`, 'error');
        uploadProgress.style.display = 'none';
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = '🚀 Upload Documents';
    }
}

function updateProgress(percentage) {
    progressFill.style.width = percentage + '%';
    progressText.textContent = Math.round(percentage) + '%';
}

// Chat functionality
async function askQuestion() {
    const question = questionInput.value.trim();
    if (!question) {
        showStatus('Please enter a question', 'error');
        return;
    }

    const sessionId = currentSessionId || generateSessionId();
    addMessageToChat('user', question, sessionId);
    questionInput.value = '';

    typingIndicator.style.display = 'flex';

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                session_id: sessionId
            })
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Query failed');
        }

        addMessageToChat('assistant', result.answer, sessionId, result.sources, result.confidence);
        currentSessionId = result.session_id;
        updateSessionSelect();

    } catch (error) {
        addMessageToChat('assistant', `Error: ${error.message}`, sessionId);
    } finally {
        typingIndicator.style.display = 'none';
    }
}

async function askStreaming() {
    if (isStreaming) return;

    const question = questionInput.value.trim();
    if (!question) {
        showStatus('Please enter a question', 'error');
        return;
    }

    const sessionId = currentSessionId || generateSessionId();
    addMessageToChat('user', question, sessionId);
    questionInput.value = '';

    isStreaming = true;
    let streamedContent = '';

    try {
        const response = await fetch('/ask/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                session_id: sessionId
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;

                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.chunk) {
                            streamedContent += parsed.chunk;
                            updateStreamingMessage(sessionId, streamedContent);
                        } else if (parsed.done) {
                            isStreaming = false;
                            currentSessionId = sessionId;
                            updateSessionSelect();
                        } else if (parsed.error) {
                            throw new Error(parsed.error);
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }

    } catch (error) {
        updateStreamingMessage(sessionId, `Error: ${error.message}`);
        isStreaming = false;
    }
}

function addMessageToChat(role, content, sessionId, sources = null, confidence = null) {
    if (!chatSessions[sessionId]) {
        chatSessions[sessionId] = { messages: [], created: new Date().toISOString() };
    }

    const message = {
        role: role,
        content: content,
        timestamp: new Date().toISOString(),
        sources: sources,
        confidence: confidence
    };

    chatSessions[sessionId].messages.push(message);
    saveSessions();
    renderChatMessage(message);
}

function updateStreamingMessage(sessionId, content) {
    // Update the last assistant message
    const messages = chatSessions[sessionId]?.messages || [];
    const lastMessage = messages[messages.length - 1];

    if (lastMessage && lastMessage.role === 'assistant') {
        lastMessage.content = content;
        // Re-render the last message
        const messageElements = chatHistory.querySelectorAll('.chat-message');
        const lastElement = messageElements[messageElements.length - 1];
        if (lastElement) {
            lastElement.querySelector('.message-content').textContent = content;
        }
    } else {
        addMessageToChat('assistant', content, sessionId);
    }
}

function renderChatMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${message.role}`;

    let sourcesHtml = '';
    if (message.sources && message.sources.length > 0) {
        sourcesHtml = `
            <div class="sources">
                <h4>📚 Sources</h4>
                ${message.sources.map(source => `
                    <div class="source-item">
                        <span>${source.source}</span>
                        <span>Page ${source.page} ${source.confidence ? `(${ (source.confidence * 100).toFixed(1)}%)` : ''}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-header">
            <span>${message.role === 'user' ? '👤 You' : '🤖 Assistant'}</span>
            <span>${message.confidence ? `(Confidence: ${(message.confidence * 100).toFixed(1)}%)` : ''}</span>
        </div>
        <div class="message-content">${message.content}</div>
        ${sourcesHtml}
    `;

    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function createNewSession() {
    currentSessionId = generateSessionId();
    chatHistory.innerHTML = '';
    updateSessionSelect();
}

function clearChat() {
    if (currentSessionId && chatSessions[currentSessionId]) {
        chatSessions[currentSessionId].messages = [];
        chatHistory.innerHTML = '';
        saveSessions();
    }
}

function updateSessionSelect() {
    sessionSelect.innerHTML = '<option value="">New Session</option>';

    Object.keys(chatSessions).forEach(sessionId => {
        const session = chatSessions[sessionId];
        const option = document.createElement('option');
        option.value = sessionId;
        option.textContent = `Session ${sessionId.split('_')[1]} (${session.messages.length} messages)`;
        if (sessionId === currentSessionId) {
            option.selected = true;
        }
        sessionSelect.appendChild(option);
    });
}

sessionSelect.addEventListener('change', (e) => {
    currentSessionId = e.target.value;
    loadChatHistory();
});

function loadChatHistory() {
    chatHistory.innerHTML = '';
    if (currentSessionId && chatSessions[currentSessionId]) {
        chatSessions[currentSessionId].messages.forEach(message => {
            renderChatMessage(message);
        });
    }
}

function saveSessions() {
    localStorage.setItem('chatSessions', JSON.stringify(chatSessions));
}

function loadSessions() {
    const saved = localStorage.getItem('chatSessions');
    if (saved) {
        chatSessions = JSON.parse(saved);
        updateSessionSelect();
    }
}

// Documents management
async function loadDocuments() {
    try {
        const response = await fetch('/documents');
        const data = await response.json();

        documentsList.innerHTML = '';

        if (data.documents && data.documents.length > 0) {
            data.documents.forEach(doc => {
                const docCard = createDocumentCard(doc);
                documentsList.appendChild(docCard);
            });
        } else {
            documentsList.innerHTML = '<p>No documents uploaded yet.</p>';
        }
    } catch (error) {
        console.error('Error loading documents:', error);
        documentsList.innerHTML = '<p>Error loading documents.</p>';
    }
}

function createDocumentCard(doc) {
    const card = document.createElement('div');
    card.className = 'document-card';
    card.onclick = () => showDocumentModal(doc);

    card.innerHTML = `
        <h3>${doc.filename}</h3>
        <div class="doc-meta">
            ${doc.metadata?.author ? `Author: ${doc.metadata.author}<br>` : ''}
            ${doc.metadata?.word_count ? `Words: ${doc.metadata.word_count.toLocaleString()}<br>` : ''}
            Uploaded: ${new Date(doc.uploaded_at).toLocaleDateString()}
        </div>
        <div class="doc-stats">
            <span>${doc.chunks} chunks</span>
            <span>${formatFileSize(doc.size)}</span>
        </div>
        <div class="doc-actions">
            <button onclick="event.stopPropagation(); downloadDocument('${doc.id}')">📥 Download</button>
            <button onclick="event.stopPropagation(); deleteDocument('${doc.id}')">🗑️ Delete</button>
        </div>
    `;

    return card;
}

function showDocumentModal(doc) {
    const modal = document.getElementById('document-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');

    modalTitle.textContent = doc.filename;
    modalBody.innerHTML = `
        <div class="document-details">
            <p><strong>File ID:</strong> ${doc.id}</p>
            <p><strong>Size:</strong> ${formatFileSize(doc.size)}</p>
            <p><strong>Chunks:</strong> ${doc.chunks}</p>
            <p><strong>Uploaded:</strong> ${new Date(doc.uploaded_at).toLocaleDateString()}</p>
            ${doc.metadata ? `
                <h4>Metadata</h4>
                <ul>
                    ${doc.metadata.word_count ? `<li>Word Count: ${doc.metadata.word_count.toLocaleString()}</li>` : ''}
                    ${doc.metadata.page_count ? `<li>Page Count: ${doc.metadata.page_count}</li>` : ''}
                    ${doc.metadata.author ? `<li>Author: ${doc.metadata.author}</li>` : ''}
                    ${doc.metadata.title ? `<li>Title: ${doc.metadata.title}</li>` : ''}
                </ul>
            ` : ''}
        </div>
    `;

    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('document-modal').style.display = 'none';
}

async function deleteDocument(docId) {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
        const response = await fetch(`/documents/${docId}`, { method: 'DELETE' });
        const result = await response.json();

        if (response.ok) {
            showStatus(result.message || 'Document deleted', 'success');
            loadDocuments();
            loadAnalytics();
        } else {
            showStatus(result.error || 'Delete failed', 'error');
        }
    } catch (error) {
        showStatus('Delete failed', 'error');
    }
}

function downloadDocument(docId) {
    // This would need a download endpoint in the backend
    window.open(`/download/${docId}`, '_blank');
}

function filterDocuments() {
    const searchTerm = docSearch.value.toLowerCase();
    const filterType = docFilter.value;
    const cards = documentsList.querySelectorAll('.document-card');

    cards.forEach(card => {
        const title = card.querySelector('h3').textContent.toLowerCase();
        const type = card.querySelector('.doc-stats span:last-child').textContent;

        const matchesSearch = title.includes(searchTerm);
        const matchesFilter = !filterType || type.includes(filterType);

        card.style.display = matchesSearch && matchesFilter ? 'block' : 'none';
    });
}

// Analytics
async function loadAnalytics() {
    try {
        const response = await fetch('/analytics');
        const data = await response.json();

        document.getElementById('docs-count').textContent = data.total_documents || 0;
        document.getElementById('sessions-count').textContent = data.total_sessions || 0;
        document.getElementById('queries-count').textContent = data.total_queries || 0;
        document.getElementById('avg-session').textContent = data.average_session_length?.toFixed(1) || 0;

        // Update chart if Chart.js is available
        updateChart(data);

    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function updateChart(data) {
    const ctx = document.getElementById('usage-chart');
    if (!ctx) return;

    // Simple chart implementation
    // In a real app, you'd use Chart.js or similar
    ctx.innerHTML = '<p>Chart visualization would go here</p>';
}

// Settings
function exportCurrentChat() {
    if (!currentSessionId || !chatSessions[currentSessionId]) {
        showStatus('No active chat session to export', 'error');
        return;
    }

    const session = chatSessions[currentSessionId];
    const exportData = {
        sessionId: currentSessionId,
        exportedAt: new Date().toISOString(),
        messages: session.messages
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat_export_${currentSessionId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function exportAllChats() {
    try {
        const response = await fetch('/export/chat/all', { method: 'GET' });
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'all_chats_export.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    } catch (error) {
        showStatus('Export failed', 'error');
    }
}

function clearAllData() {
    if (!confirm('Are you sure you want to clear ALL data? This cannot be undone!')) return;

    localStorage.clear();
    chatSessions = {};
    currentSessionId = null;
    chatHistory.innerHTML = '';
    updateSessionSelect();
    showStatus('All data cleared', 'success');
}

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey && questionInput === document.activeElement) {
            askQuestion();
        }
        if (e.key === 'Enter' && e.shiftKey && questionInput === document.activeElement) {
            askStreaming();
        }
    });
}

// Status messages
function showStatus(message, type) {
    uploadStatus.className = `status-${type}`;
    uploadStatus.textContent = message;

    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            uploadStatus.textContent = '';
        }, 5000);
    }
}

// Click outside modal to close
document.getElementById('document-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        closeModal();
    }
});