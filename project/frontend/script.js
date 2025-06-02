// frontend/script.js

const API_URL = 'http://localhost:5000';

// A helper to swap which “view” <div> is visible
function showView(viewId) {
  document.querySelectorAll('.view').forEach(div => {
    div.classList.remove('active');
  });
  const target = document.getElementById(viewId);
  if (target) {
    target.classList.add('active');
  }
}

// Helper to check if a JWT is expired
function tokenIsExpired(token) {
  try {
    const payloadBase64 = token.split('.')[1];
    const payloadJson = atob(payloadBase64);
    const payload = JSON.parse(payloadJson);
    return (payload.exp * 1000) < Date.now();
  } catch (e) {
    return true;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  // ────────────────────────────────────────────────────────────────────────
  // LOGIN FORM HANDLER
  // ────────────────────────────────────────────────────────────────────────
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = document.getElementById('login-email').value.trim();
      const password = document.getElementById('login-password').value.trim();
      const remember = document.getElementById('login-remember')?.checked || false;

      try {
        const res = await fetch(`${API_URL}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, remember })
        });
        const data = await res.json();

        if (res.ok) {
          alert('Login successful! Redirecting to dashboard…');
          localStorage.setItem('token', data.token);
          window.location.href = 'dashboard.html';
          return;
        }

        // Show server‐provided message on any non‐200
        const serverMsg = data.error || data.msg || 'An unexpected error occurred.';
        alert(serverMsg);
      } catch (err) {
        console.error('Login fetch error:', err);
        alert('Network error: could not reach the server.');
      }
    });
  }

  // ────────────────────────────────────────────────────────────────────────
  // REGISTER FORM HANDLER
  // ────────────────────────────────────────────────────────────────────────
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = document.getElementById('register-email').value.trim();
      const password = document.getElementById('register-password').value.trim();
      const confirm = document.getElementById('register-confirm').value.trim();

      try {
        const res = await fetch(`${API_URL}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, confirm })
        });
        const data = await res.json();

        if (res.ok) {
          alert(
            'Registration successful! Please check your email and click the verification link ' +
            'to complete your registration before you can log in.'
          );
          registerForm.reset();
          showView('login-view');
          return;
        }

        const serverMsg = data.error || data.msg || 'An unexpected error occurred during registration.';
        alert(serverMsg);
      } catch (err) {
        console.error('Register fetch error:', err);
        alert('Network error: could not reach the server.');
      }
    });
  }

  // ────────────────────────────────────────────────────────────────────────
  // RESET‐REQUEST FORM HANDLER
  // ────────────────────────────────────────────────────────────────────────
  const resetRequestForm = document.getElementById('reset-request-form');
  if (resetRequestForm) {
    resetRequestForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('reset-email').value.trim();

      try {
        const res = await fetch(`${API_URL}/reset-password-request`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email })
        });
        const data = await res.json();

        if (res.ok) {
          alert(data.message || 'If that email is registered, a reset link has been sent.');
          resetRequestForm.reset();
          showView('login-view');
        } else {
          alert(data.error || data.msg || 'Error requesting password reset.');
        }
      } catch (err) {
        console.error('Reset request fetch error:', err);
        alert('Network error: could not reach the server.');
      }
    });
  }

  // ────────────────────────────────────────────────────────────────────────
  // RESET‐PASSWORD FORM HANDLER
  // ────────────────────────────────────────────────────────────────────────
  const resetPasswordForm = document.getElementById('reset-password-form');
  if (resetPasswordForm) {
    resetPasswordForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const password = document.getElementById('new-password').value.trim();
      const confirm = document.getElementById('confirm-password').value.trim();
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token');

      if (!token) {
        alert('No reset token provided. Please use the link from your email.');
        return;
      }
      if (!password || password !== confirm) {
        alert('Passwords do not match or are invalid.');
        return;
      }

      try {
        const res = await fetch(`${API_URL}/reset-password/${token}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password, confirm })
        });
        const data = await res.json();

        if (res.ok) {
          alert(data.message || 'Password reset successfully. You can now log in.');
          window.location.href = 'index.html';
        } else {
          alert(data.error || data.msg || 'Error resetting password.');
        }
      } catch (err) {
        console.error('Reset-password fetch error:', err);
        alert('Network error: could not reach the server.');
      }
    });
  }

  // ────────────────────────────────────────────────────────────────────────
  // VIEW‐TOGGLING BUTTONS (only in index.html)
  // ────────────────────────────────────────────────────────────────────────
  const btnShowResetReq = document.getElementById('show-reset-request');
  if (btnShowResetReq) {
    btnShowResetReq.addEventListener('click', () => {
      showView('reset-request-view');
    });
  }

  const btnShowRegister = document.getElementById('show-register');
  if (btnShowRegister) {
    btnShowRegister.addEventListener('click', () => {
      showView('register-view');
    });
  }

  const btnBackFromRegister = document.getElementById('show-login-from-register');
  if (btnBackFromRegister) {
    btnBackFromRegister.addEventListener('click', () => {
      showView('login-view');
    });
  }

  const btnBackFromResetReq = document.getElementById('show-login-from-reset');
  if (btnBackFromResetReq) {
    btnBackFromResetReq.addEventListener('click', () => {
      showView('login-view');
    });
  }

  const btnBackFromResetPw = document.getElementById('show-login-from-resetpw');
  if (btnBackFromResetPw) {
    btnBackFromResetPw.addEventListener('click', () => {
      showView('login-view');
    });
  }

  // If URL is index.html?token=..., show reset-password form
  const params = new URLSearchParams(window.location.search);
  if (params.has('token')) {
    showView('reset-password-view');
  }
});

// -----------------------------------------------------
// LOGOUT FUNCTION (called from dashboard.html)
// -----------------------------------------------------
function logout() {
  localStorage.removeItem('token');
  // After logout, navigate back to index.html (login view):
  window.location.href = 'index.html';
}
