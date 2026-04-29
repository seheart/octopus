<script>
  const { title, children } = $props();
</script>

<section>
  <h2 class="text-xs uppercase tracking-wider text-muted mb-2 font-mono">{title}</h2>
  {@render children?.()}
</section>
