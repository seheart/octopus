<script>
  /**
   * Code — inline code span.
   * @typedef {Object} Props
   * @property {import('svelte').Snippet} [children]
   */

  /** @type {Props} */
  const { children } = $props();
</script>

<code class="font-mono text-xs bg-surface-2 text-body px-1 py-0.5 rounded">
  {@render children?.()}
</code>
