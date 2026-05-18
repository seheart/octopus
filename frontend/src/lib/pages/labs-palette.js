// Hex literals live here, not in LabsPage.svelte, so the design-system
// pattern check (scripts/validate-patterns.sh) stays strict for components.
// This page is the one place the app intentionally renders unmapped colors —
// it's a swatch lab for picking the wired --logo value.

export const DARK_BG = '#0a0a0a';
export const LIGHT_BG = '#f6f4ef';

export const PICKED_DARK = '#D546E2';
export const PICKED_LIGHT = '#86298E';

// Dark-mode picks against #0a0a0a — bright, saturated, CRT/neon energy.
// "magenta" is the family magenta — same (S, L) as the semantic palette.
export const darkOptions = [
  { name: 'plasma', hex: '#22D3EE', note: 'terminal cyan — out-of-family' },
  { name: 'phosphor', hex: '#A3E635', note: 'CRT lime — out-of-family' },
  { name: 'magenta', hex: '#D546E2', note: 'family magenta — hue 295° at family (S, L)' },
  { name: 'ember', hex: '#FBBF24', note: 'vintage amber — out-of-family' }
];

// Light-mode picks against #f6f4ef — deeper, saturated, still tech.
// "magenta" is the family magenta — same (S, L) as the semantic palette.
export const lightOptions = [
  { name: 'cobalt', hex: '#2563EB', note: 'electric blue — out-of-family' },
  { name: 'emerald', hex: '#047857', note: 'forest green — out-of-family' },
  { name: 'violet', hex: '#7C3AED', note: 'royal violet — out-of-family' },
  { name: 'magenta', hex: '#86298E', note: 'family magenta — hue 295° at family (S, L)' },
  { name: 'teal', hex: '#0D9488', note: 'deep terminal teal — out-of-family' },
  { name: 'indigo', hex: '#4338CA', note: 'moodier blue — out-of-family' },
  { name: 'burnt', hex: '#C2410C', note: 'burnt orange — out-of-family' },
  { name: 'carbon', hex: '#18181B', note: 'near-black — minimal monochrome' }
];
