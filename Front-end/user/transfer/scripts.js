    // ── ENDPOINTS ─────────────────────────────────────────────────────────────
    const API = {
    CARD_TRANSFER: '/api/transactions/card-transfer/',
    IBAN_TRANSFER: '/api/transactions/iban-transfer/',
    LOGOUT:        '/api/v1/auth/logout/',
  };

  const access  = localStorage.getItem('access_token');
  const refresh = localStorage.getItem('refresh_token');
  if (!access) window.location.href = '../../auth/auth.html';
  const H = () => ({ 'Content-Type':'application/json','Authorization':`Bearer ${access}` });

  const userName = localStorage.getItem('user_name')||'';
  document.getElementById('sidebar-name').textContent = userName||'My Account';
  document.getElementById('sidebar-avatar').textContent = userName?userName.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase():'U';

  // Source account from localStorage (set on dashboard after loading accounts)
  const accountNumber = localStorage.getItem('account_number')||'My Default Account';
  const accountId     = localStorage.getItem('account_id')||null;
  document.getElementById('source-display').textContent = accountNumber||'My Default Account';

  function toast(msg,type='error'){
    const el=document.createElement('div');el.className=`toast ${type}`;
    el.innerHTML=`<i class="ti ti-alert-circle"></i> ${msg}`;
    document.getElementById('toast-container').appendChild(el);setTimeout(()=>el.remove(),4000);
  }

  // ── METHOD TOGGLE ─────────────────────────────────────────────────────────
  let currentMethod='card';
  function setMethod(method){
    currentMethod=method;
    document.getElementById('btn-card').classList.toggle('active',method==='card');
    document.getElementById('btn-iban').classList.toggle('active',method==='iban');
    document.getElementById('field-card-dest').style.display=method==='card'?'':'none';
    document.getElementById('field-iban-dest').style.display=method==='iban'?'':'none';
    if(method==='card'){
      document.getElementById('cv-method').textContent='Card Transfer';
      document.getElementById('cv-sub').textContent='Enter the recipient\'s card number to send money';
      document.getElementById('cv-icon').className='ti ti-credit-card cv-icon';
    } else {
      document.getElementById('cv-method').textContent='IBAN Transfer';
      document.getElementById('cv-sub').textContent='Enter the recipient\'s IBAN to send money';
      document.getElementById('cv-icon').className='ti ti-building-bank cv-icon';
    }
    clearErrors();
  }

  // ── FORMAT HELPERS ────────────────────────────────────────────────────────
  function formatCard(input){ let v=input.value.replace(/\D/g,'').slice(0,16); input.value=v.replace(/(.{4})/g,'$1 ').trim(); }
  function formatIban(input){ let v=input.value.replace(/\s/g,'').toUpperCase().slice(0,34); input.value=v.replace(/(.{4})/g,'$1 ').trim(); }

  // ── VALIDATION ────────────────────────────────────────────────────────────
  function fe(id,msg){ const el=document.getElementById(id); if(msg){el.textContent=msg;el.classList.add('show');}else el.classList.remove('show'); }
  function clearErrors(){
    ['err-card-dest','err-iban-dest','err-amount'].forEach(id=>fe(id,''));
    ['card-dest','iban-dest','amount'].forEach(id=>{ const el=document.getElementById(id); if(el) el.classList.remove('error'); });
  }
  function validate(){
    let ok=true; clearErrors();
    if(currentMethod==='card'){
      const raw=document.getElementById('card-dest').value.replace(/\s/g,'');
      if(!/^\d{16}$/.test(raw)){ fe('err-card-dest','Please enter a valid 16-digit card number.'); document.getElementById('card-dest').classList.add('error'); ok=false; }
    } else {
      const raw=document.getElementById('iban-dest').value.replace(/\s/g,'');
      if(raw.length<15||raw.length>34){ fe('err-iban-dest','Please enter a valid IBAN.'); document.getElementById('iban-dest').classList.add('error'); ok=false; }
    }
    const amount=parseFloat(document.getElementById('amount').value);
    if(!amount||amount<=0){ fe('err-amount','Please enter a valid amount greater than €0.'); document.getElementById('amount').classList.add('error'); ok=false; }
    return ok;
  }

  // ── CONFIRM MODAL ─────────────────────────────────────────────────────────
  function openConfirm(){
    if(!validate()) return;
    const amount=parseFloat(document.getElementById('amount').value).toFixed(2);
    const dest=currentMethod==='card'?document.getElementById('card-dest').value.trim():document.getElementById('iban-dest').value.trim();
    const desc=document.getElementById('description').value.trim();
    document.getElementById('modal-amount').textContent=`€${amount}`;
    document.getElementById('modal-method').textContent=currentMethod==='card'?'Card Transfer':'IBAN Transfer';
    document.getElementById('modal-dest').textContent=dest;
    document.getElementById('modal-desc').textContent=desc||'—';
    document.getElementById('modal-desc-row').style.display=desc?'flex':'none';
    document.getElementById('confirm-modal').classList.add('show');
  }
  function closeConfirm(){ document.getElementById('confirm-modal').classList.remove('show'); }

  // ── SUBMIT ────────────────────────────────────────────────────────────────
  async function submitTransfer(){
    const btn=document.getElementById('confirm-btn');
    const spin=document.getElementById('confirm-spin');
    const icon=document.getElementById('confirm-icon');
    const txt=document.getElementById('confirm-text');
    btn.disabled=true;spin.style.display='block';icon.style.display='none';txt.textContent='Sending…';

    const amount=parseFloat(document.getElementById('amount').value);
    const desc=document.getElementById('description').value.trim();

    // Backend expects: source_account (id), destination_card or destination_iban, amount, description
    let endpoint, payload;
    if(currentMethod==='card'){
      const dest=document.getElementById('card-dest').value.replace(/\s/g,'');
      endpoint=API.CARD_TRANSFER;
      payload={ source_account_id: parseInt(accountId), destination_card_number: dest, amount, description: desc };
    } else {
      const dest=document.getElementById('iban-dest').value.replace(/\s/g,'');
      endpoint=API.IBAN_TRANSFER;
      payload={ source_account_id: parseInt(accountId), destination_iban: dest, amount, description: desc };
    }

    try{
      const res=await fetch(endpoint,{method:'POST',headers:H(),body:JSON.stringify(payload)});
      const data=await res.json();
      if(res.ok){
        closeConfirm();
        showSuccess(payload,amount);
      } else {
        closeConfirm();
        toast(data.detail||data.message||'Transfer failed. Please try again.');
      }
    } catch { closeConfirm(); toast('Network error. Please try again.'); }
    finally { btn.disabled=false;spin.style.display='none';icon.style.display='';txt.textContent='Send Money'; }
  }

  // ── SUCCESS STATE ─────────────────────────────────────────────────────────
  function showSuccess(payload,amount){
    document.getElementById('form-body').style.display='none';
    document.getElementById('form-footer').style.display='none';
    document.getElementById('success-sub').textContent=`€${Number(amount).toFixed(2)} has been sent successfully.`;
    const dest=currentMethod==='card'?payload.destination_card:payload.destination_iban;
    document.getElementById('success-detail').innerHTML=`
      <div class="success-detail-row"><span>Method</span><span>${currentMethod==='card'?'Card Transfer':'IBAN Transfer'}</span></div>
      <div class="success-detail-row"><span>To</span><span>${dest}</span></div>
      <div class="success-detail-row"><span>Amount</span><span>€${Number(amount).toFixed(2)}</span></div>
      ${payload.description?`<div class="success-detail-row"><span>Description</span><span>${payload.description}</span></div>`:''}
      <div class="success-detail-row"><span>Date</span><span>${new Date().toLocaleString('en-DE',{dateStyle:'short',timeStyle:'short'})}</span></div>`;
    document.getElementById('success-overlay').classList.add('show');
  }

  function newTransfer(){
    resetForm();
    document.getElementById('form-body').style.display='';
    document.getElementById('form-footer').style.display='';
    document.getElementById('success-overlay').classList.remove('show');
  }
  function resetForm(){
    document.getElementById('card-dest').value='';
    document.getElementById('iban-dest').value='';
    document.getElementById('amount').value='';
    document.getElementById('description').value='';
    clearErrors();
  }

  document.getElementById('confirm-modal').addEventListener('click',function(e){ if(e.target===this) closeConfirm(); });

  async function logout(){
    try{await fetch(API.LOGOUT,{method:'POST',headers:H(),body:JSON.stringify({refresh_token:refresh})});}catch{}
    localStorage.clear();window.location.href='../../auth/auth.html';
  }
