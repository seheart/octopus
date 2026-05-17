<script>
  const { size = 18, color = null, bg = null } = $props();

  const fillColor = $derived(color ?? 'var(--logo, var(--text-heading))');
  const eyeColor = $derived(bg ?? 'var(--bg)');
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 64 64"
  xmlns="http://www.w3.org/2000/svg"
  aria-label="Octopus logo"
  role="img"
  style="color: {fillColor};"
>
  <!-- Head -->
  <path
    d="M32 8c-11 0-19 8-19 19v4c0 3 2 4 4 4h30c2 0 4-1 4-4v-4c0-11-8-19-19-19z"
    fill="currentColor"
  />
  <!-- Eyes (background-color punch-outs) -->
  <circle cx="25" cy="22" r="2.5" style="fill: {eyeColor};" />
  <circle cx="39" cy="22" r="2.5" style="fill: {eyeColor};" />
  <!-- 8 tentacles -->
  <g fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">
    <path d="M17 35 Q13 42 16 50 Q19 55 14 60" />
    <path d="M22 35 Q20 44 24 51 Q26 56 22 60" />
    <path d="M27 35 Q26 46 28 53 Q29 58 26 61" />
    <path d="M31 35 Q31 48 30 60" />
    <path d="M35 35 Q35 48 36 60" />
    <path d="M39 35 Q40 46 38 53 Q37 58 40 61" />
    <path d="M44 35 Q46 44 42 51 Q40 56 44 60" />
    <path d="M49 35 Q53 42 50 50 Q47 55 52 60" />
  </g>
</svg>
