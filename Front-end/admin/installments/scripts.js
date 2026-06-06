  const access=localStorage.getItem('access_token');
  const refresh=localStorage.getItem('refresh_token');
  //if(!access) window.location.href='/auth/auth.html';
  const API={
    OVERDUE:'/installments/admin/overdue/',
    ALL:(q)=>`/installments/admin/?${q}`,
    DETAIL:(id)=>`/installments/admin/${id}/`,
    PENALTY:(id)=>`/installments/admin/${id}/penalty/`,
    LOGOUT:'/api/v1/auth/logout/',
  };
  const H=()=>({'Content-Type':'application/json','Authorization':`Bearer ${access}`});
  const adminName=localStorage.getItem('user_name')||'Admin';
  document.getElementById('sidebar-name').textContent=adminName;
  document.getElementById('sidebar-avatar').textContent=adminName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()||'AD';

  function toast(msg,type='success'){
    const el=document.createElement('div');el.className=`toast ${type}`;
    el.innerHTML=`<i class="ti ti-${type==='success'?'circle-check':'alert-circle'}"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);setTimeout(()=>el.remove(),4000);
  }

  const tabs=['overdue','all'];
  function switchTab(tab){
    tabs.forEach(t=>{document.getElementById('tab-'+t).classList.toggle('active',t===tab);document.getElementById('panel-'+t).classList.toggle('active',t===tab);});
    if(tab==='overdue') loadOverdue();
    if(tab==='all')     loadAll();
  }

  function instRows(list,wrap,cntEl,cntLbl){
    document.getElementById(cntEl).textContent=list.length;
    document.getElementById(cntLbl).textContent=`${list.length} installment${list.length!==1?'s':''}`;
    if(!list.length){document.getElementById(wrap).innerHTML='<div class="empty-state"><i class="ti ti-receipt-off"></i><p>No installments found.</p></div>';return;}
    document.getElementById(wrap).innerHTML=`<table>
      <thead><tr><th>#</th><th>Customer</th><th>Due Date</th><th>Amount</th><th>Penalty</th><th>Status</th><th>Paid At</th></tr></thead>
      <tbody>${list.map(i=>`
        <tr onclick="openDrawer('${i.id}')">
          <td style="font-weight:700;">${i.number}</td>
          <td>${i.loan?.customer?.fullname||'—'}</td>
          <td style="font-weight:500;">${i.due_date||'—'}${new Date(i.due_date)<new Date()&&i.status!=='PAID'?'<br><span style="font-size:11px;color:var(--danger);font-weight:600;">OVERDUE</span>':''}</td>
          <td style="font-weight:600;">€${Number(i.amount||0).toFixed(2)}</td>
          <td>${Number(i.penalty_amount||0)>0?`<span style="color:var(--danger);font-weight:600;">€${Number(i.penalty_amount).toFixed(2)}</span>`:'—'}</td>
          <td><span class="badge ${i.status}">${i.status}</span></td>
          <td style="font-size:12px;color:var(--text-3);">${i.paid_at?new Date(i.paid_at).toLocaleDateString('en-DE'):'—'}</td>
        </tr>`).join('')}
      </tbody></table>`;
  }

  async function loadOverdue(){
    document.getElementById('overdue-wrap').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    try{
      const res=await fetch(API.OVERDUE,{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      instRows(list,'overdue-wrap','cnt-overdue','cnt-overdue-lbl');
    } catch { instRows(mockInst().filter(i=>i.status==='OVERDUE'),'overdue-wrap','cnt-overdue','cnt-overdue-lbl'); }
  }

  async function loadAll(){
    document.getElementById('all-wrap').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    const p=new URLSearchParams();
    const s=document.getElementById('filter-status').value;
    const f=document.getElementById('filter-from').value;
    const t=document.getElementById('filter-to').value;
    if(s) p.set('status',s); if(f) p.set('due_date_from',f); if(t) p.set('due_date_to',t);
    try{
      const res=await fetch(API.ALL(p),{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      instRows(list,'all-wrap','cnt-all','cnt-all-lbl');
    } catch { instRows(mockInst(),'all-wrap','cnt-all','cnt-all-lbl'); }
  }

  function resetFilters(){
    document.getElementById('filter-status').value='';
    document.getElementById('filter-from').value='';
    document.getElementById('filter-to').value='';
    loadAll();
  }

  let activeId=null;
  async function openDrawer(id){
    activeId=id;
    document.getElementById('overlay').classList.add('show');
    document.getElementById('inst-drawer').classList.add('open');
    document.getElementById('drawer-body').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    document.getElementById('drawer-footer').innerHTML='';
    try{
      const res=await fetch(API.DETAIL(id),{headers:H()});
      const i=await res.json();
      renderDrawer(i);
    } catch { renderDrawer(mockInst().find(i=>i.id===id)||mockInst()[0]); }
  }

  function renderDrawer(i){
    const total=(Number(i.amount||0)+Number(i.penalty_amount||0)).toFixed(2);
    document.getElementById('drawer-body').innerHTML=`
      <div style="text-align:center;padding:1rem 0 1.5rem;border-bottom:1px solid var(--border);margin-bottom:1.25rem;">
        <div style="font-size:13px;color:var(--text-3);margin-bottom:6px;">Installment #${i.number}</div>
        <div style="font-family:'DM Serif Display',serif;font-size:34px;color:var(--navy);">€${total}</div>
        <div style="margin-top:8px;"><span class="badge ${i.status}">${i.status}</span></div>
      </div>
      <div class="detail-grid">
        <div class="detail-cell"><div class="detail-label">Customer</div><div class="detail-val">${i.loan?.customer?.fullname||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Due Date</div><div class="detail-val">${i.due_date||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Base Amount</div><div class="detail-val">€${Number(i.amount||0).toFixed(2)}</div></div>
        <div class="detail-cell"><div class="detail-label">Penalty</div><div class="detail-val" style="color:var(--danger);">€${Number(i.penalty_amount||0).toFixed(2)}</div></div>
        <div class="detail-cell"><div class="detail-label">Paid Amount</div><div class="detail-val" style="color:var(--success);">€${Number(i.paid_amount||0).toFixed(2)}</div></div>
        <div class="detail-cell"><div class="detail-label">Paid At</div><div class="detail-val">${i.paid_at?new Date(i.paid_at).toLocaleString('en-DE'):'Not paid'}</div></div>
        <div class="detail-cell"><div class="detail-label">Loan ID</div><div class="detail-val" style="font-size:11px;font-family:monospace;">${i.loan?.id||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Created</div><div class="detail-val">${i.created_at?new Date(i.created_at).toLocaleDateString('en-DE'):'—'}</div></div>
      </div>`;
    if(i.status!=='PAID'){
      document.getElementById('drawer-footer').innerHTML=`<button class="btn danger" onclick="openPenaltyModal()"><i class="ti ti-alert-circle"></i> Apply Penalty</button>`;
    } else {
      document.getElementById('drawer-footer').innerHTML=`<span style="font-size:12.5px;color:var(--text-3);">This installment has been paid.</span>`;
    }
  }

  function closeDrawer(){document.getElementById('overlay').classList.remove('show');document.getElementById('inst-drawer').classList.remove('open');activeId=null;}
  function openPenaltyModal(){document.getElementById('penalty-modal').classList.add('show');}
  function closePenaltyModal(){document.getElementById('penalty-modal').classList.remove('show');}

  async function confirmPenalty(){
    const amount=parseFloat(document.getElementById('penalty-amount').value);
    if(!amount||amount<=0){toast('Enter a valid penalty amount','error');return;}
    const btn=document.getElementById('penalty-btn');const spin=document.getElementById('penalty-spin');
    btn.disabled=true;spin.style.display='block';
    try{
      const res=await fetch(API.PENALTY(activeId),{method:'POST',headers:H(),body:JSON.stringify({amount})});
      if(res.ok){toast('Penalty applied successfully');closePenaltyModal();closeDrawer();loadOverdue();}
      else{const d=await res.json();toast(d.detail||'Failed','error');}
    } catch{toast('Network error','error');}
    finally{btn.disabled=false;spin.style.display='none';document.getElementById('penalty-amount').value='';}
  }

  document.getElementById('penalty-modal').addEventListener('click',function(e){if(e.target===this)closePenaltyModal();});

  function mockInst(){
    return [
      {id:'i1',number:8, loan:{id:'l1',customer:{fullname:'Alice Johnson'}},due_date:'2026-05-15',amount:380,paid_amount:0,  penalty_amount:19,  status:'OVERDUE', paid_at:null,         created_at:'2025-01-15T00:00:00Z'},
      {id:'i2',number:9, loan:{id:'l1',customer:{fullname:'Alice Johnson'}},due_date:'2026-06-15',amount:380,paid_amount:0,  penalty_amount:0,   status:'PENDING', paid_at:null,         created_at:'2025-01-15T00:00:00Z'},
      {id:'i3',number:7, loan:{id:'l1',customer:{fullname:'Alice Johnson'}},due_date:'2026-04-15',amount:380,paid_amount:380,penalty_amount:0,   status:'PAID',    paid_at:'2026-04-14T08:00:00Z',created_at:'2025-01-15T00:00:00Z'},
      {id:'i4',number:3, loan:{id:'l2',customer:{fullname:'Bob Smith'}},   due_date:'2026-05-01',amount:870,paid_amount:0,  penalty_amount:43.5,status:'OVERDUE', paid_at:null,         created_at:'2025-10-01T00:00:00Z'},
    ];
  }

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear();window.location.href='/auth/auth.html';
  }

  loadOverdue();
