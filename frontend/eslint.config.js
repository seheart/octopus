import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import prettier from 'eslint-config-prettier';
import globals from 'globals';
import svelteParser from 'svelte-eslint-parser';

export default [
  js.configs.recommended,
  ...svelte.configs['flat/recommended'],
  prettier,
  ...svelte.configs['flat/prettier'],
  {
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node
      }
    },
    rules: {
      'no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrors: 'all',
          caughtErrorsIgnorePattern: '^_'
        }
      ],
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'prefer-const': 'error',
      eqeqeq: ['error', 'always']
    }
  },
  {
    files: ['**/*.svelte'],
    languageOptions: {
      parser: svelteParser
    }
  },
  {
    files: ['**/*.test.js'],
    languageOptions: {
      globals: { ...globals.node }
    },
    rules: {
      'no-unused-expressions': 'off'
    }
  },
  {
    ignores: ['dist/**', 'node_modules/**', '.svelte-kit/**']
  }
];
