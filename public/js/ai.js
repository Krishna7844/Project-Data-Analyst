/* ═══════════════════════════════════════════════════════════
   ai.js — Gemini AI Insights Interface
   Handles queries to /generate-insights and renders results.
   ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    const askBtn = document.getElementById('ask-ai-btn');
    const autoSummaryBtn = document.getElementById('auto-summary-btn');
    const queryInput = document.getElementById('ai-query');
    const resultsContainer = document.getElementById('ai-results');

    // ─── Custom Query ────────────────────────────────
    askBtn.addEventListener('click', async () => {
        const query = queryInput.value.trim();
        if (!query) {
            queryInput.style.borderColor = 'var(--danger)';
            setTimeout(() => queryInput.style.borderColor = '', 1500);
            return;
        }
        await fetchInsights(query);
    });

    // ─── Auto Summary ────────────────────────────────
    autoSummaryBtn.addEventListener('click', async () => {
        await fetchInsights(null);
    });

    async function fetchInsights(query) {
        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = `
            <div style="text-align:center; padding:2rem; color:var(--text-muted);">
                <i class="fa-solid fa-spinner fa-spin fa-2x" style="color:var(--primary-light);"></i>
                <p style="margin-top:1rem;">Gemini is analyzing your data...</p>
            </div>`;

        // Disable buttons
        askBtn.disabled = true;
        autoSummaryBtn.disabled = true;

        try {
            const params = new URLSearchParams({ session_id: window.APP.sessionId });
            if (query) params.append('query', query);

            const res = await fetch(`/generate-insights?${params.toString()}`, {
                method: 'POST',
            });
            const data = await res.json();

            if (!res.ok) {
                renderError(data.detail || 'Unknown error');
                return;
            }

            if (data.error) {
                renderError(data.error);
                return;
            }

            renderInsights(data);
        } catch (err) {
            renderError('Network error: ' + err.message);
        } finally {
            askBtn.disabled = false;
            autoSummaryBtn.disabled = false;
        }
    }

    function renderInsights(data) {
        let html = '';

        // Main Insights
        if (data.insights) {
            html += `
                <div class="ai-section insights-section">
                    <h3><i class="fa-solid fa-lightbulb"></i> Analysis</h3>
                    <p>${formatText(data.insights)}</p>
                </div>`;
        }

        // Key Findings
        if (data.key_findings && data.key_findings.length > 0) {
            html += `
                <div class="ai-section findings-section">
                    <h3><i class="fa-solid fa-magnifying-glass"></i> Key Findings</h3>
                    <ul>
                        ${data.key_findings.map(f => `<li>${formatText(f)}</li>`).join('')}
                    </ul>
                </div>`;
        }

        // Recommendations
        if (data.recommendations && data.recommendations.length > 0) {
            html += `
                <div class="ai-section recommendations-section">
                    <h3><i class="fa-solid fa-clipboard-check"></i> Strategic Recommendations</h3>
                    <ul>
                        ${data.recommendations.map(r => `<li>${formatText(r)}</li>`).join('')}
                    </ul>
                </div>`;
        }

        // KPI Assessment
        if (data.kpi_assessment && data.kpi_assessment.length > 0) {
            html += `
                <div class="ai-section kpi-section">
                    <h3><i class="fa-solid fa-gauge-high"></i> KPI Assessment</h3>
                    ${data.kpi_assessment.map(kpi => `
                        <div class="kpi-assessment-item">
                            <span class="kpi-status ${(kpi.status || '').toLowerCase()}">${kpi.status || 'N/A'}</span>
                            <div>
                                <div class="kpi-name">${kpi.kpi || ''}</div>
                                <div class="kpi-detail">${kpi.detail || ''}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>`;
        }

        if (!html) {
            html = '<p style="color:var(--text-muted); padding:1rem;">No insights generated. Try a different query.</p>';
        }

        resultsContainer.innerHTML = html;
    }

    function renderError(message) {
        resultsContainer.innerHTML = `
            <div class="ai-error">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <strong> Error:</strong> ${message}
            </div>`;
    }

    function formatText(text) {
        if (!text) return '';
        // Basic formatting: bold **text**, italic *text*, code `text`
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background:rgba(99,102,241,0.15);padding:0.1rem 0.3rem;border-radius:3px;color:var(--primary-light);">$1</code>')
            .replace(/\n/g, '<br>');
    }
});
