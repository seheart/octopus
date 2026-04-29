const STORAGE_KEY = 'octopus-theme';

function read() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'light' || v === 'dark') return v;
  } catch (_) {
    /* ignore */
  }
  return matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function apply(value) {
  const root = document.documentElement;
  root.classList.toggle('dark', value === 'dark');
}

export const theme = $state({ value: read() });

export function setTheme(value) {
  theme.value = value;
  apply(value);
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch (_) {
    /* ignore */
  }
}

export function toggleTheme() {
  setTheme(theme.value === 'dark' ? 'light' : 'dark');
}

export function initTheme() {
  apply(theme.value);
}
