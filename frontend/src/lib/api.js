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

export async function deleteModel(name) {
  const r = await fetch(`/api/models/${encodeURIComponent(name)}`, { method: 'DELETE' });
  if (!r.ok) {
    const body = await r.text().catch(() => '');
    throw new Error(`delete failed (${r.status}): ${body}`);
  }
  return await r.json();
}

export async function unloadModel(name) {
  const r = await fetch(`/api/models/${encodeURIComponent(name)}/unload`, { method: 'POST' });
  if (!r.ok) {
    const body = await r.text().catch(() => '');
    throw new Error(`unload failed (${r.status}): ${body}`);
  }
  return await r.json();
}

/**
 * Stream a model pull. Calls onEvent for each NDJSON event Ollama emits.
 * Returns { done, abort } — await done; call abort to cancel.
 *
 * @param {string} name
 * @param {(evt: {status: string, total?: number, completed?: number, error?: string}) => void} onEvent
 * @returns {{ done: Promise<void>, abort: () => void }}
 */
export function pullModel(name, onEvent) {
  const ctrl = new AbortController();
  const done = (async () => {
    const resp = await fetch('/api/pull', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ model: name }),
      signal: ctrl.signal
    });
    if (!resp.ok) throw new Error(`pull failed: ${resp.status}`);
    if (!resp.body) throw new Error('pull failed: empty response body');
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done: streamDone } = await reader.read();
      if (streamDone) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n\n');
      buf = lines.pop();
      for (const block of lines) {
        const line = block.split('\n').find((l) => l.startsWith('data: '));
        if (!line) continue;
        try {
          onEvent(JSON.parse(line.slice(6)));
        } catch (_e) {
          /* skip malformed event */
        }
      }
    }
  })();
  return { done, abort: () => ctrl.abort() };
}

/**
 * Stream the diagnostic run. Calls onEvent for each NDJSON event the backend emits.
 * Returns { done, abort } — await done; call abort to cancel.
 *
 * @param {(evt: {type: string, [key: string]: any}) => void} onEvent
 * @returns {{ done: Promise<void>, abort: () => void }}
 */
export function runDiagnostic(onEvent) {
  const ctrl = new AbortController();
  const done = (async () => {
    const resp = await fetch('/api/diagnostic', {
      method: 'POST',
      signal: ctrl.signal
    });
    if (!resp.ok) throw new Error(`diagnostic failed: ${resp.status}`);
    if (!resp.body) throw new Error('diagnostic failed: empty response body');
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done: streamDone } = await reader.read();
      if (streamDone) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n\n');
      buf = lines.pop();
      for (const block of lines) {
        const line = block.split('\n').find((l) => l.startsWith('data: '));
        if (!line) continue;
        try {
          onEvent(JSON.parse(line.slice(6)));
        } catch (_e) {
          /* skip malformed event */
        }
      }
    }
  })();
  return { done, abort: () => ctrl.abort() };
}

export async function getDiagnosticChecks() {
  const r = await fetch('/api/diagnostic/checks');
  if (!r.ok) throw new Error('failed to load diagnostic checks');
  return (await r.json()).checks || [];
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
