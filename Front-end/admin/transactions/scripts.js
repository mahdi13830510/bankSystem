  const access  = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');
  //if (!access) window.location.href = '../../auth/auth.html';

  const API = {
    LIST:    (q) => `/transactions/admin/?${q}`,
    DETAIL:  (id)=> `/transactions/admin/${id}/`,
    REVERSE: (id)=> `/transactions/admin/${id}/reverse/`,
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

  const typeIcons = {
    CARD_TO_CARD:'ti-credit-card', IBAN_TRANSFER:'ti-building-bank',
    INTERNAL_TRANSFER:'ti-arrows-right-left', CASH_DEPOSIT:'ti-arrow-down-left',
    CASH_WITHDRAW:'ti-arrow-up-right', LOAN_DISBURSEMENT:'ti-coin',
    INSTALLMENT_PAYMENT:'ti-receipt', REFUND:'ti-rotate-clockwise-2',
    LATE_FEE:'ti-alert-circle', LOAN_SETTLEMENT:'ti-check',
  };
  const creditTypes=['CASH_DEPOSIT','LOAN_DISBURSEMENT','REFUND'];

  let currentPage=1, totalCount=0, activeId=null;
  const PAGE=20;

  async function loadTx(page=1){
    currentPage=page;
    const p=new URLSearchParams();
    const ref   =document.getElementById('search-ref').value.trim();
    const type  =document.getElementById('filter-type').value;
    const status=document.getElementById('filter-status').value;
    const from  =document.getElementById('filter-from').value;
    const to    =document.getElementById('filter-to').value;
    if(ref)    p.set('reference_number',ref);
    if(type)   p.set('type',type);
    if(status) p.set('status',status);
    if(from)   p.set('date_from',from);
    if(to)     p.set('date_to',to);

    document.getElementById('table-wrap').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    document.getElementById('pagination').style.display='none';

    try{
      const res=await fetch(API.LIST(p),{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      totalCount=data.count||list.length;
      renderTable(list);
    } catch { renderTable(mockTx()); totalCount=mockTx().length; }
  }

  function renderTable(list){
    document.getElementById('table-count').textContent=`${totalCount} result${totalCount!==1?'s':''}`;
    if(!list.length){
      document.getElementById('table-wrap').innerHTML='<div class="empty-state"><i class="ti ti-arrows-right-left"></i><p>No transactions found.</p></div>';
      return;
    }
    const rows=list.map(t=>{
      const isCredit=creditTypes.includes(t.type);
      const d=new Date(t.created_at);
      return `
        <tr onclick="openDrawer('${t.id}')">
          <td>
            <div style="display:flex;align-items:center;gap:10px;">
              <div style="width:34px;height:34px;border-radius:9px;background:${isCredit?'var(--success-bg)':'var(--danger-bg)'};display:flex;align-items:center;justify-content:center;font-size:16px;color:${isCredit?'var(--success)':'var(--danger)'};flex-shrink:0;">
                <i class="ti ${typeIcons[t.type]||'ti-arrows-right-left'}"></i>
              </div>
              <div>
                <div class="type-label">${(t.type||'').replace(/_/g,' ')}</div>
                <div class="mono" style="color:var(--text-3);">${t.reference_number||'—'}</div>
              </div>
            </div>
          </td>
          <td>${t.account?.customer?.fullname||'—'}</td>
          <td><span class="tx-amount ${isCredit?'credit':'debit'}">${isCredit?'+':'-'}€${Number(t.amount||0).toFixed(2)}</span>${t.fee>0?`<br><span style="font-size:11px;color:var(--text-3);">Fee: €${Number(t.fee).toFixed(2)}</span>`:''}</td>
          <td><span class="badge ${t.status}">${t.status}</span></td>
          <td style="color:var(--text-3);font-size:12px;">${d.toLocaleDateString('en-DE')}<br><span style="font-size:11px;">${d.toLocaleTimeString('en-DE',{hour:'2-digit',minute:'2-digit'})}</span></td>
        </tr>`;
    }).join('');
    document.getElementById('table-wrap').innerHTML=`
      <table>
        <thead><tr><th>Transaction</th><th>Account Holder</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    const pages=Math.ceil(totalCount/PAGE);
    if(pages>1){
      document.getElementById('pagination').style.display='flex';
      document.getElementById('pag-info').textContent=`Page ${currentPage} of ${pages}`;
      let b=`<button class="pag-btn" onclick="loadTx(${currentPage-1})" ${currentPage===1?'disabled':''}><i class="ti ti-chevron-left"></i></button>`;
      for(let i=1;i<=Math.min(pages,7);i++) b+=`<button class="pag-btn ${i===currentPage?'active':''}" onclick="loadTx(${i})">${i}</button>`;
      b+=`<button class="pag-btn" onclick="loadTx(${currentPage+1})" ${currentPage===pages?'disabled':''}><i class="ti ti-chevron-right"></i></button>`;
      document.getElementById('pag-btns').innerHTML=b;
    }
  }

  function resetFilters(){
    ['search-ref','filter-from','filter-to'].forEach(id=>document.getElementById(id).value='');
    ['filter-type','filter-status'].forEach(id=>document.getElementById(id).value='');
    loadTx(1);
  }

  // ── DRAWER ────────────────────────────────────────────────────────────────
  async function openDrawer(id){
    activeId=id;
    document.getElementById('overlay').classList.add('show');
    document.getElementById('tx-drawer').classList.add('open');
    document.getElementById('drawer-body').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    document.getElementById('drawer-footer').innerHTML='';
    try{
      const res=await fetch(API.DETAIL(id),{headers:H()});
      const t=await res.json();
      renderDrawer(t);
    } catch {
      const t=mockTx().find(t=>t.id===id)||mockTx()[0];
      renderDrawer(t);
    }
  }

  function renderDrawer(t){
    const isCredit=creditTypes.includes(t.type);
    const d=new Date(t.created_at);
    document.getElementById('drawer-body').innerHTML=`
      <div style="text-align:center;padding:1.5rem 0 1.75rem;border-bottom:1px solid var(--border);margin-bottom:1.25rem;">
        <div style="width:56px;height:56px;border-radius:14px;background:${isCredit?'var(--success-bg)':'var(--danger-bg)'};display:flex;align-items:center;justify-content:center;font-size:26px;color:${isCredit?'var(--success)':'var(--danger)'};margin:0 auto 12px;">
          <i class="ti ${typeIcons[t.type]||'ti-arrows-right-left'}"></i>
        </div>
        <div style="font-size:12px;color:var(--text-3);margin-bottom:4px;">${(t.type||'').replace(/_/g,' ')}</div>
        <div style="font-family:'DM Serif Display',serif;font-size:36px;color:${isCredit?'var(--success)':'var(--danger)'};">${isCredit?'+':'-'}€${Number(t.amount||0).toFixed(2)}</div>
        <div style="margin-top:8px;"><span class="badge ${t.status}">${t.status}</span></div>
      </div>
      <div class="detail-grid">
        <div class="detail-cell"><div class="detail-label">Reference</div><div class="detail-val" style="font-family:monospace;font-size:12px;">${t.reference_number||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Account Holder</div><div class="detail-val">${t.account?.customer?.fullname||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Account No.</div><div class="detail-val" style="font-family:monospace;font-size:12px;">${t.account?.account_number||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Fee</div><div class="detail-val">€${Number(t.fee||0).toFixed(2)}</div></div>
        <div class="detail-cell"><div class="detail-label">Date</div><div class="detail-val">${d.toLocaleDateString('en-DE')}</div></div>
        <div class="detail-cell"><div class="detail-label">Time</div><div class="detail-val">${d.toLocaleTimeString('en-DE')}</div></div>
        <div class="detail-cell" style="grid-column:1/-1;"><div class="detail-label">Description</div><div class="detail-val">${t.description||'—'}</div></div>
        <div class="detail-cell" style="grid-column:1/-1;"><div class="detail-label">Transaction ID</div><div class="detail-val" style="font-family:monospace;font-size:11px;">${t.id}</div></div>
      </div>`;
    const canReverse = t.status === 'SUCCESS' && !['REFUND','REVERSED'].includes(t.type);
    if(canReverse){
      document.getElementById('drawer-footer').innerHTML=`
        <button class="btn danger" onclick="openReverseModal()"><i class="ti ti-rotate-clockwise-2"></i> Reverse Transaction</button>`;
    } else {
      document.getElementById('drawer-footer').innerHTML=`<span style="font-size:12.5px;color:var(--text-3);">This transaction cannot be reversed.</span>`;
    }
  }

  function closeDrawer(){ document.getElementById('overlay').classList.remove('show'); document.getElementById('tx-drawer').classList.remove('open'); activeId=null; }

  function openReverseModal(){ document.getElementById('reverse-modal').classList.add('show'); }
  function closeReverseModal(){ document.getElementById('reverse-modal').classList.remove('show'); }

  async function confirmReverse(){
    const btn=document.getElementById('reverse-btn'); const spin=document.getElementById('reverse-spin');
    btn.disabled=true; spin.style.display='block';
    try{
      const res=await fetch(API.REVERSE(activeId),{method:'POST',headers:H(),body:'{}'});
      if(res.ok){ toast('Transaction reversed successfully'); closeReverseModal(); closeDrawer(); loadTx(currentPage); }
      else { const d=await res.json(); toast(d.detail||'Failed','error'); }
    } catch { toast('Network error','error'); }
    finally { btn.disabled=false; spin.style.display='none'; }
  }

  document.getElementById('reverse-modal').addEventListener('click',function(e){ if(e.target===this) closeReverseModal(); });
  document.getElementById('search-ref').addEventListener('keydown',e=>{ if(e.key==='Enter') loadTx(1); });

  function mockTx(){
    return [
      {id:'t1',type:'CARD_TO_CARD',    amount:500,   fee:1.5, status:'SUCCESS', reference_number:'TXN2026051400001',account:{account_number:'40000000001',customer:{fullname:'Alice Johnson'}},description:'Transfer to Bob',created_at:'2026-05-14T11:22:00Z'},
      {id:'t2',type:'IBAN_TRANSFER',   amount:1200,  fee:2.0, status:'SUCCESS', reference_number:'TXN2026051300002',account:{account_number:'40000000002',customer:{fullname:'Bob Smith'}},   description:'',          created_at:'2026-05-13T09:10:00Z'},
      {id:'t3',type:'CASH_DEPOSIT',    amount:3200,  fee:0,   status:'SUCCESS', reference_number:'TXN2026051500003',account:{account_number:'40000000001',customer:{fullname:'Alice Johnson'}},description:'Salary',     created_at:'2026-05-15T09:00:00Z'},
      {id:'t4',type:'INSTALLMENT_PAYMENT',amount:380,fee:0,   status:'SUCCESS', reference_number:'TXN2026051000004',account:{account_number:'40000000001',customer:{fullname:'Alice Johnson'}},description:'Inst #15',   created_at:'2026-05-10T08:00:00Z'},
      {id:'t5',type:'CASH_WITHDRAW',   amount:200,   fee:0.5, status:'FAILED',  reference_number:'TXN2026050800005',account:{account_number:'40000000003',customer:{fullname:'Clara Lee'}},   description:'ATM',        created_at:'2026-05-08T15:30:00Z'},
      {id:'t6',type:'LOAN_DISBURSEMENT',amount:8000, fee:0,   status:'SUCCESS', reference_number:'TXN2026042500006',account:{account_number:'40000000004',customer:{fullname:'David Park'}},  description:'Loan payout',created_at:'2026-04-25T10:00:00Z'},
    ];
  }

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear(); window.location.href='../../auth/auth.html';
  }

  loadTx(1);
