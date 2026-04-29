<script>
  /**
   * Card — wraps content in surface + border + rounded.
   * @typedef {'sm' | 'md' | 'lg'} Padding
   */

  const { padding = 'md', children } = $props();

  const paddings = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-5'
  };
</script>

<div class="bg-surface border border-border rounded-lg {paddings[padding]}">
  {@render children?.()}
</div>
