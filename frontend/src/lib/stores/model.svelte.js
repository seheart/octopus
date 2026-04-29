const STORAGE_KEY = 'octopus-selected-model';

function read() {
  try {
    return localStorage.getItem(STORAGE_KEY) || '';
  } catch (_e) {
    return '';
  }
}

export const selectedModel = $state({ value: read() });

export function setModel(name) {
  selectedModel.value = name;
  try {
    localStorage.setItem(STORAGE_KEY, name);
  } catch (_e) {
    /* ignore */
  }
}
