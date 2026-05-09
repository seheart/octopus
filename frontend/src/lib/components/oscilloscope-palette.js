// Stable per-model color picker for the Oscilloscope. Each model name
// hashes to a fixed slot in a small palette so the same model always
// gets the same color across reloads.

function hashString(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h * 31) | 0) + s.charCodeAt(i);
  return Math.abs(h);
}

const PALETTE = [
  '#4ade80', // green
  '#60a5fa', // blue
  '#f472b6', // pink
  '#fbbf24', // amber
  '#a78bfa', // violet
  '#22d3ee' // cyan
];

export function colorFor(modelName) {
  return PALETTE[hashString(modelName) % PALETTE.length];
}
