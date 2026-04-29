<script>
  /**
   * Tag — inline label / badge.
   * @typedef {'neutral' | 'success' | 'error' | 'warning'} Tone
   */

  const { tone = 'neutral', children } = $props();

  const tones = {
    neutral: 'text-muted',
    success: 'text-success',
    error: 'text-error',
    warning: 'text-warning'
  };
</script>

<span
  class="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-surface-2 font-mono {tones[
    tone
  ]}"
>
  {@render children?.()}
</span>
