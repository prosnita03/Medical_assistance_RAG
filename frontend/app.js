/**
 * MedAssist AI — Frontend Application Logic
 * Handles: Chat Q&A, Report Summarization, Document Ingestion
 */

// ── API Base URL (auto-detects environment) ──────────────────
const API_BASE = window.location.origin;

// ── State ────────────────────────────────────────────────────
let sessionId = crypto.randomUUID();
let isLoading = false;
let summarizeFile = null;
let ingestFile = null;

// ── DOM refs ─────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const chatMessages       = $('chatMessages');
const welcomeScreen      = $('welcomeScreen');
const chatInput          = $('chatInput');
const sendBtn            = $('sendBtn');
const clearChatBtn       = $('clearChatBtn');

const summarizeTextInput = $('summarizeTextInput');
const summarizeBtn       = $('summarizeBtn');
const summaryResult      = $('summaryResult');
const summaryText        = $('summaryText');
const findingsList       = $('findingsList');
const recommendationsList= $('recommendationsList');
const findingsSection    = $('findingsSection');
const recommendationsSection = $('recommendationsSection');
const copySummaryBtn     = $('copySummaryBtn');

const uploadZoneSummarize = $('uploadZoneSummarize');
const summarizeFileInput  = $('summarizeFileInput');
const summarizeFileName   = $('summarizeFileName');
const uploadLinkSummarize = $('uploadLinkSummarize');

const uploadZoneIngest   = $('uploadZoneIngest');
const ingestFileInput    = $('ingestFileInput');
const ingestFileName     = $('ingestFileName');
const uploadLinkIngest   = $('uploadLinkIngest');
const ingestFileBtn      = $('ingestFileBtn');
const refreshKbBtn       = $('refreshKbBtn');
const ingestResult       = $('ingestResult');
const ingestChunks       = $('ingestChunks');
const ingestTotal        = $('ingestTotal');
const urlIngestInput     = $('urlIngestInput');
const urlIngestBtn       = $('urlIngestBtn');

const loadingOverlay     = $('loadingOverlay');
const spinnerText        = $('spinnerText');
const toastContainer     = $('toastContainer');

const sidebar            = $('sidebar');
const sidebarToggle      = $('sidebarToggle');
const mobileMenuBtn      = $('mobileMenuBtn');

const statusDot          = $('statusDot');
const mobileStatusDot    = $('mobileStatusDot');
const statusText         = $('statusText');
const chunkCount         = $('chunkCount');
const modelName          = $('modelName');

// ══════════════════════════════════════════════════════
// HEALTH CHECK
// ══════════════════════════════════════════════════════
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error('Server error');
    const data = await res.json();

    statusDot.className = 'status-dot online';
    mobileStatusDot.className = 'mobile-status-dot online';
    statusText.textContent = 'Online';
    chunkCount.textContent = data.collection_size.toLocaleString();
    modelName.textContent = data.model.replace('gemini-', 'Gemini ');
  } catch (e) {
    statusDot.className = 'status-dot error';
    mobileStatusDot.className = 'mobile-status-dot';
    statusText.textContent = 'Offline';
    chunkCount.textContent = '—';
    modelName.textContent = '—';
  }
}

// ══════════════════════════════════════════════════════
// PANEL NAVIGATION
// ══════════════════════════════════════════════════════
function switchPanel(panelId) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  $(`panel${panelId.charAt(0).toUpperCase() + panelId.slice(1)}`).classList.add('active');
  $(`nav${panelId.charAt(0).toUpperCase() + panelId.slice(1)}`).classList.add('active');

  // Close sidebar on mobile
  if (window.innerWidth <= 768) closeSidebar();
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchPanel(btn.dataset.panel));
});

// ══════════════════════════════════════════════════════
// SIDEBAR (mobile)
// ══════════════════════════════════════════════════════
let sidebarOverlay;

function openSidebar() {
  sidebar.classList.add('open');
  if (!sidebarOverlay) {
    sidebarOverlay = document.createElement('div');
    sidebarOverlay.className = 'sidebar-overlay';
    sidebarOverlay.addEventListener('click', closeSidebar);
    document.body.appendChild(sidebarOverlay);
  }
  sidebarOverlay.classList.add('visible');
}

function closeSidebar() {
  sidebar.classList.remove('open');
  if (sidebarOverlay) sidebarOverlay.classList.remove('visible');
}

mobileMenuBtn.addEventListener('click', openSidebar);
sidebarToggle.addEventListener('click', closeSidebar);

// ══════════════════════════════════════════════════════
// CHAT
// ══════════════════════════════════════════════════════

// Auto-resize textarea
chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + 'px';
  sendBtn.disabled = chatInput.value.trim().length < 3 || isLoading;
});

chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendBtn.disabled) sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);
clearChatBtn.addEventListener('click', clearChat);

// Example questions
document.querySelectorAll('.example-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    chatInput.value = btn.dataset.question;
    chatInput.dispatchEvent(new Event('input'));
    chatInput.focus();
  });
});

function hideWelcomeScreen() {
  if (welcomeScreen) {
    welcomeScreen.style.opacity = '0';
    welcomeScreen.style.transition = 'opacity 0.3s ease';
    setTimeout(() => welcomeScreen.remove(), 300);
  }
}

function addMessage(role, content, sources = []) {
  const msg = document.createElement('div');
  msg.className = `message ${role}`;

  const aiSVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
    <path d="M12 8v4M8 12h8M12 16a6 6 0 1 0 0-12 6 6 0 0 0 0 12z" opacity="0"/>
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 8v4M8 12h8"/>
  </svg>`;

  const userInitials = 'You';

  msg.innerHTML = `
    <div class="avatar ${role === 'user' ? 'user-avatar' : 'ai-avatar'}">
      ${role === 'user' ? userInitials : aiSVG}
    </div>
    <div class="message-content">
      <div class="message-bubble">${formatMessage(content)}</div>
      ${sources.length > 0 ? renderSources(sources) : ''}
    </div>
  `;

  chatMessages.appendChild(msg);
  scrollToBottom();
  return msg;
}

function formatMessage(text) {
  // Simple markdown-like formatting
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/^#{1,3}\s+(.+)$/gm, '<strong>$1</strong>')
    .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)+/gs, '<ul>$&</ul>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n(?!<)/g, '<br/>');
}

function renderSources(sources) {
  if (!sources || sources.length === 0) return '';
  const chips = sources.map(s => `
    <div class="source-chip">
      <span class="source-chip-name">📄 ${s.source}</span>
      <span>${s.content.substring(0, 120)}…</span>
      ${s.score !== null ? `<span class="source-chip-score">${(s.score * 100).toFixed(0)}%</span>` : ''}
    </div>
  `).join('');
  return `
    <div class="message-sources">
      <div class="sources-label">Sources</div>
      ${chips}
    </div>
  `;
}

function addTypingIndicator() {
  const msg = document.createElement('div');
  msg.className = 'message ai';
  msg.id = 'typingIndicator';
  msg.innerHTML = `
    <div class="avatar ai-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8v4M8 12h8"/>
      </svg>
    </div>
    <div class="message-content">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  chatMessages.appendChild(msg);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = $('typingIndicator');
  if (el) el.remove();
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendMessage() {
  const question = chatInput.value.trim();
  if (!question || isLoading) return;

  hideWelcomeScreen();
  isLoading = true;
  sendBtn.disabled = true;
  chatInput.value = '';
  chatInput.style.height = 'auto';

  addMessage('user', question);
  addTypingIndicator();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, session_id: sessionId }),
    });

    removeTypingIndicator();

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }

    const data = await res.json();
    addMessage('ai', data.answer, data.sources || []);
    checkHealth(); // refresh count after chat
  } catch (e) {
    removeTypingIndicator();
    addMessage('ai', `⚠️ **Error:** ${e.message}\n\nPlease check that the server is running and your API key is configured.`);
    showToast(e.message, 'error');
  } finally {
    isLoading = false;
    sendBtn.disabled = chatInput.value.trim().length < 3;
  }
}

function clearChat() {
  chatMessages.innerHTML = '';
  sessionId = crypto.randomUUID();
  // Re-add welcome screen
  const welcome = document.createElement('div');
  welcome.className = 'welcome-screen';
  welcome.id = 'welcomeScreen';
  welcome.innerHTML = `
    <div class="welcome-logo">
      <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" width="80" height="80">
        <circle cx="40" cy="40" r="40" fill="url(#wGrad2)"/>
        <path d="M40 20v40M20 40h40" stroke="white" stroke-width="6" stroke-linecap="round"/>
        <defs>
          <linearGradient id="wGrad2" x1="0" y1="0" x2="80" y2="80">
            <stop stop-color="#6366f1"/>
            <stop offset="1" stop-color="#06b6d4"/>
          </linearGradient>
        </defs>
      </svg>
    </div>
    <h2 class="welcome-title">How can I help you today?</h2>
    <p class="welcome-subtitle">I have access to medical knowledge covering symptoms, diseases, drug interactions, lab values, and clinical guidelines.</p>
    <div class="example-questions">
      <button class="example-btn" data-question="What are the symptoms of Type 2 diabetes?">What are symptoms of Type 2 diabetes?</button>
      <button class="example-btn" data-question="Can I take ibuprofen with warfarin?">Can I take ibuprofen with warfarin?</button>
      <button class="example-btn" data-question="What are normal blood pressure ranges?">What are normal blood pressure ranges?</button>
      <button class="example-btn" data-question="What is the treatment for hypertension?">What is the treatment for hypertension?</button>
      <button class="example-btn" data-question="What causes shortness of breath?">What causes shortness of breath?</button>
      <button class="example-btn" data-question="What are the signs of a stroke?">What are the signs of a stroke?</button>
    </div>
  `;
  chatMessages.appendChild(welcome);

  // Re-attach example btn listeners
  welcome.querySelectorAll('.example-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      chatInput.value = btn.dataset.question;
      chatInput.dispatchEvent(new Event('input'));
      chatInput.focus();
    });
  });
}

// ══════════════════════════════════════════════════════
// SUMMARIZE
// ══════════════════════════════════════════════════════

function setupDropzone(zone, fileInput, fileNameEl, onFile) {
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
  });
  zone.addEventListener('click', (e) => {
    if (e.target.classList.contains('upload-link')) return;
    fileInput.click();
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) onFile(fileInput.files[0]);
  });
}

function setFileDisplay(fileNameEl, file) {
  fileNameEl.textContent = `📎 ${file.name}`;
  fileNameEl.hidden = false;
}

setupDropzone(uploadZoneSummarize, summarizeFileInput, summarizeFileName, (file) => {
  summarizeFile = file;
  setFileDisplay(summarizeFileName, file);
  showToast(`File selected: ${file.name}`, 'info');
});

uploadLinkSummarize.addEventListener('click', () => summarizeFileInput.click());

summarizeBtn.addEventListener('click', async () => {
  if (isLoading) return;

  const text = summarizeTextInput.value.trim();
  const hasFile = !!summarizeFile;
  const hasText = text.length >= 50;

  if (!hasFile && !hasText) {
    showToast('Please upload a file or paste at least 50 characters of text.', 'warning');
    return;
  }

  isLoading = true;
  summarizeBtn.disabled = true;
  showLoading('Generating medical summary…');

  try {
    let res;

    if (hasFile) {
      const formData = new FormData();
      formData.append('file', summarizeFile);
      res = await fetch(`${API_BASE}/api/summarize/file`, { method: 'POST', body: formData });
    } else {
      res = await fetch(`${API_BASE}/api/summarize/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }

    const data = await res.json();
    renderSummaryResult(data);
    showToast('Summary generated successfully!', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    isLoading = false;
    summarizeBtn.disabled = false;
    hideLoading();
  }
});

function renderSummaryResult(data) {
  summaryText.textContent = data.summary;

  findingsList.innerHTML = '';
  if (data.key_findings && data.key_findings.length) {
    data.key_findings.forEach(f => {
      const li = document.createElement('li');
      li.textContent = f;
      findingsList.appendChild(li);
    });
    findingsSection.style.display = 'block';
  } else {
    findingsSection.style.display = 'none';
  }

  recommendationsList.innerHTML = '';
  if (data.recommendations && data.recommendations.length) {
    data.recommendations.forEach(r => {
      const li = document.createElement('li');
      li.textContent = r;
      recommendationsList.appendChild(li);
    });
    recommendationsSection.style.display = 'block';
  } else {
    recommendationsSection.style.display = 'none';
  }

  summaryResult.hidden = false;
  summaryResult.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

copySummaryBtn.addEventListener('click', () => {
  const text = `SUMMARY:\n${summaryText.textContent}\n\nKEY FINDINGS:\n${
    Array.from(findingsList.children).map(li => '• ' + li.textContent).join('\n')
  }\n\nRECOMMENDATIONS:\n${
    Array.from(recommendationsList.children).map(li => '• ' + li.textContent).join('\n')
  }`;
  navigator.clipboard.writeText(text).then(() => showToast('Summary copied!', 'success'));
});

// ══════════════════════════════════════════════════════
// INGEST
// ══════════════════════════════════════════════════════

setupDropzone(uploadZoneIngest, ingestFileInput, ingestFileName, (file) => {
  ingestFile = file;
  setFileDisplay(ingestFileName, file);
  ingestFileBtn.disabled = false;
  showToast(`File selected: ${file.name}`, 'info');
});

uploadLinkIngest.addEventListener('click', () => ingestFileInput.click());

ingestFileBtn.addEventListener('click', async () => {
  if (!ingestFile || isLoading) return;
  await doIngest(async () => {
    const formData = new FormData();
    formData.append('file', ingestFile);
    return fetch(`${API_BASE}/api/ingest/file`, { method: 'POST', body: formData });
  }, `Ingesting ${ingestFile.name}…`);
});

refreshKbBtn.addEventListener('click', async () => {
  if (isLoading) return;
  if (!confirm('This will clear the existing knowledge base and re-ingest all documents from the server ./data directory. Continue?')) return;
  await doIngest(async () => {
    return fetch(`${API_BASE}/api/ingest/refresh`, { method: 'POST' });
  }, 'Refreshing knowledge base…');
});

urlIngestInput.addEventListener('input', () => {
  const urlVal = urlIngestInput.value.trim();
  urlIngestBtn.disabled = !urlVal.startsWith('http://') && !urlVal.startsWith('https://');
});

urlIngestBtn.addEventListener('click', async () => {
  const url = urlIngestInput.value.trim();
  if (!url || isLoading) return;
  
  await doIngest(async () => {
    return fetch(`${API_BASE}/api/ingest/url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
  }, `Ingesting website: ${url}…`);
  
  urlIngestInput.value = '';
  urlIngestBtn.disabled = true;
});

async function doIngest(fetchFn, loadingMsg) {
  isLoading = true;
  showLoading(loadingMsg);
  ingestResult.hidden = true;

  try {
    const res = await fetchFn();
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }
    const data = await res.json();

    ingestChunks.textContent = `✅ ${data.chunks_added} chunks added`;
    ingestTotal.textContent = `📚 Knowledge base now has ${data.collection_size.toLocaleString()} chunks`;
    ingestResult.hidden = false;

    showToast(data.message, 'success');
    checkHealth();
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    isLoading = false;
    hideLoading();
  }
}

// ══════════════════════════════════════════════════════
// UI HELPERS
// ══════════════════════════════════════════════════════

function showLoading(text = 'Processing…') {
  spinnerText.textContent = text;
  loadingOverlay.hidden = false;
}

function hideLoading() {
  loadingOverlay.hidden = true;
}

function showToast(message, type = 'info', duration = 4000) {
  const icons = {
    success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`,
    error:   `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    warning: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info:    `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    ${icons[type] || icons.info}
    <span>${message}</span>
    <button class="toast-dismiss" aria-label="Dismiss">✕</button>
  `;

  toast.querySelector('.toast-dismiss').addEventListener('click', () => removeToast(toast));
  toastContainer.appendChild(toast);

  setTimeout(() => removeToast(toast), duration);
  return toast;
}

function removeToast(toast) {
  toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
  toast.style.opacity = '0';
  toast.style.transform = 'translateX(100%)';
  setTimeout(() => toast.remove(), 300);
}

// ══════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════
(async function init() {
  await checkHealth();
  // Poll health every 30 seconds
  setInterval(checkHealth, 30000);
  // Focus chat input
  chatInput.focus();
})();
