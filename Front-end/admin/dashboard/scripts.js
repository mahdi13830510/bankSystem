  const access  = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');
  //if (!access) window.location.href = '/auth/auth.html';

  const API = {
    DASHBOARD: '/dashboard/overview/',
    FRAUD:     '/fraud/reports/',
    LOGOUT:    '/api/v1/auth/logout/',
  };
  function authHeaders() {
    return { 'Content-Type':'application/json', 'Authorization':`Bearer ${access}` };
  }

  // sidebar user
  const userName = localStorage.getItem('user_name') || 'Admin';
  document.getElementById('sidebar-name').textContent = userName;
  const initials = userName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase() || 'AD';
  document.getElementById('sidebar-avatar').textContent = initials;

  // topbar date
  document.getElementById('topbar-date').textContent = new Date().toLocaleDateString('en-DE',{weekday:'long',year:'numeric',month:'long',day:'numeric'});

  // toast
  function showToast(msg, type='error') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<i class="ti ti-alert-circle"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(()=>el.remove(), 4000);
  }

  function fmt(n) {
    const num = Number(n||0);
    if (num >= 1_000_000) return '€' + (num/1_000_000).toFixed(1) + 'M';
    if (num >= 1_000)     return '€' + (num/1_000).toFixed(1) + 'K';
    return '€' + num.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
  }

  // ── CHART SETUP ────────────────────────────────────────────────────────────
  let trendChart = null;
  let chartDays  = 7;

  function initChart(labels, values) {
    const ctx = document.getElementById('trend-chart').getContext('2d');
    if (trendChart) trendChart.destroy();
    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Transaction Volume',
          data: values,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,0.08)',
          borderWidth: 2.5,
          pointBackgroundColor: '#3b82f6',
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend:{ display:false }, tooltip:{ callbacks:{ label: ctx => ' €' + Number(ctx.raw).toLocaleString() } } },
        scales: {
          x: { grid:{ display:false }, ticks:{ font:{ family:'Sora', size:11 }, color:'#94a3b8' } },
          y: { grid:{ color:'#f1f5f9' }, ticks:{ font:{ family:'Sora', size:11 }, color:'#94a3b8', callback: v => '€'+Number(v).toLocaleString() } }
        }
      }
    });
  }

  function setChartDays(days, btn) {
    chartDays = days;
    document.querySelectorAll('.period-pill').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    loadAll();
  }

  // ── LOAD DASHBOARD ─────────────────────────────────────────────────────────
  async function loadDashboard() {
    try {
      const res  = await fetch(API.DASHBOARD, { headers:authHeaders() });
      if (!res.ok) throw new Error();
      const d = await res.json();

      // KPIs
      const fin  = d.kpis?.financial   || {};
      const usr  = d.kpis?.users       || {};
      const lns  = d.kpis?.loans       || {};
      const txs  = d.kpis?.transactions|| {};

      document.getElementById('kpi-total-balance').textContent = fmt(fin.total_balance);
      document.getElementById('kpi-total-users').textContent   = (usr.total_users||0).toLocaleString();
      document.getElementById('kpi-active-users-sub').innerHTML = `<i class="ti ti-user-check"></i> ${usr.active_users||0} active`;
      document.getElementById('kpi-active-loans').textContent  = (lns.active_loans||0).toLocaleString();
      document.getElementById('kpi-pending-loans-sub').innerHTML = `<i class="ti ti-clock"></i> ${lns.pending_loans||0} pending review`;
      document.getElementById('kpi-total-tx').textContent      = (txs.total||0).toLocaleString();
      document.getElementById('pending-badge').textContent     = lns.pending_loans||0;

      // loan & user mini
      document.getElementById('loans-active').textContent  = lns.active_loans||0;
      document.getElementById('loans-pending').textContent = lns.pending_loans||0;
      document.getElementById('users-total').textContent   = usr.total_users||0;
      document.getElementById('users-active').textContent  = usr.active_users||0;
      document.getElementById('rt-avg-balance').textContent = fin.avg_balance ? fmt(fin.avg_balance) : '—';

      // realtime
      const rt = d.realtime || {};
      document.getElementById('rt-tx-minute').textContent   = rt.tx_last_minute ?? '—';
      const healthy = (rt.system_status||'').toUpperCase() === 'HEALTHY';
      document.getElementById('system-status-text').textContent = healthy ? 'All systems operational' : rt.system_status || '—';

      // fraud summary
      const fr = d.fraud || {};
      document.getElementById('fraud-total').textContent  = fr.total_alerts||0;
      document.getElementById('fraud-medium').textContent = fr.medium_risk||0;
      document.getElementById('fraud-high').textContent   = fr.high_risk||0;

      // trend chart — slice to chartDays
      const trend = (d.analytics?.trend || []).slice(-chartDays);
      const labels = trend.map(t => { const d=new Date(t.date); return d.toLocaleDateString('en-DE',{month:'short',day:'numeric'}); });
      const values = trend.map(t => Number(t.volume||0));
      initChart(labels, values);

      // recent fraud alerts
      renderFraudAlerts(d.recent_fraud_alerts || []);

      // last updated
      document.getElementById('last-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();

    } catch {
      // mock data fallback
      document.getElementById('kpi-total-balance').textContent = '€2.4M';
      document.getElementById('kpi-total-users').textContent   = '1,284';
      document.getElementById('kpi-active-users-sub').innerHTML = '<i class="ti ti-user-check"></i> 1,102 active';
      document.getElementById('kpi-active-loans').textContent  = '348';
      document.getElementById('kpi-pending-loans-sub').innerHTML = '<i class="ti ti-clock"></i> 12 pending review';
      document.getElementById('kpi-total-tx').textContent      = '28,541';
      document.getElementById('pending-badge').textContent     = '12';
      document.getElementById('loans-active').textContent  = '348';
      document.getElementById('loans-pending').textContent = '12';
      document.getElementById('users-total').textContent   = '1,284';
      document.getElementById('users-active').textContent  = '1,102';
      document.getElementById('rt-tx-minute').textContent  = '3';
      document.getElementById('rt-avg-balance').textContent = '€1.8K';

      // mock chart
      const today = new Date();
      const labels = Array.from({length:chartDays},(_,i)=>{
        const d=new Date(today); d.setDate(d.getDate()-(chartDays-1-i));
        return d.toLocaleDateString('en-DE',{month:'short',day:'numeric'});
      });
      const values = labels.map(()=>Math.floor(Math.random()*80000)+20000);
      initChart(labels, values);

      document.getElementById('fraud-total').textContent  = '47';
      document.getElementById('fraud-medium').textContent = '29';
      document.getElementById('fraud-high').textContent   = '8';
      renderFraudAlerts([
        {id:'a1',score:91,decision:'BLOCKED',   transaction_id:'tx-aaa-111'},
        {id:'a2',score:72,decision:'SUSPICIOUS', transaction_id:'tx-bbb-222'},
        {id:'a3',score:65,decision:'SUSPICIOUS', transaction_id:'tx-ccc-333'},
        {id:'a4',score:88,decision:'BLOCKED',    transaction_id:'tx-ddd-444'},
        {id:'a5',score:22,decision:'SAFE',       transaction_id:'tx-eee-555'},
      ]);
      document.getElementById('last-updated').textContent = 'Mock data';
    }
  }

  // ── FRAUD ALERTS RENDER ────────────────────────────────────────────────────
  function renderFraudAlerts(alerts) {
    const el = document.getElementById('fraud-list');
    if (!alerts.length) { el.innerHTML='<div class="empty"><i class="ti ti-shield-check"></i>No recent alerts</div>'; return; }
    el.innerHTML = alerts.slice(0,6).map(a => {
      const dec = (a.decision||'').toLowerCase();
      const clr = dec==='blocked'?'var(--danger)':dec==='suspicious'?'var(--warning)':'var(--success)';
      const pct = Math.min(100,a.score||0);
      return `
        <div class="fraud-item">
          <div style="flex-shrink:0;">
            <span class="badge ${dec}">${a.decision||'—'}</span>
          </div>
          <div class="fraud-score-bar">
            <div class="fraud-bar-bg"><div class="fraud-bar-fill ${dec}" style="width:${pct}%"></div></div>
          </div>
          <div class="fraud-score-num" style="color:${clr};">${a.score}</div>
          <div class="fraud-tx">${String(a.transaction_id||'').slice(0,16)}…</div>
        </div>`;
    }).join('');
  }

  // ── LOAD FRAUD (separate endpoint) ────────────────────────────────────────
  async function loadFraud() {
    try {
      const res  = await fetch(API.FRAUD, { headers:authHeaders() });
      const data = await res.json();
      const list = Array.isArray(data) ? data : (data.results||[]);
      if (list.length) renderFraudAlerts(list);
    } catch { /* dashboard already has recent_fraud_alerts */ }
  }

  // ── MAIN LOAD ─────────────────────────────────────────────────────────────
  async function loadAll() {
    const btn = document.getElementById('refresh-btn');
    btn.classList.add('spinning');
    await Promise.all([loadDashboard(), loadFraud()]);
    btn.classList.remove('spinning');
  }

  // ── LOGOUT ────────────────────────────────────────────────────────────────
  async function logout() {
    try { await fetch(API.LOGOUT,{method:'POST',headers:authHeaders(),body:JSON.stringify({refresh_token:refresh})}); } catch {}
    localStorage.clear();
    window.location.href='/auth/auth.html';
  }

  loadAll();
  // auto-refresh every 60 seconds
  setInterval(loadAll, 60000);