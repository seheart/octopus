import { describe, expect, it } from 'vitest';
import { renderMarkdown } from './markdown.js';

describe('renderMarkdown', () => {
  it('renders bold text', () => {
    const html = renderMarkdown('**hello**');
    expect(html).toContain('<strong>hello</strong>');
  });

  it('renders inline code', () => {
    const html = renderMarkdown('use `marked` here');
    expect(html).toContain('<code>marked</code>');
  });

  it('renders a fenced code block', () => {
    const html = renderMarkdown('```\nx = 1\n```');
    expect(html).toMatch(/<pre>.*x = 1.*<\/pre>/s);
  });

  it('strips dangerous HTML (XSS attempt)', () => {
    const html = renderMarkdown('hi <script>alert(1)</script>');
    expect(html).not.toContain('<script>');
  });

  it('strips javascript: URLs in links', () => {
    const html = renderMarkdown('[click](javascript:alert(1))');
    expect(html).not.toContain('javascript:');
  });

  it('returns empty string for empty input', () => {
    expect(renderMarkdown('')).toBe('');
    expect(renderMarkdown(null)).toBe('');
    expect(renderMarkdown(undefined)).toBe('');
  });

  // Prompt-injection guard: model output mustn't be able to render style
  // attrs that fetch a remote URL (background:url(...) exfil).
  it('strips style attributes from raw HTML', () => {
    const html = renderMarkdown('<p style="background:url(http://evil/x)">hi</p>');
    expect(html).not.toContain('style=');
    expect(html).not.toContain('background:url');
  });

  it('strips <style>, <link>, <meta> tags', () => {
    const html = renderMarkdown('<style>body{x:1}</style><link rel="x"><meta name="y">');
    expect(html).not.toContain('<style');
    expect(html).not.toContain('<link');
    expect(html).not.toContain('<meta');
  });

  // Tab-napping guard: model can request target="_blank" but we always
  // force rel="noopener noreferrer", even if the model tried rel="opener".
  it('forces noopener noreferrer on target="_blank" links', () => {
    const html = renderMarkdown('<a href="http://x" target="_blank" rel="opener">click</a>');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('noopener');
    expect(html).toContain('noreferrer');
    expect(html).not.toContain('rel="opener"');
  });
});
