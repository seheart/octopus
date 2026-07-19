// The shipped palette, in source-of-truth form. Hex literals live in a .js
// file (not DesignPage.svelte) so the design-system pattern check stays
// strict for component code.

export const DARK_BG = '#0a0a0a';
export const LIGHT_BG = '#f6f4ef';

export const DARK_PROFILE = 'hsl(·, 73%, 58%)';
export const LIGHT_PROFILE = 'hsl(·, 55%, 36%)';

// Ten hues, ordered around the wheel. Four are wired as semantic tokens
// (accent, success, error, warning); the rest are available for charts,
// the oscilloscope, illustrations, or future semantic roles. Adding new
// hues = keep the S/L, change only the hue.
export const darkFamily = [
  { name: 'red', hex: '#E24646', hue: '0°', role: 'error' },
  { name: 'amber', hex: '#E2A946', hue: '38°', role: 'warning' },
  { name: 'yellow', hex: '#E2E246', hue: '60°' },
  { name: 'lime', hex: '#60E246', hue: '110°' },
  { name: 'green', hex: '#46E27C', hue: '141°', role: 'accent' },
  { name: 'teal', hex: '#46E2A9', hue: '158°', role: 'success' },
  { name: 'cyan', hex: '#46CBE2', hue: '189°' },
  { name: 'blue', hex: '#4694E2', hue: '210°' },
  { name: 'violet', hex: '#7A46E2', hue: '260°' },
  { name: 'magenta', hex: '#D546E2', hue: '295°' }
];

export const lightFamily = [
  { name: 'red', hex: '#8E2929', hue: '0°', role: 'error' },
  { name: 'amber', hex: '#8E6929', hue: '38°', role: 'warning' },
  { name: 'yellow', hex: '#8E8E29', hue: '60°' },
  { name: 'lime', hex: '#3A8E29', hue: '110°' },
  { name: 'green', hex: '#298E4D', hue: '141°', role: 'accent' },
  { name: 'teal', hex: '#298E69', hue: '158°', role: 'success' },
  { name: 'cyan', hex: '#297F8E', hue: '189°' },
  { name: 'blue', hex: '#295C8E', hue: '210°' },
  { name: 'violet', hex: '#4B298E', hue: '260°' },
  { name: 'magenta', hex: '#86298E', hue: '295°' }
];
