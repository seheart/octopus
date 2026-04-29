import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import OctoLogo from './OctoLogo.svelte';

describe('OctoLogo', () => {
  it('renders an svg with aria-label', () => {
    const { container } = render(OctoLogo, { props: { size: 24 } });
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    expect(svg.getAttribute('aria-label')).toBe('Octopus logo');
    expect(svg.getAttribute('width')).toBe('24');
  });

  it('has 8 tentacle paths', () => {
    const { container } = render(OctoLogo);
    const tentacles = container.querySelectorAll('g path');
    expect(tentacles.length).toBe(8);
  });
});
