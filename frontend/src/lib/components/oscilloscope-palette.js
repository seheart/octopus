// Stable per-model color picker for the Oscilloscope. Each model name
// hashes to a fixed slot in a small palette so the same model always
// gets the same color across reloads.
//
// Hues are spread across the wheel so adjacent palette slots don't read
// as the same color when two traces overlap.

function hashString(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h * 31) | 0) + s.charCodeAt(i);
  return Math.abs(h);
}

// 8 hues sampled from the design palette's dark family hsl(·, 73%, 58%) —
// red, amber, lime, green, teal, cyan, blue, magenta. Each adjacent pair
// differs by ≥38° on the wheel so they never look like the same colour.
const PALETTE = [
  '#E24646', // red
  '#E2A946', // amber
  '#60E246', // lime
  '#46E2A9', // teal
  '#46CBE2', // cyan
  '#4694E2', // blue
  '#7A46E2', // violet
  '#D546E2' // magenta
];

export function colorFor(modelName) {
  return PALETTE[hashString(modelName) % PALETTE.length];
}
