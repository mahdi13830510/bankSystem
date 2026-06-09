 const access  = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');
  if (!access) window.location.href = '../../auth/auth.html';

  const API = {
    USERS:  (q) => `/api/v1/users/admin/?${q}`,
    USER:   (id) => `/api/v1/users/admin/${id}/`,
    VERIFY: (id) => `/api/v1/users/admin/${id}/verify/`,
    BLOCK:  (id) => `/api/v1/users/admin/${id}/block/`,
    UNBLOCK:(id) => `/api/v1/users/admin/${id}/unblock/`,
    SUSPEND:(id) => `/api/v1/users/admin/${id}/suspend/`,
    ACTIVATE:(id)=> `/api/v1/users/admin/${id}/activate/`,
    ROLE:   (id) => `/api/v1/users/admin/${id}/change-role/`,
    RESET_PW:(id)=> `/api/v1/users/admin/${id}/reset-password/`,
    RESET_FA:(id)=> `/api/v1/users/admin/${id}/reset-attempts/`,
    LOGOUT: '/api/v1/auth/logout/',
  };
  function authHeaders(ct=true) {
    const h = { 'Authorization':`Bearer ${access}` };
    if (ct) h['Content-Type']='application/json';
    return h;
  }

  // sidebar
  const adminName = localStorage.getItem('user_name')||'Admin';
  document.getElementById('sidebar-name').textContent = adminName;
  document.getElementById('sidebar-avatar').textContent = adminName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()||'AD';

  // toast
  function toast(msg,type='success'){
    const el=document.createElement('div'); el.className=`toast ${type}`;
    el.innerHTML=`<i class="ti ti-${type==='success'?'circle-check':'alert-circle'}"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(()=>el.remove(),4000);
  }

  // ── COLORS ────────────────────────────────────────────────────────────────
  const avatarColors = ['#3b82f6','#10b981','#f59e0b','#8b5cf6','#ef4444','#06b6d4','#ec4899'];
  function avatarColor(name){ return avatarColors[(name||'').charCodeAt(0)%avatarColors.length]; }
  function initials(name){ return (name||'?').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase(); }

  // ── STATE ─────────────────────────────────────────────────────────────────
  let allUsers=[], currentPage=1, totalCount=0;
  const PAGE=20;
  let activeUserId=null;

  // ── LOAD USERS ────────────────────────────────────────────────────────────
  async function loadUsers(page=1){
    currentPage=page;
    const params=new URLSearchParams();
    const search=document.getElementById('search').value.trim();
    const status=document.getElementById('filter-status').value;
    const role  =document.getElementById('filter-role').value;
    const verif =document.getElementById('filter-verified').value;
    if(search) params.set('search',search);
    if(status) params.set('status',status);
    if(role)   params.set('primary_role',role);
    if(verif)  params.set('is_verified',verif);

    document.getElementById('table-wrap').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    document.getElementById('pagination').style.display='none';

    try{
      const res  = await fetch(API.USERS(params.toString()),{headers:authHeaders()});
      const data = await res.json();
      allUsers   = Array.isArray(data)?data:(data.results||[]);
      totalCount = data.count||allUsers.length;
      renderTable();
    } catch {
      // mock
      allUsers = Array.from({length:12},(_,i)=>({
        id:i+1, fullname:['Alice Johnson','Bob Smith','Clara Lee','David Park','Eva Müller','Frank Berg','Grace Kim','Hassan Ali','Iris Chen','Jack Wu','Karen Yıldız','Leo Rossi'][i],
        phone:`+49 170 ${100+i} 0000`, email:`user${i+1}@elirapay.com`, national_code:`100000000${i}`,
        status:['active','active','pending','blocked','active','suspended','active','active','active','pending','active','active'][i],
        primary_role:['customer','customer','customer','customer','employee','customer','manager','customer','admin','customer','customer','customer'][i],
        is_verified:[true,true,false,true,true,false,true,true,true,false,true,true][i],
        date_joined: new Date(Date.now()-i*86400000*15).toISOString(),
      }));
      totalCount=allUsers.length;
      renderTable();
    }
  }

  function renderTable(){
    document.getElementById('table-count').textContent=`${totalCount} result${totalCount!==1?'s':''}`;
    if(!allUsers.length){
      document.getElementById('table-wrap').innerHTML='<div class="empty-state"><i class="ti ti-users-off"></i><p>No users found.</p></div>';
      return;
    }
    const rows=allUsers.map(u=>`
      <tr onclick="openDrawer(${u.id})">
        <td>
          <div class="user-cell">
            <div class="user-avatar-tbl" style="background:${avatarColor(u.fullname)}">${initials(u.fullname)}</div>
            <div>
              <div class="user-fullname">${u.fullname||'—'}</div>
              <div class="user-phone">${u.phone||'—'}</div>
            </div>
          </div>
        </td>
        <td>${u.email||'—'}</td>
        <td><span class="badge ${u.status||'pending'}">${u.status||'—'}</span></td>
        <td><span class="badge ${u.primary_role||'customer'}">${u.primary_role||'—'}</span></td>
        <td>${u.is_verified
          ?'<i class="ti ti-circle-check verified-icon" title="Verified"></i>'
          :'<i class="ti ti-clock unverified-icon" title="Pending verification"></i>'}
        </td>
        <td style="color:var(--text-3);font-size:12.5px;">${u.date_joined?new Date(u.date_joined).toLocaleDateString('en-DE'):'—'}</td>
        <td><button class="action-btn" onclick="event.stopPropagation();openDrawer(${u.id})"><i class="ti ti-dots-vertical"></i></button></td>
      </tr>`).join('');

    document.getElementById('table-wrap').innerHTML=`
      <table>
        <thead><tr>
          <th>User</th><th>Email</th><th>Status</th><th>Role</th><th>Verified</th><th>Joined</th><th></th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>`;

    // simple pagination display (backend may return all at once)
    const pages=Math.ceil(totalCount/PAGE);
    if(pages>1){
      document.getElementById('pagination').style.display='flex';
      document.getElementById('pag-info').textContent=`Page ${currentPage} of ${pages}`;
      let btns=`<button class="pag-btn" onclick="loadUsers(${currentPage-1})" ${currentPage===1?'disabled':''}><i class="ti ti-chevron-left"></i></button>`;
      for(let i=1;i<=Math.min(pages,7);i++) btns+=`<button class="pag-btn ${i===currentPage?'active':''}" onclick="loadUsers(${i})">${i}</button>`;
      btns+=`<button class="pag-btn" onclick="loadUsers(${currentPage+1})" ${currentPage===pages?'disabled':''}><i class="ti ti-chevron-right"></i></button>`;
      document.getElementById('pag-btns').innerHTML=btns;
    }
  }

  function resetFilters(){
    document.getElementById('search').value='';
    document.getElementById('filter-status').value='';
    document.getElementById('filter-role').value='';
    document.getElementById('filter-verified').value='';
    loadUsers(1);
  }

  // ── DRAWER ────────────────────────────────────────────────────────────────
  async function openDrawer(id){
    activeUserId=id;
    document.getElementById('overlay').classList.add('show');
    document.getElementById('user-drawer').classList.add('open');
    document.getElementById('drawer-body').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    document.getElementById('drawer-footer').innerHTML='';

    try{
      const res  = await fetch(API.USER(id),{headers:authHeaders()});
      const u    = await res.json();
      renderDrawer(u);
    } catch {
      const u=allUsers.find(u=>u.id===id)||{id,fullname:'Unknown',phone:'—',email:'—',status:'active',primary_role:'customer',is_verified:false};
      renderDrawer(u);
    }
  }

  function renderDrawer(u){
    const col=avatarColor(u.fullname);
    document.getElementById('drawer-body').innerHTML=`
      <div class="profile-header">
        <div class="profile-avatar-lg" style="background:${col}">${initials(u.fullname)}</div>
        <div>
          <div class="profile-name">${u.fullname||'—'}</div>
          <div class="profile-phone">${u.phone||'—'}</div>
          <div class="profile-badges">
            <span class="badge ${u.status}">${u.status||'—'}</span>
            <span class="badge ${u.primary_role}">${u.primary_role||'—'}</span>
            ${u.is_verified?'<span class="badge active"><i class="ti ti-check"></i> Verified</span>':'<span class="badge pending"><i class="ti ti-clock"></i> Unverified</span>'}
          </div>
        </div>
      </div>

      <div class="detail-grid">
        <div class="detail-cell"><div class="detail-label">ID</div><div class="detail-val">${u.id}</div></div>
        <div class="detail-cell"><div class="detail-label">Email</div><div class="detail-val">${u.email||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">National Code</div><div class="detail-val">${u.national_code||'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Failed Logins</div><div class="detail-val">${u.failed_login_attempts??'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Last Login</div><div class="detail-val">${u.last_login?new Date(u.last_login).toLocaleString('en-DE'):'Never'}</div></div>
        <div class="detail-cell"><div class="detail-label">Joined</div><div class="detail-val">${u.date_joined?new Date(u.date_joined).toLocaleDateString('en-DE'):'—'}</div></div>
        <div class="detail-cell"><div class="detail-label">Is Staff</div><div class="detail-val">${u.is_staff?'Yes':'No'}</div></div>
        <div class="detail-cell"><div class="detail-label">Blocked Until</div><div class="detail-val">${u.blocked_until?new Date(u.blocked_until).toLocaleString('en-DE'):'—'}</div></div>
      </div>`;

    // footer action buttons based on status
    const btns=[];
    if(!u.is_verified) btns.push(`<button class="btn success" onclick="doAction('verify')"><i class="ti ti-circle-check"></i> Verify</button>`);
    if(u.status!=='blocked')   btns.push(`<button class="btn danger"  onclick="openBlockModal()"><i class="ti ti-lock"></i> Block</button>`);
    if(u.status==='blocked')   btns.push(`<button class="btn success" onclick="doAction('unblock')"><i class="ti ti-lock-open"></i> Unblock</button>`);
    if(u.status!=='suspended') btns.push(`<button class="btn warning" onclick="doAction('suspend')"><i class="ti ti-pause"></i> Suspend</button>`);
    if(u.status==='suspended'||u.status==='pending') btns.push(`<button class="btn success" onclick="doAction('activate')"><i class="ti ti-player-play"></i> Activate</button>`);
    btns.push(`<button class="btn ghost" onclick="openRoleModal('${u.primary_role}')"><i class="ti ti-user-cog"></i> Role</button>`);
    btns.push(`<button class="btn ghost" onclick="doAction('reset-attempts')"><i class="ti ti-refresh"></i> Reset Attempts</button>`);
    btns.push(`<button class="btn ghost" onclick="openPwModal()"><i class="ti ti-key"></i> Reset PW</button>`);
    document.getElementById('drawer-footer').innerHTML=btns.join('');
  }

  function closeDrawer(){
    document.getElementById('overlay').classList.remove('show');
    document.getElementById('user-drawer').classList.remove('open');
    activeUserId=null;
  }

  // ── ACTIONS ───────────────────────────────────────────────────────────────
  async function doAction(action){
    if(!activeUserId) return;
    const map={
      verify:   {url:API.VERIFY(activeUserId),   msg:'User verified successfully'},
      unblock:  {url:API.UNBLOCK(activeUserId),  msg:'User unblocked'},
      suspend:  {url:API.SUSPEND(activeUserId),  msg:'User suspended'},
      activate: {url:API.ACTIVATE(activeUserId), msg:'User activated'},
      'reset-attempts':{url:API.RESET_FA(activeUserId), msg:'Failed attempts reset'},
    };
    const a=map[action]; if(!a) return;
    try{
      const res=await fetch(a.url,{method:'POST',headers:authHeaders(),body:JSON.stringify({})});
      if(res.ok){ toast(a.msg); closeDrawer(); loadUsers(currentPage); }
      else { const d=await res.json(); toast(d.detail||'Action failed','error'); }
    } catch { toast('Network error','error'); }
  }

  // ── BLOCK MODAL ───────────────────────────────────────────────────────────
  function openBlockModal(){ document.getElementById('block-modal').classList.add('show'); }
  function closeBlockModal(){ document.getElementById('block-modal').classList.remove('show'); }
  async function confirmBlock(){
    const btn=document.getElementById('block-confirm-btn');
    const spin=document.getElementById('block-spin');
    btn.disabled=true; spin.style.display='block';
    const reason=document.getElementById('block-reason').value;
    const until =document.getElementById('block-until').value;
    const body={};
    if(reason) body.reason=reason;
    if(until)  body.blocked_until=new Date(until).toISOString();
    try{
      const res=await fetch(API.BLOCK(activeUserId),{method:'POST',headers:authHeaders(),body:JSON.stringify(body)});
      if(res.ok){ toast('User blocked'); closeBlockModal(); closeDrawer(); loadUsers(currentPage); }
      else { const d=await res.json(); toast(d.detail||'Failed','error'); }
    } catch { toast('Network error','error'); }
    finally { btn.disabled=false; spin.style.display='none'; }
  }

  // ── RESET PW MODAL ────────────────────────────────────────────────────────
  function openPwModal(){ document.getElementById('pw-modal').classList.add('show'); }
  function closePwModal(){ document.getElementById('pw-modal').classList.remove('show'); }
  async function confirmResetPw(){
    const pw=document.getElementById('new-password').value;
    if(!pw||pw.length<8){ toast('Password must be at least 8 characters','error'); return; }
    const btn=document.getElementById('pw-confirm-btn'); const spin=document.getElementById('pw-spin');
    btn.disabled=true; spin.style.display='block';
    try{
      const res=await fetch(API.RESET_PW(activeUserId),{method:'POST',headers:authHeaders(),body:JSON.stringify({new_password:pw})});
      if(res.ok){ toast('Password reset successfully'); closePwModal(); }
      else { const d=await res.json(); toast(d.detail||'Failed','error'); }
    } catch { toast('Network error','error'); }
    finally { btn.disabled=false; spin.style.display='none'; document.getElementById('new-password').value=''; }
  }

  // ── CHANGE ROLE MODAL ─────────────────────────────────────────────────────
  function openRoleModal(current){ document.getElementById('new-role').value=current; document.getElementById('role-modal').classList.add('show'); }
  function closeRoleModal(){ document.getElementById('role-modal').classList.remove('show'); }
  async function confirmChangeRole(){
    const role=document.getElementById('new-role').value;
    const btn=document.getElementById('role-confirm-btn'); const spin=document.getElementById('role-spin');
    btn.disabled=true; spin.style.display='block';
    try{
      const res=await fetch(API.ROLE(activeUserId),{method:'POST',headers:authHeaders(),body:JSON.stringify({primary_role:role})});
      if(res.ok){ toast(`Role changed to ${role}`); closeRoleModal(); closeDrawer(); loadUsers(currentPage); }
      else { const d=await res.json(); toast(d.detail||'Failed','error'); }
    } catch { toast('Network error','error'); }
    finally { btn.disabled=false; spin.style.display='none'; }
  }

  // close modals on overlay click
  ['block-modal','pw-modal','role-modal'].forEach(id=>{
    document.getElementById(id).addEventListener('click',function(e){ if(e.target===this) this.classList.remove('show'); });
  });

  // search on enter
  document.getElementById('search').addEventListener('keydown',e=>{ if(e.key==='Enter') loadUsers(1); });

  // ── LOGOUT ────────────────────────────────────────────────────────────────
  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:authHeaders(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear(); window.location.href='../../auth/auth.html';
  }

  loadUsers(1);