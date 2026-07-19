/**
 * Heuristic "what is this model good for" hints derived from name + family
 * + param count. Pure function — no external data, works on any new model
 * pulled from Ollama tomorrow.
 *
 * Returns { bestFor: string, tryPrompt: string|null, chatCapable: boolean }.
 *
 * The hints intentionally read like a person guiding you, not labels you
 * have to know how to interpret. "Best for X" + "Try: Y" reads naturally
 * regardless of background.
 */

/** @param {string|undefined} s */
function parseParamsB(s) {
  if (!s) return 0;
  const match = String(s).match(/([\d.]+)\s*B/i);
  return match ? parseFloat(match[1]) : 0;
}

/** @param {{name: string, details?: {family?: string, parameter_size?: string}}} model */
export function modelHints(model) {
  const name = (model.name || '').toLowerCase();
  const family = (model.details?.family || '').toLowerCase();
  const params = parseParamsB(model.details?.parameter_size);

  // Embeddings — not a chat model. Show what it's actually for.
  if (name.includes('embed')) {
    return {
      bestFor: 'indexing documents for search and RAG (not a chat model)',
      tryPrompt: null,
      chatCapable: false
    };
  }

  // Code-focused models
  if (name.includes('coder') || name.includes('code') || name.includes('starcoder')) {
    return {
      bestFor: 'writing, refactoring, and debugging code',
      tryPrompt:
        'Help me debug this Python function — it returns None when the list is empty, but I want it to raise.',
      chatCapable: true
    };
  }

  // Reasoning models — qwen3 / deepseek-r1 / qwq / o1 stream chain-of-thought
  if (
    name.startsWith('qwen3') ||
    name.includes('r1') ||
    name.includes('qwq') ||
    name.includes('o1')
  ) {
    return {
      bestFor: 'multi-step problems where you want to see the model reason before answering',
      tryPrompt:
        'A train leaves Boston at 8am going 60mph. Another leaves NYC at 9am going 80mph. Walk through how to figure out where they meet.',
      chatCapable: true
    };
  }

  // Vision / multimodal — these models CAN read images, but Octopus's chat
  // is text-only today (plain textarea, text-only ChatMessage schema). The
  // hint must teach what works here and now, not send users hunting for an
  // upload button that doesn't exist.
  if (family === 'gemma3' || name.includes('llava') || name.includes('vision')) {
    return {
      bestFor:
        'general chat with strong instruction following (it also understands images, but Octopus chat is text-only for now)',
      tryPrompt: 'Rewrite this to be friendlier: "Your request has been denied."',
      chatCapable: true
    };
  }

  // Small / fast — under 4B
  if (params > 0 && params < 4) {
    return {
      bestFor: 'fast everyday questions where you want a quick answer over the most-careful one',
      tryPrompt: 'Explain promises in JavaScript in one short paragraph.',
      chatCapable: true
    };
  }

  // Heavy — 30B+
  if (params >= 30) {
    return {
      bestFor: 'thoughtful, careful answers — slower but stronger on hard or nuanced questions',
      tryPrompt:
        'Explain the differences between SQL JOIN types (inner, left, right, full) with one short example each.',
      chatCapable: true
    };
  }

  // Sensible default for mid-sized general models
  return {
    bestFor: 'general chat, writing, and explanations',
    tryPrompt: 'Explain async/await in JavaScript with a small worked example.',
    chatCapable: true
  };
}
