// ===== js/auth.js =====

const AUTH_BASE = 'http://localhost:8008';

// ── Helpers ───────────────────────────────────────
function showError(msg) {
  const el = document.getElementById('error-banner');
  el.textContent = '❌ ' + msg;
  el.classList.add('show');
  document.getElementById('success-banner')?.classList.remove('show');
}

function showSuccess(msg) {
  const el = document.getElementById('success-banner');
  el.textContent = '✅ ' + msg;
  el.classList.add('show');
  document.getElementById('error-banner')?.classList.remove('show');
}

function clearErrors() {
  document.getElementById('error-banner')?.classList.remove('show');
  document.getElementById('success-banner')?.classList.remove('show');
}

function setLoading(loading) {
  const btn    = document.getElementById('login-btn') || document.getElementById('register-btn');
  const text   = document.getElementById('btn-text');
  const loader = document.getElementById('btn-loader');
  if (btn)    btn.disabled    = loading;
  if (text)   text.style.display  = loading ? 'none' : 'inline';
  if (loader) loader.style.display = loading ? 'inline' : 'none';
}

function hint(id, msg, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className   = `field-hint ${type}`;
}

function setFieldState(id, state) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `field-input ${state}`;
}

// ── Show/hide password ────────────────────────────
function togglePass(id, eye) {
  const inp = document.getElementById(id);
  if (!inp) return;
  const isPass = inp.type === 'password';
  inp.type = isPass ? 'text' : 'password';
  eye.textContent = isPass ? '🙈' : '👁️';
}

// ── Password strength ─────────────────────────────
function checkPassword() {
  const val    = document.getElementById('password')?.value || '';
  const fill   = document.getElementById('strength-fill');
  const label  = document.getElementById('strength-label');

  if (!fill || !label) return;

  if (val.length === 0) {
    fill.className  = 'strength-fill';
    label.textContent = '';
    hint('strength-label', '', '');
    return;
  }

  let score = 0;
  if (val.length >= 8)                    score++;
  if (/[A-Z]/.test(val))                  score++;
  if (/[0-9]/.test(val))                  score++;
  if (/[^A-Za-z0-9]/.test(val))           score++;

  if (score <= 1) {
    fill.className = 'strength-fill weak';
    hint('strength-label', '⚠️ Weak password', 'warn');
    setFieldState('password', 'error');
  } else if (score <= 2) {
    fill.className = 'strength-fill medium';
    hint('strength-label', '🔶 Medium strength', 'warn');
    setFieldState('password', '');
  } else {
    fill.className = 'strength-fill strong';
    hint('strength-label', '✅ Strong password', 'success');
    setFieldState('password', 'success');
  }

  // Re-check confirm if filled
  const confirm = document.getElementById('confirm')?.value;
  if (confirm) checkConfirm();
}

// ── Confirm password ──────────────────────────────
function checkConfirm() {
  const pass    = document.getElementById('password')?.value  || '';
  const confirm = document.getElementById('confirm')?.value   || '';

  if (!confirm) return;

  if (pass === confirm) {
    hint('confirm-hint', '✅ Passwords match', 'success');
    setFieldState('confirm', 'success');
  } else {
    hint('confirm-hint', '❌ Passwords do not match', 'error');
    setFieldState('confirm', 'error');
  }
}

// ── Login ─────────────────────────────────────────
async function login() {
  const email    = document.getElementById('email')?.value.trim()    || '';
  const password = document.getElementById('password')?.value        || '';

  clearErrors();

  if (!email)    { showError('Email is required');    setFieldState('email', 'error');    return; }
  if (!password) { showError('Password is required'); setFieldState('password', 'error'); return; }

  setLoading(true);

  try {
    const res  = await fetch(`${AUTH_BASE}/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (res.ok && data.token) {
      localStorage.setItem('eliana-token', data.token);
      localStorage.setItem('eliana-user',  JSON.stringify(data.user));
      showSuccess('Login successful! Redirecting...');
      setTimeout(() => window.location.href = 'index.html', 1000);
    } else {
      showError(data.detail || 'Invalid email or password');
      setFieldState('password', 'error');
      hint('pass-hint', '❌ Wrong password or email not found', 'error');
    }
  } catch {
    showError('Cannot connect to server — is backend running?');
  }

  setLoading(false);
}

// ── Register ──────────────────────────────────────
async function register() {
  const username = document.getElementById('username')?.value.trim() || '';
  const email    = document.getElementById('email')?.value.trim()    || '';
  const password = document.getElementById('password')?.value        || '';
  const confirm  = document.getElementById('confirm')?.value         || '';

  clearErrors();

  // Validation
  if (!username) { showError('Username is required');       setFieldState('username', 'error'); return; }
  if (username.length < 3) { showError('Username too short (min 3)'); return; }
  if (!email)    { showError('Email is required');          setFieldState('email', 'error');    return; }
  if (!email.includes('@')) { showError('Invalid email');   setFieldState('email', 'error');    return; }
  if (!password) { showError('Password is required');       setFieldState('password', 'error'); return; }
  if (password.length < 8) { showError('Password too short (min 8)'); return; }
  if (password !== confirm) { showError('Passwords do not match');    setFieldState('confirm', 'error'); return; }

  setLoading(true);

  try {
    const res  = await fetch(`${AUTH_BASE}/register`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ username, email, password })
    });
    const data = await res.json();

    if (res.ok && data.token) {
      localStorage.setItem('eliana-token', data.token);
      localStorage.setItem('eliana-user',  JSON.stringify(data.user));
      showSuccess('Account created! Redirecting...');
      setTimeout(() => window.location.href = 'index.html', 1000);
    } else {
      showError(data.detail || 'Registration failed');
      if (data.detail?.includes('email')) setFieldState('email', 'error');
    }
  } catch {
    showError('Cannot connect to server — is backend running?');
  }

  setLoading(false);
}

// ── Auth guard ────────────────────────────────────
function checkAuth() {
  const token = localStorage.getItem('eliana-token');
  const page  = window.location.pathname.split('/').pop();
  const authPages = ['login.html', 'register.html'];

  if (!token && !authPages.includes(page)) {
    window.location.href = 'login.html';
  }
  if (token && authPages.includes(page)) {
    window.location.href = 'index.html';
  }
}

// ── Logout ────────────────────────────────────────
function logout() {
  localStorage.removeItem('eliana-token');
  localStorage.removeItem('eliana-user');
  window.location.href = 'login.html';
}

// ── Run auth check ────────────────────────────────
checkAuth();
