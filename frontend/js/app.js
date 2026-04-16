// SimchaLeads Dashboard

const API = '';

// ─── State ────────────────────────────────────────────────
let currentTab = 'dashboard';

// ─── API Helpers ──────────────────────────────────────────
async function api(path, opts = {}) {
    const url = `${API}${path}`;
    const config = { headers: { 'Content-Type': 'application/json' }, ...opts };
    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
        config.body = JSON.stringify(config.body);
    }
    if (config.body instanceof FormData) {
        delete config.headers['Content-Type'];
    }
    const res = await fetch(url, config);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

// ─── Navigation ───────────────────────────────────────────
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === `page-${tab}`));

    const loaders = {
        dashboard: loadDashboard,
        engagements: loadEngagements,
        contacts: loadContacts,
        drafts: loadDrafts,
        settings: loadSettings,
    };
    if (loaders[tab]) loaders[tab]();
}

// ─── Dashboard ────────────────────────────────────────────
async function loadDashboard() {
    try {
        const stats = await api('/api/stats');
        document.getElementById('stat-engagements').textContent = stats.engagements;
        document.getElementById('stat-contacts').textContent = stats.contacts;
        document.getElementById('stat-matches').textContent = stats.matches;
        document.getElementById('stat-drafts').textContent = stats.drafts_pending;
        document.getElementById('stat-approved').textContent = stats.drafts_approved;
        document.getElementById('stat-sent').textContent = stats.sent;
    } catch (e) {
        showAlert('error', 'Failed to load stats: ' + e.message);
    }
}

async function runPipeline() {
    const btn = document.getElementById('btn-pipeline');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running...';
    try {
        const result = await api('/api/pipeline/run', { method: 'POST' });
        showAlert('success',
            `Pipeline complete! Scraped: ${result.scrape.new_saved} new, ` +
            `Matched: ${result.match.total_matches}, ` +
            `Drafts: ${result.drafts.drafts_created}`
        );
        loadDashboard();
    } catch (e) {
        showAlert('error', 'Pipeline failed: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Run Full Pipeline';
    }
}

// ─── Engagements ──────────────────────────────────────────
async function loadEngagements() {
    try {
        const data = await api('/api/engagements');
        const tbody = document.getElementById('engagements-table');
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No engagements yet. Run the scraper or add manually.</td></tr>';
            return;
        }
        tbody.innerHTML = data.map(e => `
            <tr>
                <td><strong>${esc(e.chatan_first)}${e.chatan_last ? ' ' + esc(e.chatan_last) : ''}</strong></td>
                <td><strong>${esc(e.kallah_first)}${e.kallah_last ? ' ' + esc(e.kallah_last) : ''}</strong></td>
                <td>${e.post_date ? new Date(e.post_date).toLocaleDateString() : '-'}</td>
                <td>${e.match_count || 0}</td>
                <td>${e.draft_count || 0}</td>
                <td>
                    ${e.source_url ? `<a href="${esc(e.source_url)}" target="_blank" class="btn btn-outline btn-sm">View</a>` : ''}
                    <button class="btn btn-danger btn-sm" onclick="deleteEngagement(${e.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        showAlert('error', 'Failed to load engagements: ' + e.message);
    }
}

async function addEngagementManual() {
    const fields = ['chatan_first', 'chatan_last', 'kallah_first', 'kallah_last'];
    const data = {};
    for (const f of fields) {
        data[f] = document.getElementById(`add-${f}`).value.trim();
    }
    if (!data.chatan_first || !data.kallah_first) {
        showAlert('warning', 'Chatan and Kallah first names are required.');
        return;
    }
    try {
        await api('/api/engagements/manual', { method: 'POST', body: data });
        showAlert('success', 'Engagement added!');
        for (const f of fields) document.getElementById(`add-${f}`).value = '';
        loadEngagements();
    } catch (e) {
        showAlert('error', 'Failed: ' + e.message);
    }
}

async function deleteEngagement(id) {
    if (!confirm('Delete this engagement and all related matches/drafts?')) return;
    try {
        await api(`/api/engagements/${id}`, { method: 'DELETE' });
        loadEngagements();
    } catch (e) {
        showAlert('error', 'Failed: ' + e.message);
    }
}

// ─── Contacts ─────────────────────────────────────────────
async function loadContacts() {
    const search = document.getElementById('contact-search')?.value || '';
    try {
        const data = await api(`/api/contacts?search=${encodeURIComponent(search)}&limit=100`);
        const tbody = document.getElementById('contacts-table');
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No contacts. Import from Smartlist (CSV or VCF).</td></tr>';
            return;
        }
        tbody.innerHTML = data.map(c => `
            <tr>
                <td><strong>${esc(c.first_name)} ${esc(c.last_name)}</strong></td>
                <td>${esc(c.phone || '-')}</td>
                <td>${esc(c.email || '-')}</td>
                <td>${esc(c.city || c.community || '-')}</td>
                <td>${esc(c.source || '-')}</td>
            </tr>
        `).join('');
    } catch (e) {
        showAlert('error', 'Failed to load contacts: ' + e.message);
    }
}

async function importContacts() {
    const fileInput = document.getElementById('contact-file');
    const community = document.getElementById('import-community')?.value || '';
    if (!fileInput.files.length) {
        showAlert('warning', 'Please select a CSV or VCF file.');
        return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('community', community);
    try {
        const result = await api('/api/contacts/import', { method: 'POST', body: formData });
        showAlert('success', `Imported ${result.imported} contacts from ${result.filename}`);
        fileInput.value = '';
        loadContacts();
    } catch (e) {
        showAlert('error', 'Import failed: ' + e.message);
    }
}

// ─── Drafts ───────────────────────────────────────────────
async function loadDrafts() {
    const statusFilter = document.getElementById('draft-status-filter')?.value || '';
    const channelFilter = document.getElementById('draft-channel-filter')?.value || '';
    try {
        const data = await api(`/api/drafts?status=${statusFilter}&channel=${channelFilter}&limit=100`);
        const container = document.getElementById('drafts-list');
        if (data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="icon">&#9993;</div>
                    <h3>No drafts yet</h3>
                    <p>Run the pipeline to scrape, match, and generate drafts.</p>
                </div>`;
            return;
        }
        container.innerHTML = data.map(d => `
            <div class="draft-card" id="draft-${d.id}">
                <div class="draft-card-header">
                    <h4>${esc(d.recipient_name)}</h4>
                    <span class="badge badge-${d.status}">${d.status}</span>
                </div>
                <div class="draft-meta">
                    <span class="badge badge-${d.channel}">${d.channel.toUpperCase()}</span>
                    <span style="color:var(--gray-500);font-size:12px;">
                        ${esc(d.chatan_first)}${d.chatan_last ? ' ' + esc(d.chatan_last) : ''}
                        &amp;
                        ${esc(d.kallah_first)}${d.kallah_last ? ' ' + esc(d.kallah_last) : ''}
                    </span>
                    <span style="color:var(--gray-500);font-size:12px;">
                        To: ${d.channel === 'email' ? esc(d.recipient_email || '-') : esc(d.recipient_phone || '-')}
                    </span>
                </div>
                <div class="draft-message" id="draft-msg-${d.id}">${esc(d.message)}</div>
                <div class="draft-actions">
                    ${d.status === 'draft' ? `
                        <button class="btn btn-outline btn-sm" onclick="editDraft(${d.id})">Edit</button>
                        <button class="btn btn-primary btn-sm" onclick="approveDraft(${d.id})">Approve</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteDraft(${d.id})">Delete</button>
                    ` : ''}
                    ${d.status === 'approved' ? `
                        <button class="btn btn-outline btn-sm" onclick="editDraft(${d.id})">Edit</button>
                        <button class="btn btn-success btn-sm" onclick="sendDraft(${d.id})">Send</button>
                    ` : ''}
                    ${d.status === 'sent' ? `
                        <span style="color:var(--success);font-size:12px;">Sent ${d.sent_at ? new Date(d.sent_at).toLocaleString() : ''}</span>
                    ` : ''}
                    ${d.status === 'failed' ? `
                        <button class="btn btn-warning btn-sm" onclick="sendDraft(${d.id})">Retry</button>
                    ` : ''}
                </div>
            </div>
        `).join('');
    } catch (e) {
        showAlert('error', 'Failed to load drafts: ' + e.message);
    }
}

async function approveDraft(id) {
    try {
        await api(`/api/drafts/${id}`, { method: 'PUT', body: { status: 'approved' } });
        loadDrafts();
    } catch (e) {
        showAlert('error', e.message);
    }
}

async function approveAllDrafts() {
    const drafts = await api('/api/drafts?status=draft&limit=500');
    for (const d of drafts) {
        await api(`/api/drafts/${d.id}`, { method: 'PUT', body: { status: 'approved' } });
    }
    showAlert('success', `Approved ${drafts.length} drafts`);
    loadDrafts();
}

async function sendDraft(id) {
    try {
        await api(`/api/send/${id}`, { method: 'POST' });
        showAlert('success', 'Message sent!');
        loadDrafts();
    } catch (e) {
        showAlert('error', 'Send failed: ' + e.message);
    }
}

async function sendAllApproved() {
    if (!confirm('Send ALL approved drafts?')) return;
    const drafts = await api('/api/drafts?status=approved&limit=500');
    const ids = drafts.map(d => d.id);
    try {
        const result = await api('/api/send/bulk', { method: 'POST', body: { draft_ids: ids } });
        const sent = result.results.filter(r => r.success).length;
        const failed = result.results.filter(r => !r.success).length;
        showAlert('success', `Sent: ${sent}, Failed: ${failed}`);
        loadDrafts();
    } catch (e) {
        showAlert('error', e.message);
    }
}

async function deleteDraft(id) {
    try {
        await api(`/api/drafts/${id}`, { method: 'DELETE' });
        loadDrafts();
    } catch (e) {
        showAlert('error', e.message);
    }
}

function editDraft(id) {
    const msgEl = document.getElementById(`draft-msg-${id}`);
    const currentMsg = msgEl.textContent;
    const modal = document.getElementById('edit-modal');
    document.getElementById('edit-draft-id').value = id;
    document.getElementById('edit-draft-message').value = currentMsg;
    modal.classList.add('show');
}

async function saveEditDraft() {
    const id = document.getElementById('edit-draft-id').value;
    const message = document.getElementById('edit-draft-message').value;
    try {
        await api(`/api/drafts/${id}`, { method: 'PUT', body: { message } });
        closeModal();
        loadDrafts();
    } catch (e) {
        showAlert('error', e.message);
    }
}

function closeModal() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('show'));
}

// ─── Settings ─────────────────────────────────────────────
async function loadSettings() {
    try {
        const settings = await api('/api/settings');
        const container = document.getElementById('settings-form');
        const settingGroups = {
            'Business': ['business_name', 'discount_percent'],
            'Instagram API': ['instagram_account', 'ig_access_token', 'ig_user_id'],
            'Twilio (SMS/WhatsApp)': ['twilio_account_sid', 'twilio_auth_token', 'twilio_from_number', 'twilio_whatsapp_from'],
            'Email (SMTP)': ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'smtp_from_email', 'smtp_from_name'],
            'Message Templates': ['message_template_sms', 'message_template_whatsapp', 'message_template_email', 'email_subject_template'],
        };

        let html = '';
        for (const [group, keys] of Object.entries(settingGroups)) {
            html += `<div class="card"><div class="card-header"><h3>${group}</h3></div><div class="card-body">`;
            for (const key of keys) {
                const val = settings[key] || '';
                const isTextarea = key.startsWith('message_template');
                const isSensitive = key.includes('token') || key.includes('password') || key.includes('secret');
                html += `<div class="form-group">
                    <label>${key.replace(/_/g, ' ')}</label>
                    ${isTextarea
                        ? `<textarea class="form-control setting-input" data-key="${key}">${esc(val)}</textarea>`
                        : `<input class="form-control setting-input" data-key="${key}"
                            type="${isSensitive ? 'password' : 'text'}" value="${esc(val)}">`
                    }
                </div>`;
            }
            html += '</div></div>';
        }
        container.innerHTML = html;
    } catch (e) {
        showAlert('error', 'Failed to load settings: ' + e.message);
    }
}

async function saveSettings() {
    const inputs = document.querySelectorAll('.setting-input');
    const data = {};
    inputs.forEach(el => {
        const key = el.dataset.key;
        const val = el.value;
        // Don't save masked values
        if (!val.includes('****')) {
            data[key] = val;
        }
    });
    try {
        await api('/api/settings', { method: 'POST', body: data });
        showAlert('success', 'Settings saved!');
    } catch (e) {
        showAlert('error', e.message);
    }
}

// ─── Utilities ────────────────────────────────────────────
function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showAlert(type, msg) {
    const container = document.getElementById('alerts');
    const el = document.createElement('div');
    el.className = `alert alert-${type}`;
    el.textContent = msg;
    container.prepend(el);
    setTimeout(() => el.remove(), 6000);
}

// ─── Match & Generate buttons ─────────────────────────────
async function runScrape() {
    try {
        const result = await api('/api/scrape', { method: 'POST' });
        showAlert('success', `Scraped ${result.total_found} posts, ${result.new_saved} new engagements saved.`);
        if (currentTab === 'engagements') loadEngagements();
        if (currentTab === 'dashboard') loadDashboard();
    } catch (e) {
        showAlert('error', 'Scrape failed: ' + e.message);
    }
}

async function runMatch() {
    try {
        const result = await api('/api/match', { method: 'POST' });
        showAlert('success', `Checked ${result.engagements_checked} engagements, found ${result.total_matches} matches.`);
        if (currentTab === 'dashboard') loadDashboard();
    } catch (e) {
        showAlert('error', 'Match failed: ' + e.message);
    }
}

async function runGenerateDrafts() {
    try {
        const result = await api('/api/drafts/generate', { method: 'POST' });
        showAlert('success', `Generated ${result.drafts_created} drafts.`);
        if (currentTab === 'drafts') loadDrafts();
        if (currentTab === 'dashboard') loadDashboard();
    } catch (e) {
        showAlert('error', 'Draft generation failed: ' + e.message);
    }
}

// ─── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Tab navigation
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Close modals on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });
    });

    // Contact search debounce
    let searchTimeout;
    const searchInput = document.getElementById('contact-search');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(loadContacts, 300);
        });
    }

    // Load dashboard
    switchTab('dashboard');
});
