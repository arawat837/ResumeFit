const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchPresets() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/presets`);
    if (!res.ok) {
      throw new Error(`Failed to load role presets (HTTP ${res.status})`);
    }
    return await res.json();
  } catch (err) {
    console.error('Error fetching presets:', err);
    // Return fallback presets if backend is temporarily unreachable
    return [
      { id: 'data_analyst', title: 'Data Analyst' },
      { id: 'consultant', title: 'Management Consultant' },
      { id: 'marketing', title: 'Marketing Specialist' },
      { id: 'hr', title: 'Human Resources (HR) Generalist' }
    ];
  }
}

export async function scanResume({ file, mode, roleId, customJd }) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mode', mode);

  if (mode === 'preset' && roleId) {
    formData.append('role_id', roleId);
  } else if (mode === 'custom' && customJd) {
    formData.append('custom_jd', customJd);
  }

  // Set safe 75-second timeout to accommodate Render free-tier cold starts
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 75000);

  try {
    const res = await fetch(`${API_BASE_URL}/api/scan`, {
      method: 'POST',
      body: formData,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorDetail = 'An error occurred during resume analysis.';
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) {
          errorDetail = errJson.detail;
        }
      } catch (_) {
        errorDetail = `Server responded with status ${res.status}: ${res.statusText}`;
      }
      throw new Error(errorDetail);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error('Scan request timed out. The server took longer than 75 seconds to respond. Please try again.');
    }
    throw err;
  }
}
