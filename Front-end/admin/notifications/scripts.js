  const access=localStorage.getItem('access_token');
  const refresh=localStorage.getItem('refresh_token');
  //if(!access) window.location.href='/auth/auth.html';

  const API={
    SEND:          '/notifications/admin/send/',
    BROADCAST:     '/notifications/admin/broadcast/',
    HISTORY:       '/notifications/admin/',
    LOGOUT:        '/api/v1/auth/logout/',
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

  // ── TABS ──────────────────────────────────────────────────────────────────
  function switchTab(tab){
    ['compose','history'].forEach(t=>{
      document.getElementById('tab-'+t).classList.toggle('active',t===tab);
      document.getElementById('panel-'+t).classList.toggle('active',t===tab);
    });
    if(tab==='history') loadHistory();
  }

  // ── TARGET TOGGLE ─────────────────────────────────────────────────────────
  let currentTarget='individual';
  function setTarget(t){
    currentTarget=t;
    document.getElementById('tgt-individual').classList.toggle('active',t==='individual');
    document.getElementById('tgt-broadcast').classList.toggle('active',t==='broadcast');
    document.getElementById('user-field').style.display=t==='individual'?'':'none';
    const warn=document.getElementById('broadcast-warning');
    warn.style.display=t==='broadcast'?'flex':'none';
    document.getElementById('send-text').textContent=t==='broadcast'?'Broadcast to All':'Send Notification';
  }

  // ── CHAR COUNT ────────────────────────────────────────────────────────────
  document.getElementById('notif-message').addEventListener('input',function(){
    document.getElementById('char-count').textContent=this.value.length;
  });

  // ── VALIDATION ────────────────────────────────────────────────────────────
  function fe(id,msg){
    const el=document.getElementById(id);
    if(msg){el.textContent=msg;el.classList.add('show');}
    else{el.classList.remove('show');}
  }
  function validate(){
    let ok=true;
    if(currentTarget==='individual'){
      const uid=document.getElementById('target-user').value.trim();
      if(!uid){fe('err-user','Please enter a valid user ID.');ok=false;}
      else fe('err-user','');
    }
    const title=document.getElementById('notif-title').value.trim();
    if(!title){fe('err-title','Please enter a title.');ok=false;}
    else fe('err-title','');
    const msg=document.getElementById('notif-message').value.trim();
    if(!msg){fe('err-message','Please enter a message.');ok=false;}
    else fe('err-message','');
    return ok;
  }

  // ── SEND ──────────────────────────────────────────────────────────────────
  async function sendNotification(){
    if(!validate()) return;
    const btn=document.getElementById('send-btn');
    const spin=document.getElementById('send-spin');
    const icon=document.getElementById('send-icon');
    const txt=document.getElementById('send-text');
    btn.disabled=true;spin.style.display='block';icon.style.display='none';txt.textContent='Sending…';

    const title=document.getElementById('notif-title').value.trim();
    const message=document.getElementById('notif-message').value.trim();
    const type=document.getElementById('notif-type').value;

    try{
      let res;
      if(currentTarget==='broadcast'){
        res=await fetch(API.BROADCAST,{method:'POST',headers:H(),body:JSON.stringify({title,message,type})});
      } else {
        const user_id=document.getElementById('target-user').value.trim();
        res=await fetch(API.SEND,{method:'POST',headers:H(),body:JSON.stringify({title,message,type,user_id})});
      }
      if(res.ok){
        document.getElementById('compose-form').style.display='none';
        document.getElementById('send-success').classList.add('show');
        document.getElementById('success-sub').textContent=currentTarget==='broadcast'
          ?'Your broadcast has been sent to all users.'
          :`Notification sent to user #${document.getElementById('target-user').value.trim()}.`;
      } else {
        const d=await res.json();
        toast(d.detail||d.message||'Failed to send notification.','error');
      }
    } catch { toast('Network error. Please try again.','error'); }
    finally { btn.disabled=false;spin.style.display='none';icon.style.display='';txt.textContent=currentTarget==='broadcast'?'Broadcast to All':'Send Notification'; }
  }

  function resetCompose(){
    document.getElementById('compose-form').style.display='';
    document.getElementById('send-success').classList.remove('show');
    document.getElementById('target-user').value='';
    document.getElementById('notif-title').value='';
    document.getElementById('notif-message').value='';
    document.getElementById('notif-type').value='INFO';
    document.getElementById('char-count').textContent='0';
    setTarget('individual');
    ['err-user','err-title','err-message'].forEach(id=>fe(id,''));
  }

  // ── HISTORY ───────────────────────────────────────────────────────────────
  async function loadHistory(){
    document.getElementById('history-list').innerHTML='<div class="empty-state"><i class="ti ti-loader-2"></i><p>Loading…</p></div>';
    try{
      const res=await fetch(API.HISTORY,{headers:H()});
      const data=await res.json();
      const list=Array.isArray(data)?data:(data.results||[]);
      renderHistory(list);
    } catch { renderHistory(mockHistory()); }
  }

  const typeIcon={
    INFO:'ti-info-circle',SUCCESS:'ti-circle-check',WARNING:'ti-alert-triangle',
    ERROR:'ti-alert-circle',LOAN_UPDATE:'ti-coin',TRANSACTION:'ti-arrows-right-left',
    SECURITY:'ti-shield-lock',SYSTEM:'ti-settings',
  };

  function renderHistory(list){
    document.getElementById('history-count').textContent=`${list.length} sent`;
    if(!list.length){
      document.getElementById('history-list').innerHTML='<div class="empty-state"><i class="ti ti-bell-off"></i><p>No notifications sent yet.</p></div>';
      return;
    }
    document.getElementById('history-list').innerHTML=list.map(n=>{
      const isBroadcast=n.is_broadcast||!n.user;
      const iconCls=isBroadcast?'broadcast':n.type==='SYSTEM'?'system':'individual';
      return `
        <div class="notif-item">
          <div class="notif-icon ${iconCls}"><i class="ti ${typeIcon[n.type]||'ti-bell'}"></i></div>
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <div class="notif-title">${n.title||'—'}</div>
              <span class="badge ${iconCls}">${isBroadcast?'Broadcast':'Individual'}</span>
            </div>
            <div class="notif-body">${n.message||n.body||'—'}</div>
            <div class="notif-meta">
              <div class="notif-meta-item"><i class="ti ti-tag"></i>${n.type||'INFO'}</div>
              ${!isBroadcast&&n.user?`<div class="notif-meta-item"><i class="ti ti-user"></i>User #${n.user}</div>`:'<div class="notif-meta-item"><i class="ti ti-speakerphone"></i>All users</div>'}
              <div class="notif-meta-item"><i class="ti ti-clock"></i>${n.created_at?new Date(n.created_at).toLocaleString('en-DE',{dateStyle:'short',timeStyle:'short'}):'—'}</div>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  function mockHistory(){
    return [
      {id:'n1',title:'System Maintenance',        message:'Scheduled maintenance on June 10 from 2–4 AM.',          type:'SYSTEM',  is_broadcast:true, user:null,created_at:'2026-06-01T10:00:00Z'},
      {id:'n2',title:'Loan Request Approved',     message:'Your personal loan of €8,000 has been approved.',        type:'LOAN_UPDATE',is_broadcast:false,user:42,created_at:'2026-05-28T14:30:00Z'},
      {id:'n3',title:'Security Alert',            message:'A login was detected from a new device.',                type:'SECURITY',is_broadcast:false,user:7, created_at:'2026-05-25T22:10:00Z'},
      {id:'n4',title:'New Feature Available',     message:'You can now transfer money via IBAN instantly.',          type:'INFO',    is_broadcast:true, user:null,created_at:'2026-05-20T09:00:00Z'},
      {id:'n5',title:'Transaction Reversed',      message:'Your transaction of €1,200 has been reversed by admin.', type:'TRANSACTION',is_broadcast:false,user:15,created_at:'2026-05-11T16:30:00Z'},
    ];
  }

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear();window.location.href='/auth/auth.html';
  }
