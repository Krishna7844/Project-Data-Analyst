/* ═══════════════════════════════════════════════════════════
   app.js — Core Application Logic
   Handles file uploads, preprocessing, relationship analysis,
   and step navigation.
   ═══════════════════════════════════════════════════════════ */

const API_URL = '';  // Same origin — no CORS issues

// Global state
window.APP = {
    sessionId: null,
    currentStep: 1,
};

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileListEl = document.getElementById('file-list');
    const preprocessBtn = document.getElementById('preprocess-btn');
    const uploadStatus = document.getElementById('upload-status');
    const sections = document.querySelectorAll('section');
    const navItems = document.querySelectorAll('.sidebar nav li');

    let uploadedFiles = [];

    // ─── Navigation ──────────────────────────────────────
    function switchTab(targetId) {
        sections.forEach(sec => {
            sec.classList.remove('active-section');
            sec.classList.add('hidden-section');
        });
        const target = document.getElementById(targetId);
        if (target) {
            target.classList.remove('hidden-section');
            target.classList.add('active-section');
        }
        navItems.forEach(item => {
            item.classList.remove('active');
            if (item.dataset.target === targetId) item.classList.add('active');
        });

        // Toggle Reset Button
        const resetBtn = document.getElementById('reset-dashboard-btn');
        if (resetBtn) {
            resetBtn.style.display = targetId === 'dashboard-section' ? 'flex' : 'none';
        }
    }

    function enableStep(stepNum) {
        navItems.forEach(item => {
            if (parseInt(item.dataset.step) === stepNum) {
                item.classList.remove('disabled');
            }
        });
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            if (!item.classList.contains('disabled')) {
                switchTab(item.dataset.target);
            }
        });
    });

    window.switchTab = switchTab;

    // ─── File Upload ──────────────────────────────────────
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

    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    function handleFiles(files) {
        if (!files.length) return;
        uploadedFiles = Array.from(files);
        fileListEl.innerHTML = '';
        uploadedFiles.forEach(file => {
            const div = document.createElement('div');
            div.className = 'file-item';
            div.innerHTML = `
                <i class="fa-solid fa-file-csv"></i>
                ${file.name}
                <span style="margin-left:auto; font-size:0.8em; color:var(--text-muted);">
                    ${(file.size / 1024).toFixed(1)} KB
                </span>`;
            fileListEl.appendChild(div);
        });
        preprocessBtn.disabled = false;
    }

    // ─── Step 1: Preprocess ───────────────────────────────
    preprocessBtn.addEventListener('click', async () => {
        if (!uploadedFiles.length) return;

        uploadStatus.textContent = 'Uploading and preprocessing...';
        uploadStatus.style.color = 'var(--text-muted)';
        preprocessBtn.disabled = true;

        const formData = new FormData();
        uploadedFiles.forEach(file => formData.append('files', file));

        try {
            const res = await fetch(`${API_URL}/upload-and-preprocess`, {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();

            if (res.ok) {
                window.APP.sessionId = data.session_id;

                // Show session badge
                document.getElementById('session-badge').style.display = 'flex';
                document.getElementById('session-id-display').textContent = data.session_id;

                uploadStatus.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${data.files_processed} files cleaned successfully!`;
                uploadStatus.style.color = 'var(--accent)';

                // Render cleaning reports
                renderCleaningReports(data.reports);

                // Show Next Step button
                document.getElementById('goto-step2-btn').style.display = 'inline-flex';
                enableStep(2);
            } else {
                uploadStatus.textContent = 'Error: ' + (data.detail || 'Unknown error');
                uploadStatus.style.color = 'var(--danger)';
                preprocessBtn.disabled = false;
            }
        } catch (err) {
            console.error(err);
            uploadStatus.textContent = 'Network error. Is the server running?';
            uploadStatus.style.color = 'var(--danger)';
            preprocessBtn.disabled = false;
        }
    });

    function renderCleaningReports(reports) {
        const container = document.getElementById('cleaning-reports');
        container.style.display = 'grid';
        container.innerHTML = '';

        reports.forEach(report => {
            const card = document.createElement('div');
            card.className = 'report-card';
            card.innerHTML = `
                <h3><i class="fa-solid fa-broom"></i> ${report.filename}</h3>
                <div class="report-stats">
                    <div class="report-stat">Rows: <strong>${report.original_rows} → ${report.cleaned_rows}</strong></div>
                    <div class="report-stat">Cols: <strong>${report.original_cols} → ${report.cleaned_cols}</strong></div>
                </div>
                <ul class="changes-list">
                    ${report.changes.map(c => `<li>${c}</li>`).join('')}
                </ul>`;
            container.appendChild(card);
        });
    }

    // ─── Step 2: Analyze Relationships ───────────────────
    document.getElementById('goto-step2-btn').addEventListener('click', async () => {
        switchTab('analysis-section');
        await loadRelationships();
    });

    async function loadRelationships() {
        const loader = document.getElementById('relationship-loader');
        const results = document.getElementById('relationship-results');
        loader.style.display = 'block';
        results.innerHTML = '';

        try {
            const res = await fetch(`${API_URL}/analyze-relationships?session_id=${window.APP.sessionId}`, {
                method: 'POST'
            });
            const data = await res.json();
            loader.style.display = 'none';

            if (res.ok && data.relationships.length > 0) {
                results.innerHTML = `
                    <p style="color:var(--text-muted); margin-bottom:1rem;">
                        Found <strong style="color:var(--primary-light)">${data.total_relationships}</strong> relationships between your datasets.
                    </p>
                    <div class="relationship-grid">
                        ${data.relationships.map(rel => `
                            <div class="rel-card">
                                <span class="rel-type">${rel.relationship}</span>
                                <div class="rel-tables">
                                    <span class="table-name">${rel.table_a}</span>
                                    <span class="rel-arrow">⟷</span>
                                    <span class="table-name">${rel.table_b}</span>
                                </div>
                                <div class="rel-key">Join Key: <code>${rel.key_column}</code></div>
                                <div class="rel-meta">
                                    <span>Matching: ${rel.matching_records}</span>
                                    <span>${rel.table_a}: ${rel.table_a_unique} unique</span>
                                    <span>${rel.table_b}: ${rel.table_b_unique} unique</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>`;

                document.getElementById('goto-step3-btn').style.display = 'inline-flex';
                enableStep(3);
            } else if (res.ok) {
                results.innerHTML = '<p style="color:var(--text-muted);">No relationships detected between the uploaded tables.</p>';
                document.getElementById('goto-step3-btn').style.display = 'inline-flex';
                enableStep(3);
            } else {
                results.innerHTML = `<p style="color:var(--danger);">Error: ${data.detail}</p>`;
            }
        } catch (err) {
            loader.style.display = 'none';
            results.innerHTML = `<p style="color:var(--danger);">Network error: ${err.message}</p>`;
        }
    }

    // ─── Step 3: Dashboard ───────────────────────────────
    document.getElementById('goto-step3-btn').addEventListener('click', async () => {
        switchTab('dashboard-section');
        await window.loadDashboard();
    });

    // ─── Step 4: AI Insights ─────────────────────────────
    document.getElementById('goto-step4-btn')?.addEventListener('click', () => {
        switchTab('ai-insights-section');
    });

    // ─── Theme Toggle ────────────────────────────────────
    const themeToggle = document.getElementById('theme-toggle');

    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    themeToggle.checked = savedTheme === 'light';

    themeToggle.addEventListener('change', () => {
        const newTheme = themeToggle.checked ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    });
});
