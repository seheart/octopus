<script>
  /**
   * Button — the only sanctioned button primitive.
   * @typedef {Object} Props
   * @property {'primary' | 'secondary' | 'ghost' | 'danger'} [variant]
   * @property {'sm' | 'md' | 'lg'} [size]
   * @property {'button' | 'submit' | 'reset'} [type]
   * @property {boolean} [disabled]
   * @property {(e: MouseEvent) => void} [onclick]
   * @property {string} [title]
   * @property {string} [ariaLabel]
   * @property {import('svelte').Snippet} [children]
   */

  /** @type {Props} */
  const {
    variant = 'secondary',
    size = 'md',
    type = 'button',
    disabled = false,
    onclick,
    title = '',
    ariaLabel = '',
    children
  } = $props();

  const sizes = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-sm px-4 py-2 font-medium'
  };

  const variants = {
    primary: 'bg-accent text-canvas font-medium hover:opacity-90',
    secondary: 'bg-surface-2 text-body border border-border hover:border-accent',
    ghost: 'bg-transparent text-muted hover:text-body hover:bg-surface-2',
    danger: 'bg-error text-canvas font-medium hover:opacity-90'
  };
</script>

<button
  {type}
  {disabled}
  {onclick}
  {title}
  aria-label={ariaLabel || undefined}
  class="rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed
    {sizes[size]} {variants[variant]}"
>
  {@render children?.()}
</button>
