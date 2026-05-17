// Hex literals live here, not in LabsPage.svelte, so the design-system
// pattern check (scripts/validate-patterns.sh) stays strict for components.
// This page is the one place the app intentionally renders unmapped colors —
// it's a swatch lab for picking the wired --logo value.

export const DARK_BG = '#0a0a0a';
export const LIGHT_BG = '#f6f4ef';

export const PICKED_DARK = '#22D3EE';
export const PICKED_LIGHT = '#BE185D';

// Dark-mode picks against #0a0a0a — bright, saturated, CRT/neon energy.
export const darkOptions = [
  { name: 'plasma', hex: '#22D3EE', note: 'terminal cyan — matches the current vibe' },
  { name: 'phosphor', hex: '#A3E635', note: 'CRT lime — pure AI-green' },
  { name: 'neon', hex: '#F472B6', note: 'synthwave magenta — pops hardest' },
  { name: 'ember', hex: '#FBBF24', note: 'vintage amber — old-terminal warm' }
];

// Light-mode picks against #f6f4ef — deeper, saturated, still tech.
export const lightOptions = [
  { name: 'cobalt', hex: '#2563EB', note: 'electric blue — heaviest contrast' },
  { name: 'emerald', hex: '#047857', note: 'forest green — cohesion with phosphor' },
  { name: 'violet', hex: '#7C3AED', note: 'royal violet — modern AI' },
  { name: 'magenta', hex: '#BE185D', note: 'deep pink — confident pop' },
  { name: 'teal', hex: '#0D9488', note: 'deep terminal teal' },
  { name: 'indigo', hex: '#4338CA', note: 'moodier, deeper blue' },
  { name: 'burnt', hex: '#C2410C', note: 'burnt orange — terminal warmth' },
  { name: 'carbon', hex: '#18181B', note: 'near-black — minimal monochrome' }
];
