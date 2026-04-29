<script>
  const { label, value, accent = false } = $props();
</script>

<div class="flex justify-between text-xs font-mono">
  <span class="text-muted">{label}</span>
  <span class={accent ? 'text-accent' : 'text-body'}>{value}</span>
</div>
