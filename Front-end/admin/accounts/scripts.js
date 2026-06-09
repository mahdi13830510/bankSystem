const access  = localStorage.getItem('access_token');
const refresh = localStorage.getItem('refresh_token');
if (!access) window.location.href = '../../auth/auth.html';

const API = {
  LIST:    (q)  => `/accounts/admin/?${q}`,
  DETAIL:  (id) => `/accounts/admin/${id}/`,
  STATS:         `/accounts/admin/stats/`,
  DEPOSIT: (id) => `/accounts/${id}/deposit/`,
  WITHDRAW:(id) => `/accounts/${id}/withdraw/`,
  FREEZE:  (id) => `/accounts/${id}/freeze/`,
  ACTIVATE:(id) => `/accounts/${id}/activate/`,
  CLOSE:   (id) => `/accounts/${id}/close/`,
  BLK_BAL: (id) => `/accounts/admin/${id}/block-balance/`,
  UBLK_BAL:(id) => `/accounts/admin/${id}/unblock-balance/`,
  SET_PRI: (id) => `/accounts/admin/${id}/set-primary/`,
  LOGOUT:        `/api/v1/auth/logout/`,
};
const H = () => ({ 'Content-Type':'application/json','Authorization':`Bearer ${access}` });

const adminName = localStorage.getItem('user_name')||'Admin';
document.getElementById('sidebar-name').textContent = adminName;
document.getElementById('sidebar-avatar').textContent = adminName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()||'AD';

function toast(msg,type='success'){
  const el=document.createElement('div'); el.className=`toast ${type}`;
  el.innerHTML=`<i class="ti ti-${type==='success'?'circle-check':'alert-circle'}"></i> ${msg}`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(()=>el.remove(),4000);
}

function fmt(n){ const v=Number(n||0); return v>=1e6?'€'+(v/1e6).toFixed(2)+'M':v>=1e3?'€'+(v/1e3).toFixed(1)+'K':'€'+v.toLocaleString(undefined,{minimumFractionDigits:2}); }

let currentPage=1, totalCount=0, activeId=null, activeAction=null;

// ── STATS ─────────────────────────────────────────────────────────────────
async function loadStats(){
  try{
    const res=await fetch(API.STATS,{headers:H()});
    const d=await res.json();
    document.getElementById('stat-total').textContent   = (d.total_accounts||0).toLocaleString();
    document.getElementById('stat-balance').textContent = fmt(d.total_balance);
    document.getElementById('stat-blocked').textContent = fmt(d.total_blocked_balance);
    document.getElementById('stat-closed').textContent  = (d.by_status?.CLOSED||0).toLocaleString();
  } catch {
    document.getElementById('stat-total').textContent   = '—';
    document.getElementById('stat-balance').textContent = '—';
    document.getElementById('stat-blocked').textContent = '—';
    document.getElementById('stat-closed').textContent  = '—';
  }
}

// ── LIST ──────────────────────────────────────────────────────────────────
async function loadAccounts(page=1){
  currentPage=page;
  const p=new URLSearchParams();
  const s=document.getElementById('search').value.trim();
  const status=document.getElementById('filter-status').value;
  const type  =document.getElementById('filter-type').value;
  const curr  =document.getElementById('filter-currency').value;
  if(s)      p.set('search',s);
  if(status) p.set('status',status);
  if(type)   p.set('type',type);
  if(curr)   p.set('currency',curr);

  document.getElementById('table-wrap').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
  document.getElementById('pagination').style.display='none';

  try{
    const res=await fetch(API.LIST(p.toString()),{headers:H()});
    const data=await res.json();
    const list=Array.isArray(data)?data:(data.results||[]);
    totalCount=data.count||list.length;
    renderTable(list);
  } catch {
    const mock=Array.from({length:8},(_,i)=>({
      id:i+1,
      account_number:`4000000000${10+i}`,
      iban:`DE89370400440532013${i}00`,
      type:['SAVING','CURRENT','BUSINESS','SAVING','CURRENT','SAVING','BUSINESS','CURRENT'][i],
      currency:['EUR','EUR','USD','TRY','EUR','EUR','USD','EUR'][i],
      balance:[12480,3200,45000,8000,1500,22000,900,5600][i],
      blocked_balance:[0,0,500,0,0,1000,0,0][i],
      status:['ACTIVE','ACTIVE','ACTIVE','BLOCKED','ACTIVE','ACTIVE','CLOSED','ACTIVE'][i],
      is_primary:[true,false,false,false,true,false,false,true][i],
      customer:{fullname:['Alice Johnson','Bob Smith','Clara Lee','David Park','Eva Müller','Frank Berg','Grace Kim','Hassan Ali'][i]},
      created_at:new Date(Date.now()-i*864e5*20).toISOString(),
    }));
    totalCount=mock.length;
    renderTable(mock);
  }
}

function renderTable(list){
  document.getElementById('table-count').textContent=`${totalCount} result${totalCount!==1?'s':''}`;
  if(!list.length){
    document.getElementById('table-wrap').innerHTML='<div class="empty-state"><i class="ti ti-wallet-off"></i><p>No accounts found.</p></div>';
    return;
  }
  const rows=list.map(a=>`
    <tr onclick="openDrawer(${a.id})">
      <td><span class="mono">${a.account_number}</span>${a.is_primary?'<span class="badge primary" style="margin-left:6px;">Primary</span>':''}</td>
      <td><span class="mono" style="font-size:11.5px;">${a.iban||'—'}</span></td>
      <td>${a.customer?.fullname||'—'}</td>
      <td><span class="badge ${a.type}">${a.type}</span></td>
      <td>${a.currency}</td>
      <td style="font-weight:600;">${fmt(a.balance)}</td>
      <td><span class="badge ${a.status}">${a.status}</span></td>
      <td style="color:var(--text-3);font-size:12px;">${a.created_at?new Date(a.created_at).toLocaleDateString('en-DE'):'—'}</td>
    </tr>`).join('');
  document.getElementById('table-wrap').innerHTML=`
    <table>
      <thead><tr><th>Account No.</th><th>IBAN</th><th>Customer</th><th>Type</th><th>Currency</th><th>Balance</th><th>Status</th><th>Created</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  const pages=Math.ceil(totalCount/20);
  if(pages>1){
    document.getElementById('pagination').style.display='flex';
    document.getElementById('pag-info').textContent=`Page ${currentPage} of ${pages}`;
    let b=`<button class="pag-btn" onclick="loadAccounts(${currentPage-1})" ${currentPage===1?'disabled':''}><i class="ti ti-chevron-left"></i></button>`;
    for(let i=1;i<=Math.min(pages,7);i++) b+=`<button class="pag-btn ${i===currentPage?'active':''}" onclick="loadAccounts(${i})">${i}</button>`;
    b+=`<button class="pag-btn" onclick="loadAccounts(${currentPage+1})" ${currentPage===pages?'disabled':''}><i class="ti ti-chevron-right"></i></button>`;
    document.getElementById('pag-btns').innerHTML=b;
  }
}

function resetFilters(){
  ['search','filter-status','filter-type','filter-currency'].forEach(id=>{
    const el=document.getElementById(id); el.tagName==='INPUT'?el.value='':el.value='';
  });
  loadAccounts(1);
}

// ── DRAWER ────────────────────────────────────────────────────────────────
async function openDrawer(id){
  activeId=id;
  document.getElementById('overlay').classList.add('show');
  document.getElementById('acct-drawer').classList.add('open');
  document.getElementById('drawer-body').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
  document.getElementById('drawer-footer').innerHTML='';
  try{
    const res=await fetch(API.DETAIL(id),{headers:H()});
    const a=await res.json();
    renderDrawer(a);
  } catch { toast('Failed to load account','error'); }
}

function renderDrawer(a){
  const avail=Number(a.balance||0)-Number(a.blocked_balance||0);
  document.getElementById('drawer-body').innerHTML=`
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border);">
      <div style="width:50px;height:50px;border-radius:12px;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:22px;color:var(--accent);"><i class="ti ti-wallet"></i></div>
      <div>
        <div style="font-size:16px;font-weight:700;font-family:monospace;">${a.account_number||'—'}</div>
        <div style="font-size:12.5px;color:var(--text-3);margin-top:2px;">${a.customer?.fullname||'—'} · ${a.type} · ${a.currency}</div>
        <div style="margin-top:5px;display:flex;gap:6px;">
          <span class="badge ${a.status}">${a.status}</span>
          ${a.is_primary?'<span class="badge primary">Primary</span>':''}
        </div>
      </div>
    </div>

    <div class="balance-row">
      <div class="balance-box">
        <div class="balance-box-label">Balance</div>
        <div class="balance-box-val">${fmt(a.balance)}</div>
      </div>
      <div class="balance-box">
        <div class="balance-box-label">Available</div>
        <div class="balance-box-val green">${fmt(avail)}</div>
      </div>
      <div class="balance-box">
        <div class="balance-box-label">Blocked</div>
        <div class="balance-box-val red">${fmt(a.blocked_balance)}</div>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-cell"><div class="detail-label">IBAN</div><div class="detail-val" style="font-size:12px;font-family:monospace;">${a.iban||'—'}</div></div>
      <div class="detail-cell"><div class="detail-label">Bank</div><div class="detail-val">${a.bank?.name||'—'}</div></div>
      <div class="detail-cell"><div class="detail-label">Loan Blocked</div><div class="detail-val">${fmt(a.loan_blocked_balance)}</div></div>
      <div class="detail-cell"><div class="detail-label">Created</div><div class="detail-val">${a.created_at?new Date(a.created_at).toLocaleDateString('en-DE'):'—'}</div></div>
      <div class="detail-cell"><div class="detail-label">Customer ID</div><div class="detail-val">${a.customer?.id||'—'}</div></div>
      <div class="detail-cell"><div class="detail-label">Customer Email</div><div class="detail-val">${a.customer?.email||'—'}</div></div>
    </div>`;

  const btns=[];
  btns.push(`<button class="btn success" onclick="openAmountModal('deposit','Deposit Funds','Enter amount to deposit into this account')"><i class="ti ti-arrow-down-left"></i> Deposit</button>`);
  btns.push(`<button class="btn warning" onclick="openAmountModal('withdraw','Withdraw Funds','Enter amount to withdraw from this account')"><i class="ti ti-arrow-up-right"></i> Withdraw</button>`);
  if(a.status==='ACTIVE')  btns.push(`<button class="btn danger" onclick="doAction('freeze')"><i class="ti ti-snowflake"></i> Freeze</button>`);
  if(a.status==='BLOCKED') btns.push(`<button class="btn success" onclick="doAction('activate')"><i class="ti ti-player-play"></i> Activate</button>`);
  if(a.status!=='CLOSED')  btns.push(`<button class="btn danger" onclick="doAction('close')"><i class="ti ti-circle-x"></i> Close</button>`);
  btns.push(`<button class="btn ghost" onclick="openAmountModal('block-balance','Block Balance','Amount to add to blocked balance')"><i class="ti ti-lock"></i> Block Bal.</button>`);
  btns.push(`<button class="btn ghost" onclick="openAmountModal('unblock-balance','Unblock Balance','Amount to release from blocked balance')"><i class="ti ti-lock-open"></i> Unblock Bal.</button>`);
  if(!a.is_primary) btns.push(`<button class="btn ghost" onclick="doAction('set-primary')"><i class="ti ti-star"></i> Set Primary</button>`);
  document.getElementById('drawer-footer').innerHTML=btns.join('');
}

function closeDrawer(){ document.getElementById('overlay').classList.remove('show'); document.getElementById('acct-drawer').classList.remove('open'); activeId=null; }

// ── ACTIONS ───────────────────────────────────────────────────────────────
async function doAction(action){
  if(!activeId) return;
  const map={
    freeze:       {url:API.FREEZE(activeId),   msg:'Account frozen'},
    activate:     {url:API.ACTIVATE(activeId), msg:'Account activated'},
    close:        {url:API.CLOSE(activeId),    msg:'Account closed'},
    'set-primary':{url:API.SET_PRI(activeId),  msg:'Set as primary account'},
  };
  const a=map[action]; if(!a) return;
  try{
    const res=await fetch(a.url,{method:'POST',headers:H(),body:JSON.stringify({})});
    if(res.ok){ toast(a.msg); closeDrawer(); loadAccounts(currentPage); loadStats(); }
    else { const d=await res.json(); toast(d.detail||'Action failed','error'); }
  } catch { toast('Network error','error'); }
}

// ── AMOUNT MODAL ──────────────────────────────────────────────────────────
function openAmountModal(action, title, hint){
  activeAction=action;
  document.getElementById('amount-modal-title').textContent=title;
  document.getElementById('amount-hint').textContent=hint;
  document.getElementById('modal-amount').value='';
  document.getElementById('amount-modal').classList.add('show');
}
function closeAmountModal(){ document.getElementById('amount-modal').classList.remove('show'); activeAction=null; }

async function confirmAmount(){
  const amount=parseFloat(document.getElementById('modal-amount').value);
  if(!amount||amount<=0){ toast('Enter a valid amount','error'); return; }
  const urlMap={
    'deposit':         API.DEPOSIT(activeId),
    'withdraw':        API.WITHDRAW(activeId),
    'block-balance':   API.BLK_BAL(activeId),
    'unblock-balance': API.UBLK_BAL(activeId),
  };
  const url=urlMap[activeAction]; if(!url) return;
  const btn=document.getElementById('amount-confirm-btn');
  const spin=document.getElementById('amount-spin');
  btn.disabled=true; spin.style.display='block';
  try{
    const res=await fetch(url,{method:'POST',headers:H(),body:JSON.stringify({amount})});
    if(res.ok){ toast('Operation successful'); closeAmountModal(); closeDrawer(); loadAccounts(currentPage); loadStats(); }
    else { const d=await res.json(); toast(d.detail||'Failed','error'); }
  } catch { toast('Network error','error'); }
  finally { btn.disabled=false; spin.style.display='none'; }
}

document.getElementById('amount-modal').addEventListener('click',function(e){ if(e.target===this) closeAmountModal(); });
document.getElementById('search').addEventListener('keydown',e=>{ if(e.key==='Enter') loadAccounts(1); });

async function logout(){
  try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
  localStorage.clear(); window.location.href='../../auth/auth.html';
}

loadStats();
loadAccounts(1);