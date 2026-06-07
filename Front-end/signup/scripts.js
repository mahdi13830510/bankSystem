  // ── ENDPOINT ──────────────────────────────────────────────────────────────
  const API_REGISTER = '/api/v1/users/register/';

  // ── HELPERS ───────────────────────────────────────────────────────────────
  function showError(msg) {
    const el = document.getElementById('global-error');
    document.getElementById('global-error-text').textContent = msg;
    el.classList.add('show');
    el.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  function clearError() { document.getElementById('global-error').classList.remove('show'); }
  function fe(id, msg) {
    const el = document.getElementById(id);
    if (msg) { el.textContent=msg; el.classList.add('show'); }
    else el.classList.remove('show');
  }
  function markError(id, has) { const el=document.getElementById(id); if(el) el.classList.toggle('error',has); }
  function togglePw(id, btn) {
    const inp = document.getElementById(id);
    const isText = inp.type==='text';
    inp.type = isText?'password':'text';
    btn.querySelector('i').className = isText?'ti ti-eye':'ti ti-eye-off';
  }

  // ── PASSWORD STRENGTH ─────────────────────────────────────────────────────
  function checkStrength(val) {
    let score=0;
    if(val.length>=8) score++;
    if(/[A-Z]/.test(val)) score++;
    if(/[0-9]/.test(val)) score++;
    if(/[^A-Za-z0-9]/.test(val)) score++;
    const bars=[1,2,3,4].map(i=>document.getElementById('bar-'+i));
    const cls=score<=1?'weak':score===2?'weak':score===3?'medium':'strong';
    const texts=['','Too weak','Could be stronger','Almost there!','Strong password ✓'];
    const colors={weak:'var(--danger)',medium:'var(--warning)',strong:'var(--success)'};
    bars.forEach((b,i)=>{ b.className='pw-bar '+(i<score?cls:''); });
    const lbl=document.getElementById('pw-label');
    lbl.textContent=val.length?texts[score]:'Use 8+ characters with letters, numbers & symbols';
    lbl.style.color=val.length?(colors[cls]||colors.weak):'';
  }

  // ── STEP NAVIGATION ───────────────────────────────────────────────────────
  function validateStep1() {
    let ok=true;
    const fullname=document.getElementById('fullname').value.trim();
    const natCode =document.getElementById('national_code').value.trim();
    const phone   =document.getElementById('phone').value.trim();
    const email   =document.getElementById('email').value.trim();
    if(fullname.length<3){ fe('err-fullname','Please enter your full name (at least 3 characters).'); markError('fullname',true); ok=false; } else{ fe('err-fullname',''); markError('fullname',false); }
    if(!/^\d{10}$/.test(natCode)){ fe('err-national_code','Please enter a valid 10-digit national code.'); markError('national_code',true); ok=false; } else{ fe('err-national_code',''); markError('national_code',false); }
    if(!/^\+?[\d\s\-]{7,15}$/.test(phone)){ fe('err-phone','Please enter a valid phone number.'); markError('phone',true); ok=false; } else{ fe('err-phone',''); markError('phone',false); }
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){ fe('err-email','Please enter a valid email address.'); markError('email',true); ok=false; } else{ fe('err-email',''); markError('email',false); }
    return ok;
  }

  function goStep2() {
    if(!validateStep1()) return;
    clearError();
    document.getElementById('panel-1').classList.remove('active');
    document.getElementById('panel-2').classList.add('active');
    document.getElementById('step-ind-1').classList.remove('active');
    document.getElementById('step-ind-1').classList.add('done');
    document.getElementById('step-circle-1').innerHTML='<i class="ti ti-check" style="font-size:13px;"></i>';
    document.getElementById('step-line-1').classList.add('done');
    document.getElementById('step-ind-2').classList.add('active');
    document.getElementById('password').focus();
  }

  function goStep1() {
    clearError();
    document.getElementById('panel-2').classList.remove('active');
    document.getElementById('panel-1').classList.add('active');
    document.getElementById('step-ind-2').classList.remove('active');
    document.getElementById('step-line-1').classList.remove('done');
    document.getElementById('step-ind-1').classList.remove('done');
    document.getElementById('step-ind-1').classList.add('active');
    document.getElementById('step-circle-1').textContent='1';
  }

  // ── SUBMIT ────────────────────────────────────────────────────────────────
  async function submitRegister() {
    clearError();
    const password = document.getElementById('password').value;
    const confirm  = document.getElementById('confirm-password').value;
    let ok=true;
    if(password.length<8){ fe('err-password','Password must be at least 8 characters.'); markError('password',true); ok=false; } else{ fe('err-password',''); markError('password',false); }
    if(password!==confirm){ fe('err-confirm','Passwords do not match.'); markError('confirm-password',true); ok=false; } else{ fe('err-confirm',''); markError('confirm-password',false); }
    if(!ok) return;

    const btn=document.getElementById('submit-btn');
    const spin=document.getElementById('submit-spin');
    const icon=document.getElementById('submit-icon');
    const txt=document.getElementById('submit-text');
    btn.disabled=true; spin.style.display='block'; icon.style.display='none'; txt.textContent='Creating…';

    const payload = {
      fullname:      document.getElementById('fullname').value.trim(),
      national_code: document.getElementById('national_code').value.trim(),
      phone:         document.getElementById('phone').value.trim(),
      email:         document.getElementById('email').value.trim(),
      password,
    };

    try {
      const res  = await fetch(API_REGISTER, {
        method: 'POST',
        headers: { 'Content-Type':'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (res.ok) {
        document.getElementById('main-form').style.display='none';
        document.getElementById('signin-link').style.display='none';
        document.getElementById('success-name').textContent=payload.fullname.split(' ')[0];
        document.getElementById('success-screen').classList.add('show');
      } else {
        // Map backend field errors to correct step
        const fieldMap={phone:'err-phone',email:'err-email',national_code:'err-national_code',fullname:'err-fullname',password:'err-password'};
        let handled=false;
        Object.entries(fieldMap).forEach(([key,errId])=>{
          if(data[key]){
            const msg=Array.isArray(data[key])?data[key][0]:data[key];
            if(['phone','email','national_code','fullname'].includes(key)) goStep1();
            fe(errId,msg); markError(key,true); handled=true;
          }
        });
        if(!handled) showError(data.detail||data.message||'Registration failed. Please try again.');
      }
    } catch { showError('Network error. Please check your connection and try again.'); }
    finally { btn.disabled=false; spin.style.display='none'; icon.style.display=''; txt.textContent='Create Account'; }
  }

  // ── NATIONAL CODE: numbers only ───────────────────────────────────────────
  document.getElementById('national_code').addEventListener('input',function(){ this.value=this.value.replace(/\D/g,'').slice(0,10); });

  // ── ENTER KEY ─────────────────────────────────────────────────────────────
  document.getElementById('email').addEventListener('keydown',e=>{ if(e.key==='Enter') goStep2(); });
  document.getElementById('confirm-password').addEventListener('keydown',e=>{ if(e.key==='Enter') submitRegister(); });