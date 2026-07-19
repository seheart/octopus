import { describe, expect, it } from 'vitest';
import { modelHints } from './modelHints.js';

function model(name, family, params) {
  return { name, details: { family, parameter_size: params } };
}

describe('modelHints', () => {
  it('flags embeddings as non-chat', () => {
    const h = modelHints(model('nomic-embed-text:latest', 'nomic-bert', '137M'));
    expect(h.chatCapable).toBe(false);
    expect(h.tryPrompt).toBeNull();
    expect(h.bestFor).toMatch(/RAG/i);
  });

  it('recognizes coder models', () => {
    const h = modelHints(model('qwen2.5-coder:14b', 'qwen2', '14.8B'));
    expect(h.bestFor).toMatch(/code/i);
    expect(h.tryPrompt).toMatch(/debug|Python|function/i);
    expect(h.chatCapable).toBe(true);
  });

  it('recognizes reasoning models (qwen3, r1, qwq)', () => {
    expect(modelHints(model('qwen3:14b', 'qwen3', '14.8B')).bestFor).toMatch(/reason/i);
    expect(modelHints(model('deepseek-r1:14b', 'qwen2', '14B')).bestFor).toMatch(/reason/i);
    expect(modelHints(model('qwq:32b', 'qwen2', '32B')).bestFor).toMatch(/reason/i);
  });

  it('is honest about vision models — no image-paste instructions in a text-only app', () => {
    const g = modelHints(model('gemma3:12b', 'gemma3', '12.2B'));
    expect(g.bestFor).toMatch(/text-only/i);
    expect(g.tryPrompt).not.toMatch(/paste|screenshot|photo/i);
    const l = modelHints(model('llava:13b', 'llama', '13B'));
    expect(l.bestFor).toMatch(/text-only/i);
  });

  it('flags small models as fast', () => {
    const h = modelHints(model('llama3.2:3b', 'llama', '3.0B'));
    expect(h.bestFor).toMatch(/fast|quick/i);
  });

  it('flags heavy models as thoughtful', () => {
    const h = modelHints(model('llama3.3:70b', 'llama', '70.6B'));
    expect(h.bestFor).toMatch(/thoughtful|careful/i);
  });

  it('falls back to general for mid-sized non-specialized models', () => {
    const h = modelHints(model('llama3.1:8b', 'llama', '8.0B'));
    expect(h.bestFor).toMatch(/general|chat|writing/i);
    expect(h.tryPrompt).toBeTruthy();
  });

  it('handles missing parameter_size gracefully', () => {
    const h = modelHints({ name: 'mystery:latest', details: {} });
    expect(h.bestFor).toMatch(/general/i);
    expect(h.chatCapable).toBe(true);
  });
});
