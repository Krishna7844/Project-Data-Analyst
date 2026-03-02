/* ═══════════════════════════════════════════════════════════
   dashboard.js — Chart.js Dashboard Rendering
   Fetches /dashboard-data and renders KPI cards + charts.
   ═══════════════════════════════════════════════════════════ */

// Color palette for charts
const CHART_COLORS = [
    '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#14b8a6',
];

const CHART_COLORS_TRANSPARENT = CHART_COLORS.map(c => c + '33');

// Store chart instances for cleanup
// Store chart instances for cleanup
const chartInstances = [];
let activeFilters = {}; // { "Region": "West", ... }

// Reset Button Logic
document.addEventListener('DOMContentLoaded', () => {
    const resetBtn = document.getElementById('reset-dashboard-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            // Clear active filters
            activeFilters = {};
            // Reload dashboard with empty filters
            window.loadDashboard({});

            // Optional: Add a temporary visual feedback?
            const icon = resetBtn.querySelector('i');
            icon.classList.add('fa-spin');
            setTimeout(() => icon.classList.remove('fa-spin'), 500);
        });
    }
});

window.loadDashboard = async function (filters = {}) {
    // frequent calls shouldn't reset activeFilters if passed from outside, 
    // but here we merge new filters into activeFilters
    Object.assign(activeFilters, filters);

    // If a filter is set to null, remove it
    Object.keys(filters).forEach(key => {
        if (filters[key] === null) delete activeFilters[key];
    });

    const loader = document.getElementById('dashboard-loader');
    const kpiGrid = document.getElementById('kpi-grid');
    const chartsGrid = document.getElementById('charts-grid');
    const tablesPreview = document.getElementById('tables-preview');

    // Only show loader if it's the initial load or a major refresh
    // For interactivity, maybe keep it subtle or don't clear everything immediately?
    // For now, let's keep the standard loading behavior but maybe optimize later
    loader.style.display = 'block';

    // Clear grids only if not an update? 
    // Actually, re-rendering everything is safer for keeping consistency
    kpiGrid.innerHTML = '';
    chartsGrid.innerHTML = '';
    tablesPreview.innerHTML = '';

    // Destroy old charts
    chartInstances.forEach(c => c.destroy());
    chartInstances.length = 0;

    try {
        const filterStr = encodeURIComponent(JSON.stringify(activeFilters));
        const res = await fetch(`/dashboard-data?session_id=${window.APP.sessionId}&filters=${filterStr}`);
        const data = await res.json();
        loader.style.display = 'none';

        if (!res.ok) {
            kpiGrid.innerHTML = `<p style="color:var(--danger);">Error: ${data.detail}</p>`;
            return;
        }

        // ─── KPI Cards ───────────────────────────────
        data.kpis.forEach((kpi, i) => {
            const card = document.createElement('div');
            card.className = 'kpi-card';
            card.innerHTML = `
                <i class="fa-solid ${kpi.icon || 'fa-chart-simple'}"></i>
                <div class="kpi-value" data-target="${kpi.value}">0</div>
                <div class="kpi-label">${kpi.label}</div>`;
            kpiGrid.appendChild(card);

            // Animate counter
            animateCounter(card.querySelector('.kpi-value'), kpi.value);
        });

        // ─── Charts ──────────────────────────────────
        data.charts.forEach((chart, idx) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'chart-card';
            wrapper.innerHTML = `<h3>${chart.title}</h3><canvas id="chart-${idx}"></canvas>`;
            chartsGrid.appendChild(wrapper);

            const ctx = document.getElementById(`chart-${idx}`).getContext('2d');
            const instance = createChart(ctx, chart);
            chartInstances.push(instance);
        });

        // ─── Data Preview Tables ─────────────────────
        if (data.tables_preview) {
            data.tables_preview.forEach(table => {
                const wrap = document.createElement('div');
                wrap.className = 'preview-table-wrap';
                wrap.innerHTML = `
                    <h3><i class="fa-solid fa-table"></i> ${table.name} <span style="font-weight:400; color:var(--text-muted); font-size:0.85rem;">(${table.total_rows} rows)</span></h3>
                    <table class="data-table">
                        <thead>
                            <tr>${table.columns.map(c => `<th>${c}</th>`).join('')}</tr>
                        </thead>
                        <tbody>
                            ${table.rows.map(row => `<tr>${row.map(v => `<td>${v ?? ''}</td>`).join('')}</tr>`).join('')}
                        </tbody>
                    </table>`;
                tablesPreview.appendChild(wrap);
            });
        }

        // Enable Step 4
        document.getElementById('goto-step4-btn').style.display = 'inline-flex';
        document.querySelector('[data-target="ai-insights-section"]').classList.remove('disabled');

    } catch (err) {
        loader.style.display = 'none';
        kpiGrid.innerHTML = `<p style="color:var(--danger);">Network error: ${err.message}</p>`;
    }
};

function createChart(ctx, chartData) {
    const config = {
        type: chartData.type,
        data: {
            labels: chartData.labels,
            datasets: [{
                label: chartData.title,
                data: chartData.data,
                backgroundColor: chartData.type === 'line'
                    ? CHART_COLORS[0] + '22'
                    : CHART_COLORS.slice(0, chartData.data.length),
                borderColor: chartData.type === 'line'
                    ? CHART_COLORS[0]
                    : CHART_COLORS.slice(0, chartData.data.length),
                borderWidth: chartData.type === 'line' ? 2 : 1,
                fill: chartData.type === 'line',
                tension: 0.4,
                pointBackgroundColor: CHART_COLORS[0],
                pointRadius: chartData.type === 'line' ? 3 : 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: ['pie', 'doughnut'].includes(chartData.type),
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } },
                },
                title: { display: false },
            },
            scales: ['bar', 'line'].includes(chartData.type) ? {
                x: {
                    ticks: { color: '#64748b', font: { family: 'Outfit', size: 10 }, maxRotation: 45 },
                    grid: { color: 'rgba(255,255,255,0.04)' },
                },
                y: {
                    ticks: { color: '#64748b', font: { family: 'Outfit', size: 10 } },
                    grid: { color: 'rgba(255,255,255,0.04)' },
                },
            } : {},
            onClick: (e, elements, chart) => {
                if (!elements.length) return;

                const index = elements[0].index;
                const label = chart.data.labels[index];

                // Determine the column name from the title or data
                // Heuristic: We need to know which column this chart represents
                // The backend sends "title": "Region Distribution (Sales)"
                // We can parse it or pass metadata. For now, let's try to infer or pass it.
                // Ideally, backend should send "column" in chartData.

                // Let's rely on the title for now which is formatted as "{col} Distribution ({table})"
                // or "{col} Over Time ({table})" or "Average Values ({table})"

                let column = null;
                const title = chartData.title;

                if (title.includes("Distribution")) {
                    column = title.split(" Distribution")[0];
                } else if (title.includes("Over Time")) {
                    // For line charts over time, usually "Date" or similar. 
                    // The label is YYYY-MM. Filtering by this might be complex (substring match).
                    // Let's skip line chart filtering for now to avoid errors unless we implement date parsing.
                    return;
                } else if (title.includes("Average Values")) {
                    // This is a summary chart of multiple columns. Clicking a bar means selecting that column?
                    // Not really a filter on rows. Skip.
                    return;
                }

                if (column) {
                    // Toggle filter
                    // If current filter for this col is the clicked label, remove it (set to null)
                    const val = activeFilters[column] === label ? null : label;
                    window.loadDashboard({ [column]: val });
                }
            }
        },
    };
    return new Chart(ctx, config);
}

function animateCounter(element, target) {
    const isFloat = !Number.isInteger(target);
    const duration = 1200;
    const start = performance.now();

    function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic

        const current = eased * target;
        element.textContent = isFloat
            ? current.toFixed(2)
            : Math.floor(current).toLocaleString();

        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}
