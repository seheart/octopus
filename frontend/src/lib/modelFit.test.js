import { describe, it, expect } from 'vitest';
import { parseApproxSize, modelFit } from './modelFit.js';

const GB = 1e9;

describe('parseApproxSize', () => {
  it('parses GB strings', () => {
    expect(parseApproxSize('~2 GB')).toBe(2e9);
    expect(parseApproxSize('4.7 GB')).toBe(4.7e9);
  });
  it('parses MB strings', () => {
    expect(parseApproxSize('~270 MB')).toBe(270e6);
  });
  it('returns 0 for unparseable input', () => {
    expect(parseApproxSize('')).toBe(0);
    expect(parseApproxSize(undefined)).toBe(0);
    expect(parseApproxSize('a lot')).toBe(0);
  });
});

describe('modelFit', () => {
  it('is unknown without a size or without hardware data', () => {
    expect(modelFit(0, { ramBytes: 32 * GB }).tier).toBe('unknown');
    expect(modelFit(4 * GB, {}).tier).toBe('unknown');
  });

  it('runs great when the model fits in VRAM with headroom', () => {
    const fit = modelFit(4 * GB, { ramBytes: 32 * GB, vramBytes: 12 * GB });
    expect(fit.tier).toBe('great');
    expect(fit.label).toBe('Runs great');
  });

  it('is tight when it spills out of VRAM but RAM holds it', () => {
    // 12 GB model, 8 GB VRAM, 32 GB RAM — loads, partially offloads.
    const fit = modelFit(12 * GB, { ramBytes: 32 * GB, vramBytes: 8 * GB });
    expect(fit.tier).toBe('tight');
    expect(fit.detail).toMatch(/VRAM/);
  });

  it('is tight on a GPU-less machine with enough RAM', () => {
    const fit = modelFit(4 * GB, { ramBytes: 32 * GB, vramBytes: 0 });
    expect(fit.tier).toBe('tight');
    expect(fit.detail).toMatch(/no GPU/);
  });

  it("won't fit when the model is larger than total memory", () => {
    const fit = modelFit(20 * GB, { ramBytes: 8 * GB, vramBytes: 0 });
    expect(fit.tier).toBe('wont-fit');
    expect(fit.label).toBe("Won't fit");
  });

  it("won't fit a model that needs more than the spare RAM", () => {
    // The real incident: gemma3:12b (~8.15 GB) on an 8.6 GB Mac froze it.
    // Total RAM looks "almost enough" — but the OS needs its share, so this
    // must read as wont-fit, not tight.
    const fit = modelFit(8.15 * GB, { ramBytes: 8.59 * GB, vramBytes: 0 });
    expect(fit.tier).toBe('wont-fit');
  });

  it('clears a small model on the same machine as tight', () => {
    // gemma3:4b (~3.3 GB) on the same 8.6 GB Mac — snug but runnable.
    const fit = modelFit(3.3 * GB, { ramBytes: 8.59 * GB, vramBytes: 0 });
    expect(fit.tier).toBe('tight');
  });

  it('treats VRAM as usable memory when RAM is unknown', () => {
    // No RAM figure, but a big GPU — should still read as great.
    expect(modelFit(4 * GB, { vramBytes: 24 * GB }).tier).toBe('great');
  });
});
