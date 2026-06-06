 // ── ENDPOINTS (base prefix set in Django: /api/v1/auth/) ──────────────────
  const API = {
    LOGIN:      '/api/v1/auth/login/',
    VERIFY_OTP: '/api/v1/auth/verify-otp/',
    ME:         '/api/v1/users/me/',
  };

  let currentPhone = '';
  let countdownTimer = null;

  // ── HELPERS ───────────────────────────────────────────────────────────────
  function showError(msg) {
    document.getElementById('global-success').classList.remove('show');
    document.getElementById('global-error-text').textContent = msg;
    document.getElementById('global-error').classList.add('show');
  }
  function showSuccess(msg) {
    document.getElementById('global-error').classList.remove('show');
    document.getElementById('global-success-text').textContent = msg;
    document.getElementById('global-success').classList.add('show');
  }
  function clearMsgs() {
    document.getElementById('global-error').classList.remove('show');
    document.getElementById('global-success').classList.remove('show');
  }
  function fe(id, msg) {
    const el = document.getElementById(id);
    if (msg) { el.textContent = msg; el.classList.add('show'); }
    else el.classList.remove('show');
  }
  function setLoading(btnId, spinId, textId, loading, label) {
    document.getElementById(btnId).disabled = loading;
    document.getElementById(spinId).style.display = loading ? 'block' : 'none';
    if (!loading && label) document.getElementById(textId).textContent = label;
  }
  function validatePhone(v) { return /^\+?[\d\s\-]{7,15}$/.test(v.trim()); }
  function togglePw(id, btn) {
    const inp = document.getElementById(id);
    const isText = inp.type === 'text';
    inp.type = isText ? 'password' : 'text';
    btn.querySelector('i').className = isText ? 'ti ti-eye' : 'ti ti-eye-off';
  }

  // ── STEP INDICATOR ────────────────────────────────────────────────────────
  function goStep2() {
    document.getElementById('panel-step1').classList.remove('active');
    document.getElementById('panel-step2').classList.add('active');
    document.getElementById('step-1').classList.remove('active');
    document.getElementById('step-1').classList.add('done');
    document.getElementById('dot-1').innerHTML = '<i class="ti ti-check" style="font-size:12px;"></i>';
    document.getElementById('line-1').classList.add('done');
    document.getElementById('step-2').classList.add('active');
    document.getElementById('otp0').focus();
    startCountdown(120);
  }

  function goBackToStep1(e) {
    if (e) e.preventDefault();
    clearMsgs();
    clearInterval(countdownTimer);
    document.querySelectorAll('.otp-box').forEach(b => b.value = '');
    document.getElementById('panel-step2').classList.remove('active');
    document.getElementById('panel-step1').classList.add('active');
    document.getElementById('step-2').classList.remove('active');
    document.getElementById('step-1').classList.remove('done');
    document.getElementById('step-1').classList.add('active');
    document.getElementById('dot-1').textContent = '1';
    document.getElementById('line-1').classList.remove('done');
  }

  // ── STEP 1: Login ─────────────────────────────────────────────────────────
  async function handleLogin() {
    clearMsgs();
    const phone    = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value;
    let ok = true;

    if (!validatePhone(phone)) { fe('err-phone','Please enter a valid phone number.'); document.getElementById('phone').classList.add('error'); ok=false; }
    else { fe('err-phone',''); document.getElementById('phone').classList.remove('error'); }

    if (!password) { fe('err-password','Please enter your password.'); document.getElementById('password').classList.add('error'); ok=false; }
    else { fe('err-password',''); document.getElementById('password').classList.remove('error'); }

    if (!ok) return;

    currentPhone = phone;
    setLoading('btn-login','spin-login','text-login',true);

    try {
      const res  = await fetch(API.LOGIN, {
        method: 'POST',
        headers: { 'Content-Type':'application/json' },
        body: JSON.stringify({ phone, password }),
      });
      const data = await res.json();

      if (res.ok) {
        // Login returns { message: "OTP sent" } → go to step 2
        showSuccess('OTP sent to your phone!');
        goStep2();
      } else {
        showError(data.detail || data.message || 'Invalid phone number or password.');
      }
    } catch { showError('Network error. Please try again.'); }
    finally { setLoading('btn-login','spin-login','text-login',false,'Continue'); }
  }

  // ── STEP 2: Verify OTP ────────────────────────────────────────────────────
  async function handleOtp() {
    clearMsgs();
    const code = [...document.querySelectorAll('.otp-box')].map(b=>b.value).join('');
    if (code.length < 6) { showError('Please enter the full 6-digit code.'); return; }

    setLoading('btn-otp','spin-otp','text-otp',true);

    try {
      const res  = await fetch(API.VERIFY_OTP, {
        method: 'POST',
        headers: { 'Content-Type':'application/json' },
        body: JSON.stringify({ phone: currentPhone, code }),
      });
      const data = await res.json();

      if (res.ok) {
        // Store tokens — backend returns access_token & refresh_token
        localStorage.setItem('access_token',  data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        showSuccess('Verified! Redirecting…');

        // Fetch user info to get role and name for redirect
        try {
          const meRes  = await fetch(API.ME, { headers: { 'Authorization': `Bearer ${data.access_token}` } });
          const me     = await meRes.json();
          localStorage.setItem('user_name',    me.fullname || '');
          localStorage.setItem('user_role',    me.primary_role || 'customer');
          localStorage.setItem('user_id',      me.id || '');

          setTimeout(() => {
            const role = me.primary_role || 'customer';
            if (role === 'admin' || role === 'manager' || role === 'employee') {
              window.location.href = '/admin/dashboard/admin-dashboard.html';
            } else {
              window.location.href = '/user/dashboard/dashboard.html';
            }
          }, 800);
        } catch {
          // fallback: go to customer dashboard
          setTimeout(() => window.location.href = '/dashboard.html', 800);
        }
      } else {
        showError(data.detail || data.message || 'Invalid or expired OTP.');
        document.querySelectorAll('.otp-box').forEach(b => { b.value=''; b.classList.add('error'); });
        document.getElementById('otp0').focus();
      }
    } catch { showError('Network error. Please try again.'); }
    finally { setLoading('btn-otp','spin-otp','text-otp',false,'Verify & Sign In'); }
  }

  // ── OTP BOX BEHAVIOR ──────────────────────────────────────────────────────
  document.querySelectorAll('.otp-box').forEach((box, idx, boxes) => {
    box.addEventListener('input', e => {
      const val = e.target.value.replace(/\D/g,'');
      e.target.value = val;
      e.target.classList.remove('error');
      if (val && idx < boxes.length-1) boxes[idx+1].focus();
    });
    box.addEventListener('keydown', e => {
      if (e.key==='Backspace' && !box.value && idx>0) boxes[idx-1].focus();
    });
    box.addEventListener('paste', e => {
      e.preventDefault();
      const pasted = (e.clipboardData||window.clipboardData).getData('text').replace(/\D/g,'');
      [...pasted].slice(0,6).forEach((ch,i) => { if(boxes[i]) boxes[i].value=ch; });
      boxes[Math.min(pasted.length,5)].focus();
    });
  });

  // ── COUNTDOWN ─────────────────────────────────────────────────────────────
  function startCountdown(seconds) {
    clearInterval(countdownTimer);
    let rem = seconds;
    const el = document.getElementById('otp-countdown');
    function tick() {
      if (rem <= 0) { clearInterval(countdownTimer); el.textContent = 'Code expired. Please sign in again.'; return; }
      const m = Math.floor(rem/60); const s = rem%60;
      el.textContent = `Code expires in ${m}:${s.toString().padStart(2,'0')}`;
      rem--;
    }
    tick();
    countdownTimer = setInterval(tick, 1000);
  }

  // ── ENTER KEY ─────────────────────────────────────────────────────────────
  document.getElementById('password').addEventListener('keydown', e => { if(e.key==='Enter') handleLogin(); });
  document.getElementById('otp5').addEventListener('keydown',     e => { if(e.key==='Enter') handleOtp(); });
