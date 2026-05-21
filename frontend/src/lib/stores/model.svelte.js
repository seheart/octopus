const STORAGE_KEY = 'octopus-selected-model';

function read() {
  try {
    return localStorage.getItem(STORAGE_KEY) || '';
  } catch (_e) {
    return '';
  }
}

export const selectedModel = $state({ value: read() });

// One-shot prompt seed — set by Models page "try this prompt" button,
// consumed by ChatPage on mount, then cleared. Not persisted, not exported
// (use setPendingPrompt / consumePendingPrompt to interact with it).
const pendingPrompt = $state({ value: '' });

// One-shot pull seed — set by the Get Started card's "Pull <model>" button,
// consumed by PullPage on mount so a fresh user lands on the pull page with
// the download already running. Same lifecycle as pendingPrompt.
const pendingPull = $state({ value: '' });

export function setModel(name) {
  selectedModel.value = name;
  try {
    localStorage.setItem(STORAGE_KEY, name);
  } catch (_e) {
    /* ignore */
  }
}

export function setPendingPrompt(text) {
  pendingPrompt.value = text || '';
}

export function consumePendingPrompt() {
  const v = pendingPrompt.value;
  pendingPrompt.value = '';
  return v;
}

export function setPendingPull(name) {
  pendingPull.value = name || '';
}

export function consumePendingPull() {
  const v = pendingPull.value;
  pendingPull.value = '';
  return v;
}
