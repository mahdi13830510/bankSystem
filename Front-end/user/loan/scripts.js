  // ── ENDPOINTS ─────────────────────────────────────────────────────────────
  const API = {
    REQUEST:     '/loans/request/',
    MY_REQUESTS: '/loans/my-requests/',
    MY_LOANS:    '/loans/my-loans/',
    LOGOUT:      '/api/v1/auth/logout/',
  };

  const access  = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');
  if (!access) window.location.href = '../../auth/auth.html';
  const H = () => ({ 'Content-Type':'application/json', 'Authorization':`Bearer ${access}` });

  const userName = localStorage.getItem('user_name')||'';
  document.getElementById('sidebar-name').textContent = userName||'My Account';
  document.getElementById('sidebar-avatar').textContent = userName?userName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase():'U';

  function toast(msg,type='success'){
    const el=document.createElement('div');el.className='toast';
    el.innerHTML=`<i class="ti ti-${type==='success'?'circle-check':'alert-circle'}"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);setTimeout(()=>el.remove(),4000);
  }

  // ── TABS ──────────────────────────────────────────────────────────────────
  const tabs=['request','my-requests','my-loans'];
  function switchTab(tab){
    tabs.forEach(t=>{
      document.getElementById('tab-'+t).classList.toggle('active',t===tab);
      document.getElementById('panel-'+t).classList.toggle('active',t===tab);
    });
    if(tab==='my-requests') loadRequests();
    if(tab==='my-loans')    loadLoans();
  }

  // ── LOAN TYPE ─────────────────────────────────────────────────────────────
  let selectedType='PERSONAL';
  function selectType(el){
    document.querySelectorAll('.type-card').forEach(c=>c.classList.remove('selected'));
    el.classList.add('selected');
    selectedType=el.dataset.type;
    updateSummary();
  }

  // ── AMOUNT SLIDER ─────────────────────────────────────────────────────────
  function updateAmount(input){
    const val=Number(input.value);
    document.getElementById('amount-display').textContent=val.toLocaleString();
    const pct=((val-1000)/(100000-1000))*100;
    input.style.setProperty('--pct',pct+'%');
    updateSummary();
  }
  (()=>{ const r=document.getElementById('amount-range'); r.style.setProperty('--pct',((10000-1000)/(100000-1000)*100)+'%'); })();

  function updateSummary(){
    const amount=Number(document.getElementById('amount-range').value);
    const duration=Number(document.getElementById('duration').value);
    if(!duration){ document.getElementById('est-monthly').textContent='—'; document.getElementById('est-total').textContent='—'; return; }
    const rate=0.065/12;
    const monthly=(amount*rate*Math.pow(1+rate,duration))/(Math.pow(1+rate,duration)-1);
    const total=monthly*duration;
    document.getElementById('est-monthly').textContent='€'+monthly.toFixed(2);
    document.getElementById('est-total').textContent='€'+total.toFixed(2);
  }

  // ── VALIDATION ────────────────────────────────────────────────────────────
  function fe(id,msg){ const el=document.getElementById(id); if(msg){el.textContent=msg;el.classList.add('show');}else el.classList.remove('show'); }
  function validateForm(){
    let ok=true;
    if(!selectedType){ fe('err-type','Please select a loan type.'); ok=false; } else fe('err-type','');
    if(!document.getElementById('duration').value){ fe('err-duration','Please select a duration.'); ok=false; } else fe('err-duration','');
    const income=document.getElementById('monthly-income').value;
    if(!income||Number(income)<=0){ fe('err-income','Please enter your monthly income.'); ok=false; } else fe('err-income','');
    return ok;
  }

  // ── SUBMIT FLOW ───────────────────────────────────────────────────────────
  function submitLoanRequest(){
    if(!validateForm()) return;
    const amount=Number(document.getElementById('amount-range').value);
    const dur=document.getElementById('duration').value;
    const income=document.getElementById('monthly-income').value;
    const debt=document.getElementById('existing-debt').value||'0';
    const typeLabel={PERSONAL:'Personal',HOME:'Home',CAR:'Car',BUSINESS:'Business'};
    document.getElementById('confirm-body').innerHTML=`
      <table style="width:100%;border-collapse:collapse;font-size:13.5px;">
        <tr><td style="padding:6px 0;color:var(--text-3);">Type</td><td style="text-align:right;font-weight:600;">${typeLabel[selectedType]}</td></tr>
        <tr><td style="padding:6px 0;color:var(--text-3);">Amount</td><td style="text-align:right;font-weight:600;">€${amount.toLocaleString()}</td></tr>
        <tr><td style="padding:6px 0;color:var(--text-3);">Duration</td><td style="text-align:right;font-weight:600;">${dur} months</td></tr>
        <tr><td style="padding:6px 0;color:var(--text-3);">Monthly Income</td><td style="text-align:right;font-weight:600;">€${Number(income).toLocaleString()}</td></tr>
        <tr><td style="padding:6px 0;color:var(--text-3);">Existing Debt</td><td style="text-align:right;font-weight:600;">€${Number(debt).toLocaleString()}</td></tr>
        <tr style="border-top:1px solid var(--border);"><td style="padding:8px 0 2px;color:var(--text-3);">Est. Monthly Payment</td><td style="text-align:right;font-weight:700;color:var(--accent);">${document.getElementById('est-monthly').textContent}</td></tr>
      </table>`;
    document.getElementById('confirm-modal').classList.add('show');
  }

  function closeModal(){ document.getElementById('confirm-modal').classList.remove('show'); }

  async function confirmSubmit(){
    const btn=document.getElementById('confirm-btn');
    const spin=document.getElementById('confirm-spin');
    const txt=document.getElementById('confirm-text');
    btn.disabled=true;spin.style.display='block';txt.textContent='Submitting…';

    // Backend field name is loan_type (not type)
    const payload={
      amount:          Number(document.getElementById('amount-range').value),
      duration_months: Number(document.getElementById('duration').value),
      loan_type:       selectedType,
      monthly_income:  Number(document.getElementById('monthly-income').value),
      existing_debt:   Number(document.getElementById('existing-debt').value||0),
    };

    try{
      const res=await fetch(API.REQUEST,{method:'POST',headers:H(),body:JSON.stringify(payload)});
      const data=await res.json();
      if(res.ok){
        closeModal();
        toast('Loan application submitted successfully!');
        resetForm();
        switchTab('my-requests');
      } else { closeModal(); toast(data.detail||data.message||'Submission failed.','error'); }
    } catch { closeModal(); toast('Network error.','error'); }
    finally{ btn.disabled=false;spin.style.display='none';txt.textContent='Confirm & Submit'; }
  }

  function resetForm(){
    document.getElementById('amount-range').value=10000;
    document.getElementById('amount-display').textContent='10,000';
    document.getElementById('amount-range').style.setProperty('--pct',((10000-1000)/(100000-1000)*100)+'%');
    document.getElementById('duration').value='';
    document.getElementById('monthly-income').value='';
    document.getElementById('existing-debt').value='0';
    selectedType='PERSONAL';
    document.querySelectorAll('.type-card').forEach(c=>c.classList.remove('selected'));
    document.querySelector('[data-type="PERSONAL"]').classList.add('selected');
    document.getElementById('est-monthly').textContent='—';
    document.getElementById('est-total').textContent='—';
    ['err-type','err-duration','err-income'].forEach(id=>fe(id,''));
  }

  // ── TYPE HELPERS ──────────────────────────────────────────────────────────
  const typeIcon ={HOME:'ti-home',CAR:'ti-car',BUSINESS:'ti-briefcase',PERSONAL:'ti-user'};
  const typeLabel={HOME:'Home Loan',CAR:'Car Loan',BUSINESS:'Business Loan',PERSONAL:'Personal Loan'};

  function statusBadge(status){
    const map={
      PENDING:'<span class="badge PENDING"><i class="ti ti-clock"></i> Pending</span>',
      UNDER_REVIEW:'<span class="badge UNDER_REVIEW"><i class="ti ti-search"></i> Under Review</span>',
      APPROVED:'<span class="badge APPROVED"><i class="ti ti-circle-check"></i> Approved</span>',
      REJECTED:'<span class="badge REJECTED"><i class="ti ti-circle-x"></i> Rejected</span>',
      ACTIVE:'<span class="badge ACTIVE"><i class="ti ti-circle-check"></i> Active</span>',
      COMPLETED:'<span class="badge COMPLETED"><i class="ti ti-circle-check"></i> Completed</span>',
      DEFAULTED:'<span class="badge DEFAULTED"><i class="ti ti-alert-circle"></i> Defaulted</span>',
    };
    return map[status]||`<span class="badge PENDING">${status||'—'}</span>`;
  }

  // ── LOAD REQUESTS ─────────────────────────────────────────────────────────
  async function loadRequests(){
    const el=document.getElementById('requests-list');
    el.innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    try{
      const res=await fetch(API.MY_REQUESTS,{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      document.getElementById('req-count').textContent=list.length;
      if(!list.length){ el.innerHTML='<div class="empty-state"><i class="ti ti-clock-off"></i><p>No loan requests yet.</p><span onclick="switchTab(\'request\')">Submit your first request →</span></div>'; return; }
      el.innerHTML=list.map((r,i)=>renderLoanCard(r,i,'request')).join('');
    } catch { el.innerHTML='<div class="empty-state"><i class="ti ti-alert-circle"></i><p>Failed to load requests.</p></div>'; }
  }

  // ── LOAD LOANS ────────────────────────────────────────────────────────────
  async function loadLoans(){
    const el=document.getElementById('loans-list');
    el.innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    try{
      const res=await fetch(API.MY_LOANS,{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      document.getElementById('loan-count').textContent=list.length;
      if(!list.length){ el.innerHTML='<div class="empty-state"><i class="ti ti-coin-off"></i><p>No active loans.</p><span onclick="switchTab(\'request\')">Apply for a loan →</span></div>'; return; }
      el.innerHTML=list.map((l,i)=>renderLoanCard(l,i,'loan')).join('');
    } catch { el.innerHTML='<div class="empty-state"><i class="ti ti-alert-circle"></i><p>Failed to load loans.</p></div>'; }
  }

  // ── RENDER CARD ───────────────────────────────────────────────────────────
  function renderLoanCard(item,idx,mode){
    const t=item.loan_type||'PERSONAL';
    const badge=statusBadge(item.status);
    const amount=mode==='loan'?item.principal_amount:item.amount;
    const details=mode==='loan'?`
      <div class="detail-cell"><div class="detail-label">Started</div><div class="detail-val">${item.started_at?new Date(item.started_at).toLocaleDateString('en-DE'):'—'}</div></div>
      <div class="detail-cell"><div class="detail-label">Monthly Payment</div><div class="detail-val">€${Number(item.monthly_installment||0).toFixed(2)}</div></div>
      <div class="detail-cell"><div class="detail-label">Total Payable</div><div class="detail-val">€${Number(item.total_payable||0).toLocaleString()}</div></div>
      <div class="detail-cell"><div class="detail-label">Paid</div><div class="detail-val" style="color:var(--success);">€${Number(item.paid_amount||0).toLocaleString()}</div></div>
      <div class="detail-cell"><div class="detail-label">Interest Rate</div><div class="detail-val">${item.interest_rate||'—'}%</div></div>
      <div class="detail-cell"><div class="detail-label">Duration</div><div class="detail-val">${item.duration_months} months</div></div>
    `:`
      <div class="detail-cell"><div class="detail-label">Duration</div><div class="detail-val">${item.duration_months} months</div></div>
      <div class="detail-cell"><div class="detail-label">Monthly Income</div><div class="detail-val">€${Number(item.monthly_income||0).toLocaleString()}</div></div>
      <div class="detail-cell"><div class="detail-label">Existing Debt</div><div class="detail-val">€${Number(item.existing_debt||0).toLocaleString()}</div></div>
      <div class="detail-cell"><div class="detail-label">Submitted</div><div class="detail-val">${item.created_at?new Date(item.created_at).toLocaleDateString('en-DE'):'—'}</div></div>
      <div class="detail-cell"><div class="detail-label">Status</div><div class="detail-val">${badge}</div></div>
      <div class="detail-cell"><div class="detail-label">Manager Note</div><div class="detail-val" style="font-size:12px;">${item.manager_note||'—'}</div></div>
    `;
    const actions=mode==='loan'
      ?`<a class="btn btn-ghost" href="installments.html?loan=${item.id}" style="font-size:12.5px;height:34px;padding:0 12px;"><i class="ti ti-receipt"></i> View Installments</a>`
      :(item.status==='PENDING'?`<button class="btn btn-ghost" style="font-size:12.5px;height:34px;padding:0 12px;color:var(--danger);border-color:var(--danger);" onclick="event.stopPropagation()"><i class="ti ti-trash"></i> Cancel</button>`:'');
    return `
      <div class="loan-card" id="card-${item.id||idx}">
        <div class="loan-card-header" onclick="toggleCard('card-${item.id||idx}')">
          <div class="loan-type-icon ${t}"><i class="ti ${typeIcon[t]||'ti-coin'}"></i></div>
          <div class="loan-card-info">
            <div class="loan-card-title">${typeLabel[t]||'Loan'} ${badge}</div>
            <div class="loan-card-meta">${item.created_at?new Date(item.created_at).toLocaleDateString('en-DE'):'—'} · ${item.duration_months} months</div>
          </div>
          <div class="loan-card-right"><div class="loan-amount-big">€${Number(amount||0).toLocaleString()}</div></div>
          <i class="ti ti-chevron-down loan-chevron"></i>
        </div>
        <div class="loan-details">
          <div class="loan-details-grid">${details}</div>
          ${actions?`<div class="loan-details-actions">${actions}</div>`:''}
        </div>
      </div>`;
  }

  function toggleCard(id){ document.getElementById(id).classList.toggle('open'); }

  document.getElementById('confirm-modal').addEventListener('click',function(e){ if(e.target===this) closeModal(); });

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear();window.location.href='../../auth/auth.html';
  }
