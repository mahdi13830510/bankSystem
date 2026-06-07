  // ── ENDPOINTS ─────────────────────────────────────────────────────────────
  // GET /api/transactions/statement/<account_id>/
  const accountId = localStorage.getItem('account_id') || '1';
  const API = {
    STATEMENT: `/api/transactions/statement/${accountId}/`,
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

  // ── STATE ─────────────────────────────────────────────────────────────────
  let allTx=[], filteredTx=[], currentType='all', currentPage=1;
  const PAGE_SIZE=15;

  // ── CREDIT TYPES (income side) ────────────────────────────────────────────
  const creditTypes=['CASH_DEPOSIT','LOAN_DISBURSEMENT','REFUND'];
  const transferTypes=['CARD_TO_CARD','IBAN_TRANSFER','INTERNAL_TRANSFER'];

  function txCategory(tx){
    if(creditTypes.includes(tx.type)) return 'income';
    if(transferTypes.includes(tx.type)) return 'transfer';
    return 'expense';
  }

  const typeIcons={
    CARD_TO_CARD:'ti-credit-card',IBAN_TRANSFER:'ti-building-bank',
    INTERNAL_TRANSFER:'ti-arrows-right-left',CASH_DEPOSIT:'ti-arrow-down-left',
    CASH_WITHDRAW:'ti-arrow-up-right',LOAN_DISBURSEMENT:'ti-coin',
    INSTALLMENT_PAYMENT:'ti-receipt',REFUND:'ti-rotate-clockwise-2',
    LATE_FEE:'ti-alert-circle',
  };

  // ── LOAD ──────────────────────────────────────────────────────────────────
  async function loadStatement(){
    try{
      const res=await fetch(API.STATEMENT,{headers:H()});
      if(!res.ok) throw new Error();
      const data=await res.json();
      allTx=Array.isArray(data)?data:(data.results||data.transactions||[]);
    } catch { allTx=[]; }
    applyFilters();
  }

  // ── FILTERS ───────────────────────────────────────────────────────────────
  function applyFilters(){
    const from=document.getElementById('filter-from').value;
    const to  =document.getElementById('filter-to').value;
    filteredTx=allTx.filter(tx=>{
      const date=new Date(tx.created_at);
      if(from && date<new Date(from)) return false;
      if(to   && date>new Date(to+'T23:59:59')) return false;
      if(currentType!=='all' && txCategory(tx)!==currentType) return false;
      return true;
    });
    currentPage=1;
    updateStats();
    renderTable();
  }

  function resetFilters(){
    document.getElementById('filter-from').value=defaultFrom();
    document.getElementById('filter-to').value=new Date().toISOString().slice(0,10);
    currentType='all';
    document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
    document.getElementById('pill-all').classList.add('active');
    applyFilters();
  }

  function setTypePill(type,btn){
    currentType=type;
    document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    applyFilters();
  }

  function defaultFrom(){
    const d=new Date(); d.setMonth(d.getMonth()-3);
    return d.toISOString().slice(0,10);
  }

  // ── STATS ─────────────────────────────────────────────────────────────────
  function fmt(n){ return '€'+Number(n||0).toLocaleString(undefined,{minimumFractionDigits:2}); }

  function updateStats(){
    const income  = filteredTx.filter(t=>txCategory(t)==='income').reduce((s,t)=>s+Number(t.amount),0);
    const expense = filteredTx.filter(t=>txCategory(t)==='expense').reduce((s,t)=>s+Number(t.amount),0);
    const net=income-expense;
    document.getElementById('stat-total').textContent   = filteredTx.length;
    document.getElementById('stat-income').textContent  = fmt(income);
    document.getElementById('stat-expense').textContent = fmt(expense);
    const netEl=document.getElementById('stat-net');
    netEl.textContent=(net>=0?'+':'')+fmt(Math.abs(net));
    netEl.className='strip-val '+(net>=0?'green':'red');
  }

  // ── RENDER TABLE ──────────────────────────────────────────────────────────
  function renderTable(){
    const wrap=document.getElementById('table-wrap');
    document.getElementById('table-count').textContent=`${filteredTx.length} result${filteredTx.length!==1?'s':''}`;

    if(!filteredTx.length){
      wrap.innerHTML='<div class="empty-state"><i class="ti ti-file-off"></i><p>No transactions match your filters.</p></div>';
      document.getElementById('pagination').style.display='none';
      return;
    }

    const totalPages=Math.ceil(filteredTx.length/PAGE_SIZE);
    const start=(currentPage-1)*PAGE_SIZE;
    const page=filteredTx.slice(start,start+PAGE_SIZE);

    const rows=page.map(tx=>{
      const cat=txCategory(tx);
      const sign=cat==='income'?'+':'-';
      const d=new Date(tx.created_at);
      const statusBadge=tx.status==='SUCCESS'
        ?'<span class="badge SUCCESS"><i class="ti ti-circle-check"></i> Completed</span>'
        :tx.status==='PENDING'
        ?'<span class="badge PENDING"><i class="ti ti-clock"></i> Pending</span>'
        :tx.status==='REVERSED'
        ?'<span class="badge REVERSED"><i class="ti ti-rotate-clockwise-2"></i> Reversed</span>'
        :'<span class="badge FAILED"><i class="ti ti-circle-x"></i> Failed</span>';
      return `
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:12px;">
              <div class="tx-type-icon ${cat}"><i class="ti ${typeIcons[tx.type]||'ti-arrows-right-left'}"></i></div>
              <div>
                <div class="tx-desc">${tx.description||tx.type?.replace(/_/g,' ')||'Transaction'}</div>
                <div class="tx-ref">${tx.reference_number||'—'}</div>
              </div>
            </div>
          </td>
          <td>
            <div style="font-size:13px;color:var(--text-2);">${d.toLocaleDateString('en-DE',{day:'2-digit',month:'short',year:'numeric'})}</div>
            <div style="font-size:11px;color:var(--text-3);">${d.toLocaleTimeString('en-DE',{hour:'2-digit',minute:'2-digit'})}</div>
          </td>
          <td>${statusBadge}</td>
          <td class="right"><span class="tx-amount ${cat}">${sign}${fmt(tx.amount)}</span>${tx.fee>0?`<br><span style="font-size:11px;color:var(--text-3);">Fee: ${fmt(tx.fee)}</span>`:''}</td>
        </tr>`;
    }).join('');

    wrap.innerHTML=`
      <table>
        <thead><tr><th>Transaction</th><th>Date</th><th>Status</th><th class="right">Amount</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;

    // Pagination
    const pagEl=document.getElementById('pagination');
    if(totalPages>1){
      pagEl.style.display='flex';
      document.getElementById('pag-info').textContent=`Showing ${start+1}–${Math.min(start+PAGE_SIZE,filteredTx.length)} of ${filteredTx.length}`;
      let b=`<button class="pag-btn" onclick="goPage(${currentPage-1})" ${currentPage===1?'disabled':''}><i class="ti ti-chevron-left"></i></button>`;
      for(let i=1;i<=totalPages;i++){
        if(totalPages<=7||i===1||i===totalPages||Math.abs(i-currentPage)<=1)
          b+=`<button class="pag-btn ${i===currentPage?'active':''}" onclick="goPage(${i})">${i}</button>`;
        else if(Math.abs(i-currentPage)===2)
          b+=`<button class="pag-btn" disabled style="border:none;">…</button>`;
      }
      b+=`<button class="pag-btn" onclick="goPage(${currentPage+1})" ${currentPage===totalPages?'disabled':''}><i class="ti ti-chevron-right"></i></button>`;
      document.getElementById('pag-btns').innerHTML=b;
    } else { pagEl.style.display='none'; }
  }

  function goPage(p){
    const total=Math.ceil(filteredTx.length/PAGE_SIZE);
    if(p<1||p>total) return;
    currentPage=p;
    renderTable();
    document.querySelector('.table-card').scrollIntoView({behavior:'smooth',block:'start'});
  }

  // ── PDF EXPORT ────────────────────────────────────────────────────────────
  function exportPDF(){
    const btn=document.getElementById('export-btn');
    btn.disabled=true; btn.innerHTML='<i class="ti ti-loader-2"></i> Generating…';
    document.getElementById('pdf-date').textContent=new Date().toLocaleString('en-DE',{dateStyle:'long',timeStyle:'short'});

    // Render all rows without pagination for print
    const allRows=filteredTx.map(tx=>{
      const cat=txCategory(tx);
      const sign=cat==='income'?'+':'-';
      const d=new Date(tx.created_at);
      return `<tr>
        <td>${tx.description||tx.type?.replace(/_/g,' ')||'—'}</td>
        <td>${tx.reference_number||'—'}</td>
        <td>${d.toLocaleDateString('en-DE')}</td>
        <td>${tx.type?.replace(/_/g,' ')||'—'}</td>
        <td>${tx.status||'—'}</td>
        <td style="text-align:right;font-weight:700;">${sign}${fmt(tx.amount)}</td>
      </tr>`;
    }).join('');

    document.getElementById('table-wrap').innerHTML=`
      <table>
        <thead><tr><th>Description</th><th>Reference</th><th>Date</th><th>Type</th><th>Status</th><th class="right">Amount</th></tr></thead>
        <tbody>${allRows}</tbody>
      </table>`;
    document.getElementById('pagination').style.display='none';

    setTimeout(()=>{
      window.print();
      setTimeout(()=>{
        renderTable();
        btn.disabled=false;
        btn.innerHTML='<i class="ti ti-file-type-pdf"></i> Export PDF';
        toast('Statement exported successfully!');
      },600);
    },300);
  }

  // ── INIT ──────────────────────────────────────────────────────────────────
  document.getElementById('filter-to').value  = new Date().toISOString().slice(0,10);
  document.getElementById('filter-from').value = defaultFrom();

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear();window.location.href='../../auth/auth.html';
  }

  loadStatement();
