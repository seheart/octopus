import { describe, it, expect } from 'vitest';
import { fmtBytes, fmtParams, ollamaTimeAgo } from './api.js';

describe('fmtBytes', () => {
  it('formats GB for >=1GB', () => {
    expect(fmtBytes(2_500_000_000)).toBe('2.5 GB');
  });
  it('formats MB for <1GB', () => {
    expect(fmtBytes(500_000_000)).toBe('500 MB');
  });
  it('returns dash for zero/null', () => {
    expect(fmtBytes(0)).toBe('–');
    expect(fmtBytes(null)).toBe('–');
  });
});

describe('fmtParams', () => {
  it('strips trailing .0 from B', () => {
    expect(fmtParams('8.0B')).toBe('8B');
    expect(fmtParams('14.8B')).toBe('14.8B');
  });
  it('handles empty', () => {
    expect(fmtParams('')).toBe('');
    expect(fmtParams(undefined)).toBe('');
  });
});

describe('ollamaTimeAgo', () => {
  it('returns "just now" for very recent', () => {
    expect(ollamaTimeAgo(new Date().toISOString())).toBe('just now');
  });
  it('returns days for older', () => {
    const d = new Date(Date.now() - 3 * 86400000);
    expect(ollamaTimeAgo(d.toISOString())).toBe('3d ago');
  });
});
