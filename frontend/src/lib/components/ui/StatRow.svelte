<script>
  /**
   * StatRow — a label/value line. Pass `hint` to explain a jargon label
   * on hover — handy for newcomers to local LLMs.
   */
  const { label, value, accent = false, hint = '' } = $props();
</script>

<div class="flex justify-between text-xs font-mono">
  <span class="text-muted" class:cursor-help={hint} title={hint || undefined}>{label}</span>
  <span class={accent ? 'text-accent' : 'text-body'}>{value}</span>
</div>
