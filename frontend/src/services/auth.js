const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'resumefit_auth_token';

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Fail silently in restricted storage
  }
}

export function removeStoredToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Fail silently
  }
}

export async function signupUser({ name, email, password }) {
  const res = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password })
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to create account. Please try again.');
  }

  if (data.token) {
    setStoredToken(data.token);
  }
  return data;
}

export async function loginUser({ email, password }) {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Invalid email or password.');
  }

  if (data.token) {
    setStoredToken(data.token);
  }
  return data;
}

export async function getMyProfile() {
  const token = getStoredToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    if (res.status === 401) {
      // Token expired or invalid
      removeStoredToken();
      return null;
    }

    if (!res.ok) {
      return null;
    }

    const data = await res.json();
    return data.user || null;
  } catch (err) {
    console.error('Error fetching user profile:', err);
    return null;
  }
}

export async function redeemCode({ code }) {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Please sign in or create an account before redeeming your promo code.');
  }

  const res = await fetch(`${API_BASE_URL}/api/auth/redeem`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ code })
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Invalid or expired promo code.');
  }

  return data;
}
