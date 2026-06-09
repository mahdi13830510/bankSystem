  // ── ENDPOINTS ─────────────────────────────────────────────────────────────
  const API = {
    ME:           '/api/v1/users/me/',
    ACCOUNTS:     '/accounts/my/',
    LOANS:        '/loans/my-loans/',
    INSTALLMENTS: '/installments/my/',
    NOTIFS:       '/notifications/my/',
    NOTIF_COUNT:  '/notifications/unread-count/',
    NOTIF_READ:   (id) => `/notifications/${id}/read/`,
    NOTIF_ALL:    '/notifications/mark-all-read/',
    LOGOUT:       '/api/v1/auth/logout/',
  };

  const access  = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');
  if (!access) window.location.href = '../../auth/auth.html';

  const H = () => ({ 'Content-Type': 'application/json', 'Authorization': `Bearer ${access}` });

  function toast(msg, type='success') {
    const el = document.createElement('div'); el.className = `toast`;
    el.innerHTML = `<i class="ti ti-${type==='success'?'circle-check':'alert-circle'}"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  function fmt(n) {
    return '€' + Number(n||0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2});
  }

  // ── GREETING ──────────────────────────────────────────────────────────────
  function initGreeting() {
    const now  = new Date();
    const hour = now.getHours();
    const greet = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    const name  = localStorage.getItem('user_name') || '';
    document.getElementById('topbar-greeting').textContent = `${greet}${name ? ', ' + name.split(' ')[0] : ''} 👋`;
    document.getElementById('topbar-date').textContent = now.toLocaleDateString('en-DE', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
    const initials = name ? name.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase() : 'U';
    document.getElementById('sidebar-avatar').textContent = initials;
    document.getElementById('sidebar-name').textContent = name || 'My Account';
  }

  // ── LOAD ACCOUNTS ─────────────────────────────────────────────────────────
  async function loadAccounts() {
    try {
      const res  = await fetch(API.ACCOUNTS, { headers: H() });
      const data = await res.json();
      const accounts = Array.isArray(data) ? data : (data.results || []);
      // find primary or first
      const primary = accounts.find(a => a.is_primary) || accounts[0];
      if (primary) {
        document.getElementById('balance-amount').textContent  = Number(primary.balance||0).toLocaleString(undefined,{minimumFractionDigits:2});
        document.getElementById('account-number').textContent  = primary.account_number ? primary.account_number.slice(-8) : '—';
        document.getElementById('available-balance').textContent = fmt(Number(primary.balance||0) - Number(primary.blocked_balance||0));
        document.getElementById('blocked-balance').textContent   = fmt(primary.blocked_balance);
        document.getElementById('account-type').textContent      = primary.type || '—';
        localStorage.setItem('account_id', primary.id);
        localStorage.setItem('account_number', primary.account_number || '');
      }
    } catch {
      document.getElementById('balance-amount').textContent = '—';
    }
  }

  // ── LOAD LOANS ────────────────────────────────────────────────────────────
  async function loadLoans() {
    const el = document.getElementById('loan-list');
    try {
      const res  = await fetch(API.LOANS, { headers: H() });
      const data = await res.json();
      const loans = Array.isArray(data) ? data : (data.results || []);
      if (!loans.length) { el.innerHTML = '<div class="empty"><i class="ti ti-coin-off"></i>No active loans</div>'; return; }
      el.innerHTML = loans.slice(0,3).map(l => `
        <div class="loan-item">
          <div class="loan-icon"><i class="ti ti-coin"></i></div>
          <div style="flex:1;">
            <div class="loan-name">${(l.loan_type||'Loan').replace(/_/g,' ')}</div>
            <div class="loan-meta">${l.started_at?new Date(l.started_at).toLocaleDateString('en-DE'):''} ${l.duration_months?'· '+l.duration_months+' months':''}</div>
          </div>
          <div style="text-align:right;">
            <div class="loan-amount-val">${fmt(l.principal_amount)}</div>
            <span class="badge ${l.status==='ACTIVE'?'success':l.status==='COMPLETED'?'success':'warning'}">${l.status||'active'}</span>
          </div>
        </div>`).join('');
    } catch {
      el.innerHTML = '<div class="empty"><i class="ti ti-coin-off"></i>No active loans</div>';
    }
  }

  // ── LOAD INSTALLMENTS ─────────────────────────────────────────────────────
  async function loadInstallments() {
    const el = document.getElementById('installment-list');
    try {
      const res  = await fetch(API.INSTALLMENTS, { headers: H() });
      const data = await res.json();
      const insts = Array.isArray(data) ? data : (data.results || []);
      const pending = insts.filter(i => i.status !== 'PAID').slice(0,3);
      if (!pending.length) { el.innerHTML = '<div class="empty"><i class="ti ti-receipt-off"></i>No pending installments</div>'; return; }
      el.innerHTML = pending.map(i => {
        const paid  = i.paid_amount||0;
        const total = i.amount||1;
        const pct   = Math.min(100, Math.round((paid/total)*100));
        return `
          <div class="inst-item">
            <div class="inst-top">
              <span class="inst-name">Installment #${i.number}</span>
              <span class="inst-due">Due: ${i.due_date||'—'}</span>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
            <div class="inst-foot">
              <span class="inst-paid">${fmt(paid)} paid</span>
              <span class="inst-remaining">${fmt(total)} total</span>
            </div>
          </div>`;
      }).join('');
    } catch {
      el.innerHTML = '<div class="empty"><i class="ti ti-receipt-off"></i>No installments</div>';
    }
  }

  // ── NOTIFICATIONS ─────────────────────────────────────────────────────────
  async function loadUnreadCount() {
    try {
      const res  = await fetch(API.NOTIF_COUNT, { headers: H() });
      const data = await res.json();
      const count = data.count || data.unread_count || 0;
      if (count > 0) {
        const badge = document.getElementById('notif-nav-badge');
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.add('show');
        document.getElementById('notif-dot').classList.add('show');
      }
    } catch { /* silent */ }
  }

  async function loadNotifications() {
    const el = document.getElementById('notif-list');
    try {
      const res  = await fetch(API.NOTIFS, { headers: H() });
      const data = await res.json();
      const notifs = Array.isArray(data) ? data : (data.results || []);
      if (!notifs.length) { el.innerHTML = '<div class="empty"><i class="ti ti-bell-off"></i>No notifications</div>'; return; }
      el.innerHTML = notifs.map(n => `
        <div class="notif-item ${!n.is_read?'unread':''}" onclick="markRead('${n.id}',this)">
          <div class="notif-dot-indicator"></div>
          <div>
            <div class="notif-title-txt">${n.title||'Notification'}</div>
            <div class="notif-msg">${n.message||n.body||''}</div>
            <div class="notif-time">${n.created_at?new Date(n.created_at).toLocaleString('en-DE',{dateStyle:'short',timeStyle:'short'}):''}</div>
          </div>
        </div>`).join('');
    } catch {
      el.innerHTML = '<div class="empty"><i class="ti ti-bell-off"></i>No notifications</div>';
    }
  }

  async function markRead(id, el) {
    el.classList.remove('unread');
    try { await fetch(API.NOTIF_READ(id), { method: 'POST', headers: H() }); } catch { /* silent */ }
  }

  async function markAllRead() {
    document.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
    document.getElementById('notif-nav-badge').classList.remove('show');
    document.getElementById('notif-dot').classList.remove('show');
    try { await fetch(API.NOTIF_ALL, { method: 'POST', headers: H() }); } catch { /* silent */ }
    toast('All notifications marked as read');
  }

  function openNotifPanel(e) {
    if (e) e.preventDefault();
    document.getElementById('notif-panel').classList.add('open');
    document.getElementById('overlay').classList.add('show');
    loadNotifications();
  }
  function closeNotifPanel() {
    document.getElementById('notif-panel').classList.remove('open');
    document.getElementById('overlay').classList.remove('show');
  }

  // ── LOGOUT ────────────────────────────────────────────────────────────────
  async function logout() {
    try {
      await fetch(API.LOGOUT, {
        method: 'POST', headers: H(),
        body: JSON.stringify({ refresh_token: refresh }),
      });
    } catch { /* best-effort */ }
    localStorage.clear();
    window.location.href = '../../auth/auth.html';
  }

  // ── INIT ──────────────────────────────────────────────────────────────────
  initGreeting();
  loadAccounts();
  loadLoans();
  loadInstallments();
  loadUnreadCount();
