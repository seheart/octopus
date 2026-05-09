<script>
  import { onMount } from 'svelte';
  import { getDiagnosticChecks, runDiagnostic } from '../api.js';
  import { Button, Card, Section } from '../components/ui/index.js';

  /** @type {Array<{id:string, name:string, category:string, status?:string, duration_ms?:number, detail?:string, expanded?:boolean}>} */
  let checks = $state([]);
  let running = $state(false);
  let runFinishedAt = $state(null);
  let summary = $state(null);
  let totalMs = $state(null);
  let err = $state(null);
  let runningId = $state('');
  let currentRun = $state(null);
  let copied = $state(false);

  onMount(async () => {
    try {
      const list = await getDiagnosticChecks();
      checks = list.map((c) => ({ ...c, status: undefined, expanded: false }));
    } catch (e) {
      err = e.message;
    }
  });

  // Group rows by category for the sectioned UI
  const grouped = $derived.by(() => {
    /** @type {Record<string, typeof checks>} */
    const g = {};
    for (const c of checks) {
      if (!g[c.category]) g[c.category] = [];
      g[c.category].push(c);
    }
    return g;
  });

  // Aggregate verdict — fail beats warn beats pass; running while any check is running.
  const overall = $derived.by(() => {
    if (running) return 'running';
    if (!summary) return 'idle';
    if (summary.fail > 0) return 'fail';
    if (summary.warn > 0) return 'warn';
    return 'pass';
  });

  const overallText = {
    idle: 'Not run yet',
    running: 'Running checks…',
    pass: 'All checks passed',
    warn: 'Passed with warnings',
    fail: 'Issues found'
  };

  function statusColor(status) {
    if (status === 'pass') return 'text-success';
    if (status === 'warn') return 'text-warning';
    if (status === 'fail') return 'text-error';
    return 'text-muted';
  }

  function statusBg(status) {
    if (status === 'pass') return 'bg-success';
    if (status === 'warn') return 'bg-warning';
    if (status === 'fail') return 'bg-error';
    return 'bg-surface-2';
  }

  async function runAll() {
    if (running) return;
    err = null;
    summary = null;
    totalMs = null;
    runFinishedAt = null;
    // Reset prior results
    checks = checks.map((c) => ({
      ...c,
      status: undefined,
      duration_ms: undefined,
      detail: undefined,
      expanded: false
    }));
    running = true;
    try {
      currentRun = runDiagnostic((evt) => {
        if (evt.type === 'running') {
          runningId = evt.id;
        } else if (evt.type === 'check') {
          checks = checks.map((c) =>
            c.id === evt.id
              ? {
                  ...c,
                  status: evt.status,
                  duration_ms: evt.duration_ms,
                  detail: evt.detail
                }
              : c
          );
        } else if (evt.type === 'done') {
          summary = evt.summary;
          totalMs = evt.duration_ms;
          runFinishedAt = new Date();
          runningId = '';
        }
      });
      await currentRun.done;
    } catch (e) {
      if (e.name !== 'AbortError') err = e.message;
    } finally {
      running = false;
      currentRun = null;
      runningId = '';
    }
  }

  function cancel() {
    currentRun?.abort();
  }

  function toggle(id) {
    checks = checks.map((c) => (c.id === id ? { ...c, expanded: !c.expanded } : c));
  }

  function copyReport() {
    const lines = [];
    lines.push('# Octopus diagnostic report');
    if (runFinishedAt) {
      lines.push('');
      lines.push(`Run at: ${runFinishedAt.toISOString()}`);
      if (totalMs !== null) lines.push(`Duration: ${(totalMs / 1000).toFixed(1)}s`);
      if (summary)
        lines.push(`Summary: pass=${summary.pass} warn=${summary.warn} fail=${summary.fail}`);
    }
    for (const cat of Object.keys(grouped)) {
      lines.push('');
      lines.push(`## ${cat}`);
      for (const c of grouped[cat]) {
        const status = c.status ? c.status.toUpperCase() : 'NOT RUN';
        const dur = c.duration_ms !== undefined ? ` (${c.duration_ms}ms)` : '';
        lines.push('');
        lines.push(`### [${status}] ${c.name}${dur}`);
        if (c.detail) {
          lines.push('```');
          lines.push(c.detail);
          lines.push('```');
        }
      }
    }
    navigator.clipboard.writeText(lines.join('\n'));
    copied = true;
    setTimeout(() => (copied = false), 1500);
  }
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-heading mb-1">Diagnostic</h1>
      <p class="text-sm text-muted">
        One-click code review, audit, and runtime health check. Each row runs server-side and
        streams its result back as it finishes.
      </p>
    </div>

    <!-- Hero: run button + overall status -->
    <Card padding="lg">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3 min-w-0">
          <span
            class="inline-block w-3 h-3 rounded-full {statusBg(overall)} {overall === 'running'
              ? 'animate-pulse'
              : ''}"
            aria-hidden="true"
          ></span>
          <div class="min-w-0">
            <div class="text-heading font-medium truncate">{overallText[overall]}</div>
            {#if summary}
              <div class="text-xs text-muted font-mono">
                <span class="text-success">{summary.pass} pass</span>
                · <span class="text-warning">{summary.warn} warn</span>
                · <span class="text-error">{summary.fail} fail</span>
                {#if totalMs !== null}
                  · {(totalMs / 1000).toFixed(1)}s
                {/if}
              </div>
            {:else if running}
              <div class="text-xs text-muted font-mono">
                {checks.find((c) => c.id === runningId)?.name || 'starting…'}
              </div>
            {/if}
          </div>
        </div>
        <div class="flex items-center gap-2">
          {#if summary}
            <Button variant="secondary" onclick={copyReport}>
              {copied ? 'copied!' : 'copy report'}
            </Button>
          {/if}
          {#if running}
            <Button variant="secondary" onclick={cancel}>cancel</Button>
          {:else}
            <Button variant="primary" onclick={runAll}>
              {summary ? 're-run all' : 'run all checks'}
            </Button>
          {/if}
        </div>
      </div>
      {#if err}
        <div class="text-error text-sm font-mono mt-3">error: {err}</div>
      {/if}
    </Card>

    {#if checks.length === 0 && !err}
      <div class="text-muted text-sm font-mono">loading checks…</div>
    {/if}

    {#each Object.entries(grouped) as [category, rows] (category)}
      <Card padding="lg">
        <Section title={category}>
          <div class="space-y-1">
            {#each rows as c (c.id)}
              <div
                class="border border-transparent rounded {c.status === 'fail'
                  ? 'border-l-2 border-l-error pl-2'
                  : c.status === 'warn'
                    ? 'border-l-2 border-l-warning pl-2'
                    : c.status === 'pass'
                      ? 'border-l-2 border-l-success pl-2'
                      : ''}"
              >
                <button
                  onclick={() => c.detail && toggle(c.id)}
                  class="w-full flex items-center justify-between gap-3 py-2 text-left {c.detail
                    ? 'cursor-pointer hover:bg-surface-2'
                    : 'cursor-default'} rounded px-2"
                  aria-expanded={!!c.expanded}
                >
                  <div class="flex items-center gap-3 min-w-0">
                    <span
                      class="text-[10px] uppercase tracking-wider font-mono {statusColor(
                        c.status
                      )} w-12 shrink-0"
                    >
                      {#if c.id === runningId && running}
                        ⋯
                      {:else if c.status}
                        {c.status}
                      {:else}
                        —
                      {/if}
                    </span>
                    <span class="text-sm text-body truncate">{c.name}</span>
                  </div>
                  <div class="flex items-center gap-2 text-xs font-mono text-muted shrink-0">
                    {#if c.duration_ms !== undefined}
                      <span>{c.duration_ms}ms</span>
                    {/if}
                    {#if c.detail}
                      <span aria-hidden="true">{c.expanded ? '▾' : '▸'}</span>
                    {/if}
                  </div>
                </button>
                {#if c.expanded && c.detail}
                  <pre
                    class="text-[11px] font-mono text-body bg-surface-2 rounded px-3 py-2 mx-2 mb-2 whitespace-pre-wrap break-words overflow-x-auto">{c.detail}</pre>
                {/if}
              </div>
            {/each}
          </div>
        </Section>
      </Card>
    {/each}
  </div>
</div>
