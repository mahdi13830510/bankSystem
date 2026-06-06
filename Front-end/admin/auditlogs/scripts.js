  const access=localStorage.getItem('access_token');
  const refresh=localStorage.getItem('refresh_token');
  //if(!access) window.location.href='/auth/auth.html';
  const API={LOGS:'/auditlogs/',LOGOUT:'/api/v1/auth/logout/'};
  const H=()=>({'Content-Type':'application/json','Authorization':`Bearer ${access}`});
  const adminName=localStorage.getItem('user_name')||'Admin';
  document.getElementById('sidebar-name').textContent=adminName;
  document.getElementById('sidebar-avatar').textContent=adminName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()||'AD';

  let allLogs=[], filtered=[], currentPage=1;
  const PAGE=25;

  const severityIcon={INFO:'ti-info-circle',WARNING:'ti-alert-triangle',CRITICAL:'ti-alert-octagon'};

  async function load(){
    try{
      const res=await fetch(API.LOGS,{headers:H()});
      const data=await res.json();
      allLogs=Array.isArray(data)?data:(data.results||[]);
    } catch {
      allLogs=[
        {id:'l1',action:'USER_BLOCKED',    target_type:'User',  target_id:'12',description:'User blocked due to suspicious activity.',severity:'CRITICAL',actor:{fullname:'Admin'},ip_address:'192.168.1.1',metadata:{reason:'Too many failed logins'},         created_at:'2026-05-15T10:22:00Z'},
        {id:'l2',action:'LOAN_APPROVED',   target_type:'Loan',  target_id:'r1',description:'Loan request approved and loan created.',  severity:'INFO',    actor:{fullname:'Admin'},ip_address:'192.168.1.1',metadata:{amount:8000,duration:24},                created_at:'2026-05-14T14:00:00Z'},
        {id:'l3',action:'BALANCE_ADJUSTED',target_type:'Account',target_id:'5',description:'Admin deposited €3,000 into account.',    severity:'WARNING', actor:{fullname:'Admin'},ip_address:'10.0.0.1',  metadata:{amount:3000,type:'deposit'},               created_at:'2026-05-13T09:10:00Z'},
        {id:'l4',action:'ROLE_CHANGED',    target_type:'User',  target_id:'8', description:'User role changed to employee.',          severity:'WARNING', actor:{fullname:'Admin'},ip_address:'192.168.1.2',metadata:{old_role:'customer',new_role:'employee'},  created_at:'2026-05-12T11:30:00Z'},
        {id:'l5',action:'TX_REVERSED',     target_type:'Tx',    target_id:'t2',description:'Transaction reversed by admin.',          severity:'CRITICAL',actor:{fullname:'Admin'},ip_address:'192.168.1.1',metadata:{original_amount:1200},                    created_at:'2026-05-11T16:00:00Z'},
        {id:'l6',action:'USER_VERIFIED',   target_type:'User',  target_id:'15',description:'User identity verified.',                severity:'INFO',    actor:{fullname:'Admin'},ip_address:'192.168.1.1',metadata:{},                                         created_at:'2026-05-10T08:00:00Z'},
        {id:'l7',action:'ACCOUNT_FROZEN',  target_type:'Account',target_id:'3',description:'Account frozen pending investigation.',   severity:'CRITICAL',actor:{fullname:'Admin'},ip_address:'10.0.0.2',  metadata:{reason:'Fraud suspicion'},                 created_at:'2026-05-09T13:45:00Z'},
        {id:'l8',action:'PENALTY_APPLIED', target_type:'Installment',target_id:'i4',description:'Manual penalty applied to overdue installment.',severity:'WARNING',actor:{fullname:'Admin'},ip_address:'192.168.1.1',metadata:{amount:43.5},               created_at:'2026-05-08T10:00:00Z'},
      ];
    }
    applyFilter();
  }

  function applyFilter(){
    const q=document.getElementById('search').value.trim().toLowerCase();
    const sev=document.getElementById('filter-severity').value;
    filtered=allLogs.filter(l=>{
      if(sev&&l.severity!==sev) return false;
      if(q&&!(l.action.toLowerCase().includes(q)||l.description.toLowerCase().includes(q))) return false;
      return true;
    });
    currentPage=1;
    render();
  }

  function resetFilter(){
    document.getElementById('search').value='';
    document.getElementById('filter-severity').value='';
    applyFilter();
  }

  function render(){
    document.getElementById('table-count').textContent=`${filtered.length} event${filtered.length!==1?'s':''}`;
    if(!filtered.length){document.getElementById('log-list').innerHTML='<div class="empty-state"><i class="ti ti-file-off"></i><p>No logs match your filters.</p></div>';document.getElementById('pagination').style.display='none';return;}

    const start=(currentPage-1)*PAGE;
    const page=filtered.slice(start,start+PAGE);

    document.getElementById('log-list').innerHTML=page.map((l,idx)=>{
      const hasLast=idx<page.length-1;
      const meta=Object.keys(l.metadata||{}).length?JSON.stringify(l.metadata,null,2):'';
      return `
        <div class="log-item" id="log-${l.id}">
          <div class="log-dot-wrap">
            <div class="log-dot ${l.severity}"></div>
            ${hasLast?'<div class="log-line"></div>':''}
          </div>
          <div class="log-body">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <div class="log-action">${l.action.replace(/_/g,' ')}</div>
              <span class="badge ${l.severity}">${l.severity}</span>
            </div>
            <div class="log-desc">${l.description||'—'}</div>
            <div class="log-meta">
              ${l.actor?`<div class="log-meta-item"><i class="ti ti-user"></i>${l.actor.fullname||'System'}</div>`:''}
              ${l.target_type?`<div class="log-meta-item"><i class="ti ti-tag"></i>${l.target_type} #${l.target_id||'?'}</div>`:''}
              ${l.ip_address?`<div class="log-meta-item"><i class="ti ti-network"></i>${l.ip_address}</div>`:''}
              <div class="log-meta-item"><i class="ti ti-clock"></i>${l.created_at?new Date(l.created_at).toLocaleString('en-DE',{dateStyle:'short',timeStyle:'medium'}):'—'}</div>
            </div>
            ${meta?`<div class="expand-btn" onclick="toggleMeta('log-${l.id}',this)"><i class="ti ti-code"></i> View metadata</div><pre class="meta-json">${meta}</pre>`:''}
          </div>
        </div>`;
    }).join('');

    const pages=Math.ceil(filtered.length/PAGE);
    const pag=document.getElementById('pagination');
    if(pages>1){
      pag.style.display='flex';
      document.getElementById('pag-info').textContent=`Showing ${start+1}–${Math.min(start+PAGE,filtered.length)} of ${filtered.length}`;
      let b=`<button class="pag-btn" onclick="goPage(${currentPage-1})" ${currentPage===1?'disabled':''}><i class="ti ti-chevron-left"></i></button>`;
      for(let i=1;i<=Math.min(pages,7);i++) b+=`<button class="pag-btn ${i===currentPage?'active':''}" onclick="goPage(${i})">${i}</button>`;
      b+=`<button class="pag-btn" onclick="goPage(${currentPage+1})" ${currentPage===pages?'disabled':''}><i class="ti ti-chevron-right"></i></button>`;
      document.getElementById('pag-btns').innerHTML=b;
    } else { pag.style.display='none'; }
  }

  function goPage(p){const total=Math.ceil(filtered.length/PAGE);if(p<1||p>total)return;currentPage=p;render();window.scrollTo(0,0);}
  function toggleMeta(logId,btn){
    const el=document.getElementById(logId);
    el.classList.toggle('expanded');
    btn.innerHTML=el.classList.contains('expanded')?'<i class="ti ti-code"></i> Hide metadata':'<i class="ti ti-code"></i> View metadata';
  }

  document.getElementById('search').addEventListener('keydown',e=>{if(e.key==='Enter')applyFilter();});
  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear();window.location.href='/auth/auth.html';
  }
  load();
