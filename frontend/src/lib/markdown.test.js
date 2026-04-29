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
});
