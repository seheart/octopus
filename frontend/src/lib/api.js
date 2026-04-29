export async function getModels() {
  const r = await fetch('/api/models');
  if (!r.ok) throw new Error('failed to load models');
  return (await r.json()).models || [];
}

export async function getLoaded() {
  const r = await fetch('/api/loaded');
  if (!r.ok) throw new Error('failed to load loaded models');
  return (await r.json()).models || [];
}

export async function getGpu() {
  const r = await fetch('/api/gpu');
  if (!r.ok) throw new Error('failed to load gpu');
  return await r.json();
}

export async function getOllamaInfo() {
  const r = await fetch('/api/ollama');
  if (!r.ok) throw new Error('failed to load ollama info');
  return await r.json();
}

export async function getHostInfo() {
  const r = await fetch('/api/host');
  if (!r.ok) throw new Error('failed to load host info');
  return await r.json();
}

export function fmtBytes(b) {
  if (!b) return '–';
  const gb = b / 1e9;
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(b / 1e6).toFixed(0)} MB`;
}

export function fmtParams(s) {
  return s ? s.replace(/\.0+B/, 'B') : '';
}

export function fmtUptime(seconds) {
  if (!seconds || seconds < 0) return '–';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function ollamaTimeAgo(iso) {
  if (!iso) return '';
  const ms = Date.now() - new Date(iso).getTime();
  const d = Math.floor(ms / 86400000);
  if (d > 0) return `${d}d ago`;
  const h = Math.floor(ms / 3600000);
  if (h > 0) return `${h}h ago`;
  const m = Math.floor(ms / 60000);
  if (m > 0) return `${m}m ago`;
  return 'just now';
}
