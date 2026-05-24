const THEME_KEY = 'octopus-theme';
const MODE_KEY = 'octopus-theme-mode';

/**
 * `mode` is the user's *preference*: 'light' | 'dark' | 'system'. `theme.value`
 * is the *resolved* class on the html element ('light' | 'dark'). When mode
 * is 'system' we follow prefers-color-scheme live; flipping the OS theme
 * updates the app without a reload.
 */

function systemPrefersLight() {
  return matchMedia?.('(prefers-color-scheme: light)').matches ?? false;
}

function readMode() {
  try {
    const v = localStorage.getItem(MODE_KEY);
    if (v === 'light' || v === 'dark' || v === 'system') return v;
  } catch (_) {
    /* ignore */
  }
  // Legacy storage: pre-3-mode versions only stored the resolved theme.
  try {
    const legacy = localStorage.getItem(THEME_KEY);
    if (legacy === 'light' || legacy === 'dark') return legacy;
  } catch (_) {
    /* ignore */
  }
  return 'system';
}

function resolve(mode) {
  if (mode === 'system') return systemPrefersLight() ? 'light' : 'dark';
  return mode;
}

function apply(value) {
  document.documentElement.classList.toggle('dark', value === 'dark');
}

const initialMode = typeof window !== 'undefined' ? readMode() : 'dark';
const initialValue = typeof window !== 'undefined' ? resolve(initialMode) : 'dark';

export const theme = $state({ value: initialValue, mode: initialMode });

/** @type {MediaQueryList | null} */
let mql = null;
/** @type {((e: MediaQueryListEvent) => void) | null} */
let mqlListener = null;

function unsubscribeSystem() {
  if (mql && mqlListener) {
    mql.removeEventListener('change', mqlListener);
  }
  mql = null;
  mqlListener = null;
}

function subscribeSystem() {
  unsubscribeSystem();
  if (typeof matchMedia === 'undefined') return;
  mql = matchMedia('(prefers-color-scheme: light)');
  mqlListener = () => {
    if (theme.mode !== 'system') return;
    theme.value = resolve('system');
    apply(theme.value);
  };
  mql.addEventListener('change', mqlListener);
}

export function setThemeMode(mode) {
  if (mode !== 'light' && mode !== 'dark' && mode !== 'system') return;
  theme.mode = mode;
  theme.value = resolve(mode);
  apply(theme.value);
  try {
    localStorage.setItem(MODE_KEY, mode);
    if (mode === 'system') {
      localStorage.removeItem(THEME_KEY);
    } else {
      localStorage.setItem(THEME_KEY, mode);
    }
  } catch (_) {
    /* ignore */
  }
  if (mode === 'system') subscribeSystem();
  else unsubscribeSystem();
}

// Kept for the footer's icon button — toggles between light and dark only,
// breaking out of "system" mode if you're in it.
export function toggleTheme() {
  setThemeMode(theme.value === 'dark' ? 'light' : 'dark');
}

// Back-compat shim for any caller still using the old API.
export function setTheme(value) {
  setThemeMode(value);
}

export function initTheme() {
  apply(theme.value);
  if (theme.mode === 'system') subscribeSystem();
}
