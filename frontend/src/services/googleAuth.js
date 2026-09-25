/**
 * ResumeFit - Google Identity Services (GIS) Integration Service
 * Manages Google OAuth 2.0 popup and Google ID token flows.
 */

let scriptLoadingPromise = null;

/**
 * Loads the Google Identity Services client script dynamically if not already present.
 */
export function loadGoogleScript() {
  if (typeof window === 'undefined') return Promise.resolve(null);

  if (window.google?.accounts?.oauth2) {
    return Promise.resolve(window.google);
  }

  if (scriptLoadingPromise) {
    return scriptLoadingPromise;
  }

  scriptLoadingPromise = new Promise((resolve, reject) => {
    // Check if script already exists in document
    const existing = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (existing) {
      if (window.google?.accounts?.oauth2) {
        return resolve(window.google);
      }
      existing.addEventListener('load', () => resolve(window.google));
      existing.addEventListener('error', () => reject(new Error('Failed to load Google Identity Services.')));
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      resolve(window.google);
    };
    script.onerror = () => {
      scriptLoadingPromise = null;
      reject(new Error('Failed to load Google Identity Services SDK. Please check your network connection.'));
    };
    document.head.appendChild(script);
  });

  return scriptLoadingPromise;
}

/**
 * Retrieves the configured Google Client ID.
 * Priority: 1. Environment variable (VITE_GOOGLE_CLIENT_ID) -> 2. LocalStorage override
 */
export function getGoogleClientId() {
  try {
    const envId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (envId && envId.trim()) {
      return envId.trim();
    }
    const localId = localStorage.getItem('resumefit_google_client_id');
    if (localId && localId.trim()) {
      return localId.trim();
    }
  } catch {
    // Fail silently in restricted storage
  }
  return '';
}

/**
 * Persists a Google Client ID in local storage for instant testing without server restart.
 */
export function saveGoogleClientId(clientId) {
  try {
    if (clientId && clientId.trim()) {
      localStorage.setItem('resumefit_google_client_id', clientId.trim());
    } else {
      localStorage.removeItem('resumefit_google_client_id');
    }
  } catch {
    // Fail silently
  }
}

/**
 * Triggers the official Google ID selection box popup.
 * Uses Google Identity Services `initTokenClient` with `prompt: 'select_account'`.
 *
 * @param {Object} options
 * @param {string} [options.clientId] - Google Cloud OAuth Client ID (falls back to getGoogleClientId())
 * @param {Function} options.onSuccess - Callback receiving { access_token }
 * @param {Function} options.onError - Callback receiving Error object
 */
export async function triggerGoogleAccountPicker({ clientId, onSuccess, onError }) {
  const effectiveClientId = (clientId || getGoogleClientId()).trim();

  if (!effectiveClientId) {
    const err = new Error('MISSING_CLIENT_ID');
    err.code = 'MISSING_CLIENT_ID';
    if (onError) onError(err);
    return;
  }

  try {
    const google = await loadGoogleScript();
    if (!google?.accounts?.oauth2) {
      throw new Error('Google Identity Services SDK is not ready yet. Please try again.');
    }

    const tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: effectiveClientId,
      scope: 'openid email profile',
      callback: (tokenResponse) => {
        if (tokenResponse.error) {
          const errMsg = tokenResponse.error_description || tokenResponse.error;
          if (onError) onError(new Error(`Google sign-in error: ${errMsg}`));
          return;
        }

        if (tokenResponse.access_token) {
          if (onSuccess) onSuccess({ access_token: tokenResponse.access_token });
        } else {
          if (onError) onError(new Error('No access token returned from Google.'));
        }
      },
      error_callback: (err) => {
        let msg = 'Failed to open Google account chooser.';
        if (err.type === 'popup_closed') {
          msg = 'Google account selection was closed before signing in.';
        } else if (err.type === 'popup_blocked') {
          msg = 'Popup blocked by your browser. Please allow popups for localhost to sign in with Google.';
        } else if (err.message) {
          msg = err.message;
        }
        if (onError) onError(new Error(msg));
      }
    });

    // Request access token with explicit account selection prompt
    // This triggers the real "Choose an account" Google popup dialog
    tokenClient.requestAccessToken({ prompt: 'select_account' });
  } catch (err) {
    if (onError) onError(err);
  }
}
