  // ── ENDPOINTS ─────────────────────────────────────────────────────────────
  const API = {
    MY:        '/installments/my/',
    PAY:       (id) => `/installments/${id}/pay/`,
    REMAINING: (lid) => `/installments/loan/${lid}/remaining/`,
    LOGOUT:    '/api/v1/auth/logout/',
  };

  const access  = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');
  //if (!access) window.location.href = '../../auth/auth.html';
  const H = () => ({ 'Content-Type':'application/json','Authorization':`Bearer ${access}` });

  const userName = localStorage.getItem('user_name')||'';
  document.getElementById('sidebar-name').textContent = userName||'My Account';
  document.getElementById('sidebar-avatar').textContent = userName?userName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase():'U';

  function toast(msg,type='success'){
    const el=document.createElement('div');el.className=`toast ${type}`;
    el.innerHTML=`<i class="ti ti-${type==='success'?'circle-check':'alert-circle'}"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);setTimeout(()=>el.remove(),4000);
  }

  let allInstallments=[];
  let activePayId=null;

  // ── LOAD ──────────────────────────────────────────────────────────────────
  async function loadInstallments(){
    try{
      const res=await fetch(API.MY,{headers:H()});
      const data=await res.json();
      allInstallments=Array.isArray(data)?data:(data.results||[]);
    } catch { allInstallments=[]; }
    renderAll();
    await loadRemainingForGroups();
  }

  function isOverdue(i){ return i.status==='OVERDUE'||(i.status!=='PAID'&&new Date(i.due_date)<new Date()); }

  function statusBadge(i){
    const ov=isOverdue(i)&&i.status!=='PAID';
    if(i.status==='PAID')    return '<span class="badge PAID"><i class="ti ti-circle-check"></i> Paid</span>';
    if(ov)                   return '<span class="badge OVERDUE"><i class="ti ti-alert-triangle"></i> Overdue</span>';
    if(i.status==='PARTIAL') return '<span class="badge PARTIAL"><i class="ti ti-adjustments"></i> Partial</span>';
    return '<span class="badge PENDING"><i class="ti ti-clock"></i> Pending</span>';
  }

  const typeIcon ={HOME:'ti-home',CAR:'ti-car',BUSINESS:'ti-briefcase',PERSONAL:'ti-user'};
  const typeLabel={HOME:'Home Loan',CAR:'Car Loan',BUSINESS:'Business Loan',PERSONAL:'Personal Loan'};

  // ── RENDER ────────────────────────────────────────────────────────────────
  function renderAll(){
    const total   = allInstallments.length;
    const paid    = allInstallments.filter(i=>i.status==='PAID').length;
    const overdue = allInstallments.filter(i=>isOverdue(i)).length;
    const pending = total-paid-overdue;
    document.getElementById('stat-total').textContent   = total;
    document.getElementById('stat-paid').textContent    = paid;
    document.getElementById('stat-pending').textContent = Math.max(0,pending);
    document.getElementById('stat-overdue').textContent = overdue;

    // Group by loan id
    const groups={};
    allInstallments.forEach(inst=>{
      const lid=inst.loan?.id||inst.loan||'unknown';
      if(!groups[lid]) groups[lid]={loan:inst.loan,items:[]};
      groups[lid].items.push(inst);
    });

    const container=document.getElementById('groups-container');
    if(!Object.keys(groups).length){
      container.innerHTML='<div class="empty-state"><i class="ti ti-receipt-off"></i><p>No installments found.</p></div>';
      return;
    }

    container.innerHTML=Object.entries(groups).map(([lid,group],gi)=>{
      const items=group.items.sort((a,b)=>a.number-b.number);
      const loan=group.loan||{};
      const t=loan.loan_type||loan.type||'PERSONAL';
      const lTotal=items.length;
      const lPaid=items.filter(i=>i.status==='PAID').length;
      const pct=Math.round((lPaid/lTotal)*100);
      const hasOverdue=items.some(i=>isOverdue(i));
      const nextDue=items.find(i=>i.status!=='PAID');

      const rows=items.map(inst=>{
        const ov=isOverdue(inst);
        const canPay=inst.status!=='PAID';
        const total=Number(inst.amount||0)+Number(inst.penalty_amount||0);
        return `
          <tr id="row-${inst.id}">
            <td><span class="td-number">${inst.number}</span></td>
            <td>${inst.due_date||'—'}${ov&&inst.status!=='PAID'?'<br><span style="font-size:11px;color:var(--danger);font-weight:600;">OVERDUE</span>':''}</td>
            <td><span class="td-amount">€${Number(inst.amount||0).toFixed(2)}</span>${Number(inst.penalty_amount||0)>0?`<span class="td-penalty">+€${Number(inst.penalty_amount).toFixed(2)} penalty</span>`:''}</td>
            <td>${statusBadge(inst)}</td>
            <td style="font-size:12px;color:var(--text-3);">${inst.paid_at?new Date(inst.paid_at).toLocaleDateString('en-DE'):'—'}</td>
            <td>${canPay
              ?`<button class="pay-btn ${ov?'overdue':''}" onclick="openPayModal('${inst.id}',${inst.number},'${inst.due_date}',${inst.amount},${inst.penalty_amount||0})"><i class="ti ti-credit-card"></i> Pay</button>`
              :`<i class="ti ti-circle-check paid-check" title="Paid ${inst.paid_at?new Date(inst.paid_at).toLocaleDateString('en-DE'):''}"></i>`
            }</td>
          </tr>`;
      }).join('');

      return `
        <div class="loan-group${gi===0?' open':''}" id="group-${lid}">
          <div class="loan-group-header" onclick="toggleGroup('group-${lid}')">
            <div class="loan-group-icon ${t}"><i class="ti ${typeIcon[t]||'ti-coin'}"></i></div>
            <div class="loan-group-info">
              <div class="loan-group-title">${typeLabel[t]||'Loan'} ${hasOverdue?'<span class="badge OVERDUE" style="font-size:10px;margin-left:6px;"><i class="ti ti-alert-triangle"></i> Overdue</span>':''}</div>
              <div class="group-progress">
                <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
                <div class="progress-label">${lPaid} of ${lTotal} paid · ${pct}%${nextDue?' · Next due: '+nextDue.due_date:''}</div>
              </div>
            </div>
            <div class="loan-group-stats">
              <div class="lg-stat"><div class="lg-stat-label">Remaining</div><div class="lg-stat-val accent" id="remaining-${lid}">—</div></div>
            </div>
            <i class="ti ti-chevron-down group-chevron"></i>
          </div>
          <div class="inst-table-wrap">
            <table>
              <thead><tr><th>#</th><th>Due Date</th><th>Amount</th><th>Status</th><th>Paid At</th><th>Action</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
            <div class="remaining-footer">
              <div><div class="remaining-label">Total Remaining Balance</div><div class="remaining-sub">Including all pending installments</div></div>
              <div class="remaining-val" id="remaining-footer-${lid}">—</div>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  // ── REMAINING ─────────────────────────────────────────────────────────────
  async function loadRemainingForGroups(){
    const groups={};
    allInstallments.forEach(inst=>{ const lid=inst.loan?.id||inst.loan||'unknown'; groups[lid]=true; });
    await Promise.all(Object.keys(groups).map(async lid=>{
      try{
        const res=await fetch(API.REMAINING(lid),{headers:H()});
        const data=await res.json();
        const val=data.remaining_amount??data.remaining??null;
        if(val!==null){
          const fmt='€'+Number(val).toLocaleString(undefined,{minimumFractionDigits:2});
          const e1=document.getElementById(`remaining-${lid}`);
          const e2=document.getElementById(`remaining-footer-${lid}`);
          if(e1) e1.textContent=fmt;
          if(e2) e2.textContent=fmt;
        }
      } catch{ /* silent */ }
    }));
  }

  function toggleGroup(id){ document.getElementById(id).classList.toggle('open'); }

  // ── PAY MODAL ─────────────────────────────────────────────────────────────
  function openPayModal(id,number,dueDate,amount,penalty){
    activePayId=id;
    const total=Number(amount)+Number(penalty);
    document.getElementById('m-number').textContent=`#${number}`;
    document.getElementById('m-due').textContent=dueDate;
    document.getElementById('m-amount').textContent=`€${Number(amount).toFixed(2)}`;
    document.getElementById('m-penalty').textContent=`€${Number(penalty).toFixed(2)}`;
    document.getElementById('m-total').textContent=`€${total.toFixed(2)}`;
    document.getElementById('m-penalty-row').style.display=Number(penalty)>0?'flex':'none';
    document.getElementById('pay-modal').classList.add('show');
  }
  function closeModal(){ document.getElementById('pay-modal').classList.remove('show'); activePayId=null; }

  async function confirmPay(){
    if(!activePayId) return;
    const btn=document.getElementById('pay-confirm-btn');
    const spin=document.getElementById('pay-spin');
    const icon=document.getElementById('pay-icon');
    const txt=document.getElementById('pay-text');
    btn.disabled=true;spin.style.display='block';icon.style.display='none';txt.textContent='Processing…';
    try{
      const res=await fetch(API.PAY(activePayId),{method:'POST',headers:H()});
      const data=await res.json();
      if(res.ok){
        closeModal();
        toast('Payment successful!');
        const idx=allInstallments.findIndex(i=>i.id===activePayId);
        if(idx!==-1){ allInstallments[idx].status='PAID'; allInstallments[idx].paid_at=new Date().toISOString(); }
        renderAll();
        await loadRemainingForGroups();
      } else { closeModal(); toast(data.detail||data.message||'Payment failed.','error'); }
    } catch { closeModal(); toast('Network error.','error'); }
    finally { btn.disabled=false;spin.style.display='none';icon.style.display='';txt.textContent='Pay Now'; }
  }

  document.getElementById('pay-modal').addEventListener('click',function(e){ if(e.target===this) closeModal(); });

  // Check if arriving from loan page with ?loan= param
  const params=new URLSearchParams(window.location.search);
  const focusLoan=params.get('loan');

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear();window.location.href='../../auth/auth.html';
  }

  loadInstallments().then(()=>{
    if(focusLoan){
      const el=document.getElementById(`group-${focusLoan}`);
      if(el){ el.classList.add('open'); el.scrollIntoView({behavior:'smooth',block:'start'}); }
    }
  });
