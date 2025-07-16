const messageDiv = document.getElementById('message');

function setToken(token) {
  localStorage.setItem('access_token', token);
}

async function login(username, password) {
  try {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('grant_type', 'password');

    const response = await fetch('/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      messageDiv.textContent = err.detail || 'Login failed';
      return false;
    }

    const data = await response.json();
    setToken(data.access_token);
    return true;
  } catch (e) {
    messageDiv.textContent = 'Network error';
    return false;
  }
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  if (!username || !password) {
    messageDiv.textContent = 'Please enter username and password';
    return;
  }
  const success = await login(username, password);
  if (success) {
    // Redirect to main page after successful login
    window.location.href = '/';
  }
});

// If already logged in, redirect to main page
if (localStorage.getItem('access_token')) {
  window.location.href = '/';
}
