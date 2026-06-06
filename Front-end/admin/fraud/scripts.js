  const access=localStorage.getItem('access_token');
  const refresh=localStorage.getItem('refresh_token');
  //if(!access) window.location.href='/auth/auth.html';
  const API={REPORTS:'/fraud/reports/',LOGOUT:'/api/v1/auth/logout/'};
  const H=()=>({'Content-Type':'application/json','Authorization':`Bearer ${access}`});
  const adminName=localStorage.getItem('user_name')||'Admin';
  document.getElementById('sidebar-name').textContent=adminName;
  document.getElementById('sidebar-avatar').textContent=adminName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()||'AD';

  let allReports=[], currentFilter='all';

  function scoreClass(s){ return s>=70?'blocked':s>=40?'suspicious':'safe'; }
  function scoreColor(s){ return s>=70?'var(--danger)':s>=40?'var(--warning)':'var(--success)'; }

  async function load(){
    try{
      const res=await fetch(API.REPORTS,{headers:H()});
      const data=await res.json();
      allReports=Array.isArray(data)?data:(data.results||[]);
    } catch {
      allReports=[
        {id:'f1',transaction_id:'aaa-111-aaa',user_id:'u1',score:92,decision:'BLOCKED',   reason:{high_amount:true,unusual_country:true},created_at:'2026-05-15T10:00:00Z'},
        {id:'f2',transaction_id:'bbb-222-bbb',user_id:'u2',score:67,decision:'SUSPICIOUS', reason:{unusual_time:true},                    created_at:'2026-05-14T22:00:00Z'},
        {id:'f3',transaction_id:'ccc-333-ccc',user_id:'u3',score:15,decision:'SAFE',       reason:{},                                     created_at:'2026-05-14T09:00:00Z'},
        {id:'f4',transaction_id:'ddd-444-ddd',user_id:'u1',score:85,decision:'BLOCKED',   reason:{high_amount:true,velocity:true},        created_at:'2026-05-13T14:00:00Z'},
        {id:'f5',transaction_id:'eee-555-eee',user_id:'u4',score:45,decision:'SUSPICIOUS', reason:{new_device:true},                      created_at:'2026-05-12T11:00:00Z'},
        {id:'f6',transaction_id:'fff-666-fff',user_id:'u5',score:8, decision:'SAFE',       reason:{},                                     created_at:'2026-05-11T08:00:00Z'},
      ];
    }
    updateStats();
    render();
  }

  function updateStats(){
    document.getElementById('cnt-safe').textContent       = allReports.filter(r=>r.decision==='SAFE').length;
    document.getElementById('cnt-suspicious').textContent = allReports.filter(r=>r.decision==='SUSPICIOUS').length;
    document.getElementById('cnt-blocked').textContent    = allReports.filter(r=>r.decision==='BLOCKED').length;
  }

  function setFilter(f,btn){
    currentFilter=f;
    document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    render();
  }

  function render(){
    const list=currentFilter==='all'?allReports:allReports.filter(r=>r.decision===currentFilter);
    document.getElementById('table-count').textContent=`${list.length} report${list!==1?'s':''}`;
    if(!list.length){document.getElementById('table-wrap').innerHTML='<div class="empty-state"><i class="ti ti-shield-check"></i><p>No reports match this filter.</p></div>';return;}
    const rows=list.map(r=>{
      const sc=scoreClass(r.score);
      const reasons=Object.keys(r.reason||{}).filter(k=>r.reason[k]);
      return `<tr>
        <td class="mono">${String(r.transaction_id).slice(0,20)}…</td>
        <td class="mono">${String(r.user_id).slice(0,12)}…</td>
        <td>
          <div class="score-col">
            <div class="score-bar-bg"><div class="score-bar-fill score-${sc}" style="width:${Math.min(100,r.score)}%"></div></div>
            <span class="score-num" style="color:${scoreColor(r.score)};">${r.score}</span>
          </div>
        </td>
        <td><span class="badge ${r.decision}">${r.decision}</span></td>
        <td>${reasons.length?reasons.map(k=>`<span class="reason-tag">${k.replace(/_/g,' ')}</span>`).join(''):'<span style="color:var(--text-3);font-size:12px;">—</span>'}</td>
        <td style="font-size:12.5px;color:var(--text-3);">${r.created_at?new Date(r.created_at).toLocaleString('en-DE',{dateStyle:'short',timeStyle:'short'}):'—'}</td>
      </tr>`;
    }).join('');
    document.getElementById('table-wrap').innerHTML=`
      <table>
        <thead><tr><th>Transaction ID</th><th>User ID</th><th>Risk Score</th><th>Decision</th><th>Reasons</th><th>Date</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear();window.location.href='/auth/auth.html';
  }

  load();
