/**
 * RAG System — Frontend Logic
 * Handles file uploads, querying, and UI interactions.
 */

// ===== DOM Elements =====
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadResults = document.getElementById('uploadResults');
const documentList = document.getElementById('documentList');
const docListItems = document.getElementById('docListItems');
const queryInput = document.getElementById('queryInput');
const querySubmit = document.getElementById('querySubmit');
const answerContainer = document.getElementById('answerContainer');
const answerText = document.getElementById('answerText');
const sourcesSection = document.getElementById('sourcesSection');
const sourcesList = document.getElementById('sourcesList');
const loadingContainer = document.getElementById('loadingContainer');
const historySection = document.getElementById('historySection');
const historyList = document.getElementById('historyList');
const clearAllBtn = document.getElementById('clearAllBtn');
const docCount = document.getElementById('docCount');
const chunkCount = document.getElementById('chunkCount');

// ===== State =====
let conversationHistory = [];

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    loadStats();
    setupEventListeners();
});

// ===== Background Particles =====
function initParticles() {
    const container = document.getElementById('bgParticles');
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        const size = Math.random() * 4 + 1;
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.animationDuration = `${Math.random() * 15 + 10}s`;
        particle.style.animationDelay = `${Math.random() * 10}s`;
        particle.style.opacity = Math.random() * 0.5 + 0.1;
        container.appendChild(particle);
    }
}

// ===== Event Listeners =====
function setupEventListeners() {
    // Drop zone
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
        fileInput.value = '';
    });

    // Query
    querySubmit.addEventListener('click', handleQuery);
    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleQuery();
        }
    });

    // Clear all
    clearAllBtn.addEventListener('click', handleClearAll);
}

// ===== File Upload =====
async function handleFiles(files) {
    if (!files || files.length === 0) return;

    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    uploadResults.hidden = false;
    uploadResults.innerHTML = `
        <div class="upload-result-item" style="border-color: rgba(99, 102, 241, 0.3);">
            <div class="result-icon" style="background: rgba(99, 102, 241, 0.2); color: var(--accent-primary);">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <path d="M12 2v20M2 12h20"/>
                </svg>
            </div>
            <span class="result-filename">Uploading ${files.length} file(s)...</span>
        </div>
    `;

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();
        displayUploadResults(data.results);
        loadStats();
        showToast(`Successfully processed ${files.length} file(s)`, 'success');
    } catch (error) {
        uploadResults.innerHTML = `
            <div class="upload-result-item error">
                <div class="result-icon error">✕</div>
                <span class="result-filename">Upload failed</span>
                <span class="result-message">${error.message}</span>
            </div>
        `;
        showToast('Upload failed: ' + error.message, 'error');
    }
}

function displayUploadResults(results) {
    uploadResults.innerHTML = results.map(r => `
        <div class="upload-result-item ${r.status}">
            <div class="result-icon ${r.status}">
                ${r.status === 'success'
                    ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>'
                    : '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
                }
            </div>
            <span class="result-filename">${escapeHtml(r.filename)}</span>
            <span class="result-message">${escapeHtml(r.message)}</span>
        </div>
    `).join('');
}

// ===== Query =====
async function handleQuery() {
    const question = queryInput.value.trim();
    if (!question) return;

    querySubmit.disabled = true;
    answerContainer.hidden = true;
    loadingContainer.hidden = false;

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Query failed');
        }

        const data = await response.json();
        displayAnswer(data);

        // Add to history
        conversationHistory.unshift({
            question: data.query,
            answer: data.answer,
            sources: data.sources,
        });
        updateHistory();

    } catch (error) {
        answerText.textContent = `Error: ${error.message}`;
        answerContainer.hidden = false;
        sourcesSection.hidden = true;
        showToast('Query failed: ' + error.message, 'error');
    } finally {
        querySubmit.disabled = false;
        loadingContainer.hidden = true;
    }
}

function displayAnswer(data) {
    answerContainer.hidden = false;
    answerText.textContent = data.answer;

    if (data.sources && data.sources.length > 0) {
        sourcesSection.hidden = false;
        sourcesList.innerHTML = data.sources.map(s => `
            <div class="source-tag">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
                ${escapeHtml(s.filename)}
                <span class="source-relevance">${Math.round(s.relevance * 100)}%</span>
            </div>
        `).join('');
    } else {
        sourcesSection.hidden = true;
    }
}

// ===== History =====
function updateHistory() {
    if (conversationHistory.length === 0) {
        historySection.hidden = true;
        return;
    }

    historySection.hidden = false;
    historyList.innerHTML = conversationHistory.map((item, idx) => `
        <div class="history-item" onclick="restoreHistory(${idx})">
            <div class="history-question">${escapeHtml(item.question)}</div>
            <div class="history-answer-preview">${escapeHtml(item.answer)}</div>
        </div>
    `).join('');
}

function restoreHistory(index) {
    const item = conversationHistory[index];
    queryInput.value = item.question;
    displayAnswer(item);
}

// ===== Stats =====
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        const numDocs = data.documents ? data.documents.length : 0;
        docCount.textContent = `${numDocs} document${numDocs !== 1 ? 's' : ''}`;
        chunkCount.textContent = `${data.total_chunks} chunks`;

        if (numDocs > 0) {
            documentList.hidden = false;
            docListItems.innerHTML = data.documents.map(name => `
                <li>
                    <svg class="doc-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                    ${escapeHtml(name)}
                </li>
            `).join('');
        } else {
            documentList.hidden = true;
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// ===== Clear All =====
async function handleClearAll() {
    if (!confirm('Are you sure you want to delete all documents? This cannot be undone.')) return;

    try {
        const response = await fetch('/api/documents', { method: 'DELETE' });
        const data = await response.json();
        loadStats();
        uploadResults.hidden = true;
        uploadResults.innerHTML = '';
        conversationHistory = [];
        updateHistory();
        answerContainer.hidden = true;
        showToast(data.message, 'success');
    } catch (error) {
        showToast('Failed to clear documents: ' + error.message, 'error');
    }
}

// ===== Toast Notifications =====
function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        ${type === 'success'
            ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>'
            : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
        }
        <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ===== Utils =====
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
