  const access  = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');
  //if (!access) window.location.href = '../../auth/auth.html';

  const API = {
    PENDING:   '/loans/admin/requests/pending/',
    REQUESTS:  (q) => `/loans/admin/requests/?${q}`,
    REQ_DETAIL:(id) => `/loans/admin/requests/${id}/`,
    EVALUATE:  (id) => `/loans/admin/requests/${id}/evaluate/`,
    APPROVE:   (id) => `/loans/admin/requests/${id}/approve/`,
    REJECT:    (id) => `/loans/admin/requests/${id}/reject/`,
    LOANS:     (q)  => `/loans/admin/loans/?${q}`,
    LOAN_DETAIL:(id)=> `/loans/admin/loans/${id}/`,
    LOAN_STATUS:(id)=> `/loans/admin/loans/${id}/status/`,
    LOGOUT: '/api/v1/auth/logout/',
  };
  const H = () => ({'Content-Type':'application/json','Authorization':`Bearer ${access}`});

  const adminName = localStorage.getItem('user_name')||'Admin';
  document.getElementById('sidebar-name').textContent = adminName;
  document.getElementById('sidebar-avatar').textContent = adminName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()||'AD';

  function toast(msg,type='success'){
    const el=document.createElement('div'); el.className=`toast ${type}`;
    el.innerHTML=`<i class="ti ti-${type==='success'?'circle-check':'alert-circle'}"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(()=>el.remove(),4000);
  }
  function fmt(n){const v=Number(n||0);return '€'+v.toLocaleString(undefined,{minimumFractionDigits:2});}

  const tabs=['pending','requests','loans'];
  function switchTab(tab){
    tabs.forEach(t=>{
      document.getElementById('tab-'+t).classList.toggle('active',t===tab);
      document.getElementById('panel-'+t).classList.toggle('active',t===tab);
    });
    if(tab==='pending')  loadPending();
    if(tab==='requests') loadRequests();
    if(tab==='loans')    loadLoans();
  }

  // ── RISK SCORE BAR ────────────────────────────────────────────────────────
  function riskBar(score){
    const pct=Math.min(100,score||0);
    const cls=pct<40?'risk-low':pct<70?'risk-med':'risk-high';
    return `<div class="risk-bar-wrap"><div class="risk-bar-bg"><div class="risk-bar-fill ${cls}" style="width:${pct}%"></div></div><span style="font-size:12px;font-weight:700;">${score||0}</span></div>`;
  }

  // ── REQUEST TABLE ROWS ────────────────────────────────────────────────────
  function reqRows(list){
    if(!list.length) return '<div class="empty-state"><i class="ti ti-coin-off"></i><p>No loan requests found.</p></div>';
    return `<table>
      <thead><tr><th>Customer</th><th>Type</th><th>Amount</th><th>Duration</th><th>Risk</th><th>Status</th><th>Date</th></tr></thead>
      <tbody>${list.map(r=>`
        <tr onclick="openRequestDrawer('${r.id}')">
          <td>${r.customer?.fullname||'—'}</td>
          <td><span class="badge ${r.loan_type}">${r.loan_type}</span></td>
          <td style="font-weight:600;">${fmt(r.amount)}</td>
          <td>${r.duration_months}mo</td>
          <td>${riskBar(r.risk_score)}</td>
          <td><span class="badge ${r.status}">${r.status.replace('_',' ')}</span></td>
          <td style="color:var(--text-3);font-size:12px;">${r.created_at?new Date(r.created_at).toLocaleDateString('en-DE'):'—'}</td>
        </tr>`).join('')}
      </tbody></table>`;
  }

  // ── LOAN TABLE ROWS ───────────────────────────────────────────────────────
  function loanRows(list){
    if(!list.length) return '<div class="empty-state"><i class="ti ti-coin-off"></i><p>No loans found.</p></div>';
    return `<table>
      <thead><tr><th>Customer</th><th>Principal</th><th>Total Payable</th><th>Monthly</th><th>Duration</th><th>Paid</th><th>Status</th><th>Started</th></tr></thead>
      <tbody>${list.map(l=>`
        <tr onclick="openLoanDrawer('${l.id}')">
          <td>${l.customer?.fullname||'—'}</td>
          <td style="font-weight:600;">${fmt(l.principal_amount)}</td>
          <td>${fmt(l.total_payable)}</td>
          <td>${fmt(l.monthly_installment)}</td>
          <td>${l.duration_months}mo</td>
          <td>${fmt(l.paid_amount)}</td>
          <td><span class="badge ${l.status}">${l.status}</span></td>
          <td style="color:var(--text-3);font-size:12px;">${l.started_at?new Date(l.started_at).toLocaleDateString('en-DE'):'—'}</td>
        </tr>`).join('')}
      </tbody></table>`;
  }

  // ── LOAD PENDING ──────────────────────────────────────────────────────────
  async function loadPending(){
    document.getElementById('pending-wrap').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    try{
      const res=await fetch(API.PENDING,{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      document.getElementById('cnt-pending').textContent=list.length;
      document.getElementById('cnt-pending-lbl').textContent=`${list.length} pending`;
      document.getElementById('pending-wrap').innerHTML=reqRows(list);
    } catch {
      const mock=mockRequests().filter(r=>r.status==='UNDER_REVIEW');
      document.getElementById('cnt-pending').textContent=mock.length;
      document.getElementById('cnt-pending-lbl').textContent=`${mock.length} pending`;
      document.getElementById('pending-wrap').innerHTML=reqRows(mock);
    }
  }

  // ── LOAD REQUESTS ─────────────────────────────────────────────────────────
  async function loadRequests(){
    document.getElementById('requests-wrap').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    const p=new URLSearchParams();
    const s=document.getElementById('req-status').value;
    const t=document.getElementById('req-type').value;
    if(s) p.set('status',s); if(t) p.set('loan_type',t);
    try{
      const res=await fetch(API.REQUESTS(p),{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      document.getElementById('cnt-requests').textContent=list.length;
      document.getElementById('cnt-requests-lbl').textContent=`${list.length} requests`;
      document.getElementById('requests-wrap').innerHTML=reqRows(list);
    } catch {
      const list=mockRequests();
      document.getElementById('cnt-requests').textContent=list.length;
      document.getElementById('cnt-requests-lbl').textContent=`${list.length} requests`;
      document.getElementById('requests-wrap').innerHTML=reqRows(list);
    }
  }

  // ── LOAD LOANS ────────────────────────────────────────────────────────────
  async function loadLoans(){
    document.getElementById('loans-wrap').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    const p=new URLSearchParams();
    const s=document.getElementById('loan-status').value;
    if(s) p.set('status',s);
    try{
      const res=await fetch(API.LOANS(p),{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      document.getElementById('cnt-loans').textContent=list.length;
      document.getElementById('cnt-loans-lbl').textContent=`${list.length} loans`;
      document.getElementById('loans-wrap').innerHTML=loanRows(list);
    } catch {
      const list=mockLoans();
      document.getElementById('cnt-loans').textContent=list.length;
      document.getElementById('cnt-loans-lbl').textContent=`${list.length} loans`;
      document.getElementById('loans-wrap').innerHTML=loanRows(list);
    }
  }

  // ── MOCK DATA ─────────────────────────────────────────────────────────────
  function mockRequests(){
    return [
      {id:'r1',customer:{fullname:'Alice Johnson'},loan_type:'PERSONAL',amount:8000,duration_months:24,risk_score:32,status:'UNDER_REVIEW',created_at:'2026-05-10T09:00:00Z'},
      {id:'r2',customer:{fullname:'Bob Smith'},   loan_type:'HOME',    amount:45000,duration_months:60,risk_score:61,status:'UNDER_REVIEW',created_at:'2026-05-08T14:00:00Z'},
      {id:'r3',customer:{fullname:'Clara Lee'},   loan_type:'CAR',     amount:12000,duration_months:36,risk_score:28,status:'PENDING',     created_at:'2026-05-06T11:00:00Z'},
      {id:'r4',customer:{fullname:'David Park'},  loan_type:'BUSINESS',amount:30000,duration_months:48,risk_score:75,status:'APPROVED',    created_at:'2026-04-20T10:00:00Z'},
      {id:'r5',customer:{fullname:'Eva Müller'},  loan_type:'PERSONAL',amount:5000, duration_months:12,risk_score:88,status:'REJECTED',    created_at:'2026-04-15T09:00:00Z'},
    ];
  }
  function mockLoans(){
    return [
      {id:'l1',customer:{fullname:'David Park'},principal_amount:30000,total_payable:34500,monthly_installment:719,duration_months:48,paid_amount:8628,status:'ACTIVE',  started_at:'2026-04-25T00:00:00Z'},
      {id:'l2',customer:{fullname:'Hassan Ali'}, principal_amount:8000, total_payable:9200, monthly_installment:384,duration_months:24,paid_amount:9200,status:'COMPLETED',started_at:'2024-01-01T00:00:00Z'},
    ];
  }

  // ── DRAWERS ───────────────────────────────────────────────────────────────
  let activeId=null, activeMode=null;

  async function openRequestDrawer(id){
    activeId=id; activeMode='request';
    document.getElementById('drawer-title').textContent='Loan Request';
    document.getElementById('overlay').classList.add('show');
    document.getElementById('loan-drawer').classList.add('open');
    document.getElementById('drawer-body').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    document.getElementById('drawer-footer').innerHTML='';
    try{
      const res=await fetch(API.REQ_DETAIL(id),{headers:H()});
      const r=await res.json();
      renderRequestDrawer(r);
    } catch {
      const r=mockRequests().find(r=>r.id===id)||mockRequests()[0];
      renderRequestDrawer(r);
    }
  }

  function renderRequestDrawer(r){
    document.getElementById('drawer-body').innerHTML=`
      <div style="margin-bottom:1.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border);">
        <div style="display:flex;gap:8px;margin-bottom:8px;">
          <span class="badge ${r.loan_type}">${r.loan_type}</span>
          <span class="badge ${r.status}">${r.status.replace('_',' ')}</span>
        </div>
        <div style="font-family:'DM Serif Display',serif;font-size:30px;color:var(--navy);">€${Number(r.amount||0).toLocaleString()}</div>
        <div style="font-size:13px;color:var(--text-3);margin-top:4px;">${r.duration_months} months · ${r.customer?.fullname||'—'}</div>
      </div>
      <div class="detail-grid">
        <div class="detail-cell"><div class="detail-label">Monthly Income</div><div class="detail-val">€${Number(r.monthly_income||0).toLocaleString()}</div></div>
        <div class="detail-cell"><div class="detail-label">Existing Debt</div><div class="detail-val">€${Number(r.existing_debt||0).toLocaleString()}</div></div>
        <div class="detail-cell"><div class="detail-label">Risk Score</div><div class="detail-val">${riskBar(r.risk_score)}</div></div>
        <div class="detail-cell"><div class="detail-label">Submitted</div><div class="detail-val">${r.created_at?new Date(r.created_at).toLocaleDateString('en-DE'):'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Customer ID</div><div class="detail-val">${r.customer?.id||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Manager Note</div><div class="detail-val">${r.manager_note||'—'}</div></div>
      </div>`;
    const btns=[];
    btns.push(`<button class="btn warning" onclick="doEvaluate()"><i class="ti ti-calculator"></i> Evaluate</button>`);
    if(['PENDING','UNDER_REVIEW'].includes(r.status)){
      btns.push(`<button class="btn success" onclick="doApprove()"><i class="ti ti-circle-check"></i> Approve</button>`);
      btns.push(`<button class="btn danger"  onclick="openRejectModal()"><i class="ti ti-circle-x"></i> Reject</button>`);
    }
    document.getElementById('drawer-footer').innerHTML=btns.join('');
  }

  async function openLoanDrawer(id){
    activeId=id; activeMode='loan';
    document.getElementById('drawer-title').textContent='Loan Detail';
    document.getElementById('overlay').classList.add('show');
    document.getElementById('loan-drawer').classList.add('open');
    document.getElementById('drawer-body').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    document.getElementById('drawer-footer').innerHTML='';
    try{
      const res=await fetch(API.LOAN_DETAIL(id),{headers:H()});
      const l=await res.json();
      renderLoanDrawer(l);
    } catch {
      const l=mockLoans().find(l=>l.id===id)||mockLoans()[0];
      renderLoanDrawer(l);
    }
  }

  function renderLoanDrawer(l){
    const pct=l.total_payable>0?Math.round((l.paid_amount/l.total_payable)*100):0;
    document.getElementById('drawer-body').innerHTML=`
      <div style="margin-bottom:1.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border);">
        <span class="badge ${l.status}" style="margin-bottom:8px;display:inline-flex;">${l.status}</span>
        <div style="font-family:'DM Serif Display',serif;font-size:30px;color:var(--navy);">${fmt(l.principal_amount)}</div>
        <div style="font-size:13px;color:var(--text-3);margin-top:4px;">${l.customer?.fullname||'—'} · ${l.duration_months} months</div>
      </div>
      <div style="background:var(--bg);border-radius:var(--radius-sm);padding:1rem 1.25rem;margin-bottom:1.25rem;">
        <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:8px;">
          <span style="color:var(--text-3);">Repayment Progress</span>
          <span style="font-weight:600;">${pct}%</span>
        </div>
        <div style="height:8px;background:var(--border);border-radius:99px;overflow:hidden;">
          <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,var(--accent),#7c3aed);border-radius:99px;transition:width 0.6s;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-3);margin-top:6px;">
          <span>Paid: ${fmt(l.paid_amount)}</span><span>Total: ${fmt(l.total_payable)}</span>
        </div>
      </div>
      <div class="detail-grid">
        <div class="detail-cell"><div class="detail-label">Interest Rate</div><div class="detail-val">${l.interest_rate}%</div></div>
        <div class="detail-cell"><div class="detail-label">Monthly Installment</div><div class="detail-val">${fmt(l.monthly_installment)}</div></div>
        <div class="detail-cell"><div class="detail-label">Started</div><div class="detail-val">${l.started_at?new Date(l.started_at).toLocaleDateString('en-DE'):'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Customer</div><div class="detail-val">${l.customer?.fullname||'—'}</div></div>
      </div>`;
    if(l.status==='ACTIVE'){
      document.getElementById('drawer-footer').innerHTML=`
        <button class="btn ghost" onclick="openStatusModal()"><i class="ti ti-pencil"></i> Change Status</button>`;
    }
  }

  function closeDrawer(){
    document.getElementById('overlay').classList.remove('show');
    document.getElementById('loan-drawer').classList.remove('open');
    activeId=null; activeMode=null;
  }

  // ── ACTIONS ───────────────────────────────────────────────────────────────
  async function doEvaluate(){
    try{
      const res=await fetch(API.EVALUATE(activeId),{method:'POST',headers:H(),body:'{}' });
      const d=await res.json();
      toast(`Risk score: ${d.risk_score} · Status: ${d.status}`);
      closeDrawer(); loadPending();
    } catch { toast('Evaluation failed','error'); }
  }

  async function doApprove(){
    try{
      const res=await fetch(API.APPROVE(activeId),{method:'POST',headers:H(),body:'{}'});
      if(res.ok){ toast('Loan approved and created!'); closeDrawer(); loadPending(); loadLoans(); }
      else { const d=await res.json(); toast(d.detail||'Failed','error'); }
    } catch { toast('Network error','error'); }
  }

  function openRejectModal(){ document.getElementById('reject-modal').classList.add('show'); }
  function closeRejectModal(){ document.getElementById('reject-modal').classList.remove('show'); }
  async function confirmReject(){
    const reason=document.getElementById('reject-reason').value.trim();
    if(!reason){ toast('Please enter a reason','error'); return; }
    const btn=document.getElementById('reject-btn'); const spin=document.getElementById('reject-spin');
    btn.disabled=true; spin.style.display='block';
    try{
      const res=await fetch(API.REJECT(activeId),{method:'POST',headers:H(),body:JSON.stringify({reason})});
      if(res.ok){ toast('Request rejected'); closeRejectModal(); closeDrawer(); loadPending(); loadRequests(); }
      else { const d=await res.json(); toast(d.detail||'Failed','error'); }
    } catch { toast('Network error','error'); }
    finally { btn.disabled=false; spin.style.display='none'; document.getElementById('reject-reason').value=''; }
  }

  function openStatusModal(){ document.getElementById('status-modal').classList.add('show'); }
  function closeStatusModal(){ document.getElementById('status-modal').classList.remove('show'); }
  async function confirmStatusChange(){
    const s=document.getElementById('new-status').value;
    const note=document.getElementById('status-note').value;
    const btn=document.getElementById('status-btn'); const spin=document.getElementById('status-spin');
    btn.disabled=true; spin.style.display='block';
    try{
      const res=await fetch(API.LOAN_STATUS(activeId),{method:'POST',headers:H(),body:JSON.stringify({status:s,note})});
      if(res.ok){ toast(`Loan status changed to ${s}`); closeStatusModal(); closeDrawer(); loadLoans(); }
      else { const d=await res.json(); toast(d.detail||'Failed','error'); }
    } catch { toast('Network error','error'); }
    finally { btn.disabled=false; spin.style.display='none'; }
  }

  ['reject-modal','status-modal'].forEach(id=>{
    document.getElementById(id).addEventListener('click',function(e){ if(e.target===this) this.classList.remove('show'); });
  });

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear(); window.location.href='../../auth/auth.html';
  }

  loadPending();
