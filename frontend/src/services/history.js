/**
 * frontend/src/services/history.js
 * Session-based scan history helper.
 * Uses browser sessionStorage (cleared when the tab closes).
 * Safe against private browsing mode storage exceptions.
 */

const HISTORY_STORAGE_KEY = 'resumefit_scan_history';
const MAX_HISTORY_ITEMS = 10;

/**
 * Retrieves the list of stored scans for this session.
 * Always returns an array, failing silently on any storage restrictions.
 */
export function getScanHistory() {
  try {
    const raw = sessionStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    // Private browsing or storage quota disabled; fail silently
    return [];
  }
}

/**
 * Saves a completed scan result to sessionStorage.
 * Prepend new entry, caps array at 10 items, drops oldest.
 */
export function saveScanResult({
  filename,
  mode,
  roleId,
  result
}) {
  if (!result || typeof result !== 'object') return [];

  const entry = {
    id: `scan_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
    filename: filename || 'Uploaded Resume',
    timestamp: Date.now(),
    ats_score: result.ats_score ?? 0,
    engine: result.engine || 'rubric_fallback',
    mode: mode || 'general',
    roleId: roleId || null,
    breakdown: result.breakdown || {},
    recommendations: result.recommendations || [],
    agent_engines: result.agent_engines || {},
    parsed_summary: result.parsed_summary || {}
  };

  try {
    const current = getScanHistory();
    // Prepend new item and filter out duplicate id if any
    const updated = [entry, ...current.filter((item) => item.id !== entry.id)].slice(0, MAX_HISTORY_ITEMS);
    sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
    return updated;
  } catch (err) {
    // Fail silently in restricted environments
    return [entry];
  }
}

/**
 * Clears scan history from sessionStorage.
 */
export function clearScanHistory() {
  try {
    sessionStorage.removeItem(HISTORY_STORAGE_KEY);
  } catch (err) {
    // Fail silently
  }
  return [];
}

/**
 * Helper to display human-readable relative timestamps.
 * e.g., "Just now", "2 min ago", "1 hour ago"
 */
export function formatRelativeTime(timestamp) {
  if (!timestamp) return '';
  const now = Date.now();
  const diffSeconds = Math.max(0, Math.floor((now - timestamp) / 1000));

  if (diffSeconds < 45) {
    return 'Just now';
  }
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) {
    return `${diffMinutes} min ago`;
  }
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours} hr${diffHours === 1 ? '' : 's'} ago`;
  }
  return new Date(timestamp).toLocaleDateString();
}
