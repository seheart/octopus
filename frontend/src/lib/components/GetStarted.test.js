import { describe, it, expect } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import GetStarted from './GetStarted.svelte';
import { route } from '../stores/route.svelte.js';
import { consumePendingPull } from '../stores/model.svelte.js';

describe('GetStarted', () => {
  it('step 1 is active when Ollama is unreachable', () => {
    const { getByText, container } = render(GetStarted, {
      props: { ollamaReachable: false, hasModels: false }
    });
    expect(getByText("Ollama isn't running")).toBeTruthy();
    // The exact command a fresh user needs, plus the auto-connect hint.
    expect(container.textContent).toContain('ollama serve');
    expect(container.textContent).toContain('waiting for Ollama');
  });

  it('keeps the model step locked until Ollama is reachable', () => {
    const { queryByText, getByText } = render(GetStarted, {
      props: { ollamaReachable: false, hasModels: false }
    });
    // No pull button while Ollama is down — a pull needs the daemon running.
    expect(queryByText('Pull llama3.2:3b')).toBeNull();
    expect(getByText(/Start Ollama first/)).toBeTruthy();
  });

  it('offers a one-click starter pull once Ollama is up', () => {
    const { getByText, container } = render(GetStarted, {
      props: { ollamaReachable: true, hasModels: false }
    });
    expect(getByText('Ollama is running')).toBeTruthy();
    expect(getByText('No models yet')).toBeTruthy();
    expect(getByText('Pull llama3.2:3b')).toBeTruthy();
    // Step 1 done — its serve command is no longer shown.
    expect(container.textContent).not.toContain('$ ollama serve');
  });

  it('renders the done state when both steps are satisfied', () => {
    const { getByText, queryByText } = render(GetStarted, {
      props: { ollamaReachable: true, hasModels: true }
    });
    expect(getByText('Ollama is running')).toBeTruthy();
    expect(getByText('A model is installed')).toBeTruthy();
    expect(queryByText('Pull llama3.2:3b')).toBeNull();
  });

  it('"Pull llama3.2:3b" seeds the pull and routes to the pull page', async () => {
    const { getByText } = render(GetStarted, {
      props: { ollamaReachable: true, hasModels: false }
    });
    await fireEvent.click(getByText('Pull llama3.2:3b'));
    expect(route.page).toBe('pull');
    expect(consumePendingPull()).toBe('llama3.2:3b');
  });
});
