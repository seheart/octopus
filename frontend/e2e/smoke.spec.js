import { expect, test } from '@playwright/test';

// Mock all backend calls so E2E tests are deterministic and don't need
// a real Ollama instance running.
test.beforeEach(async ({ page }) => {
  await page.route('**/api/models', (route) =>
    route.fulfill({
      json: {
        models: [
          {
            name: 'llama3.1:8b',
            size: 4920753328,
            modified_at: new Date().toISOString(),
            details: {
              parameter_size: '8.0B',
              quantization_level: 'Q4_K_M',
              family: 'llama'
            }
          },
          {
            name: 'qwen3:14b',
            size: 9276198565,
            modified_at: new Date().toISOString(),
            details: {
              parameter_size: '14.8B',
              quantization_level: 'Q4_K_M',
              family: 'qwen3'
            }
          }
        ]
      }
    })
  );

  await page.route('**/api/loaded', (route) =>
    route.fulfill({
      json: {
        models: [
          {
            name: 'qwen3:14b',
            size: 9276198565,
            size_vram: 9000000000,
            details: { parameter_size: '14.8B', quantization_level: 'Q4_K_M' },
            context_length: 4096
          }
        ]
      }
    })
  );

  await page.route('**/api/gpu', (route) =>
    route.fulfill({
      json: {
        available: true,
        gpus: [
          {
            name: 'NVIDIA RTX 5070',
            memory_used_mb: 9000,
            memory_total_mb: 12000,
            utilization_pct: 25,
            temp_c: 50
          }
        ]
      }
    })
  );
});

test('chat page loads and shows the model picker', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Octopus home' })).toBeVisible();
  await expect(page.locator('select').first()).toBeVisible();
  await expect(page.getByPlaceholder(/message/i)).toBeVisible();
});

test('header has Chat and Models tabs and a Settings link', async ({ page }) => {
  await page.goto('/');
  const nav = page.getByRole('navigation', { name: 'Primary' });
  await expect(nav.getByRole('button', { name: 'Chat' })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'Models' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Settings' })).toBeVisible();
});

test('footer nav routes to System, Design, Roadmap, About', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: 'System page', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'System', exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Design system page' }).click();
  await expect(page.getByRole('heading', { name: 'Design System' })).toBeVisible();

  await page.getByRole('button', { name: 'Roadmap page' }).click();
  await expect(page.getByRole('heading', { name: 'Roadmap', exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'About page' }).click();
  await expect(page.getByRole('heading', { name: 'About', exact: true })).toBeVisible();
});

test('models page lists available models', async ({ page }) => {
  await page.goto('/#/models');
  await expect(page.getByRole('heading', { name: 'Models' })).toBeVisible();
  await expect(page.getByText('llama3.1:8b')).toBeVisible();
  await expect(page.getByText('qwen3:14b')).toBeVisible();
});

test('theme toggle switches the html dark class', async ({ page }) => {
  await page.goto('/');

  const initialIsDark = await page.evaluate(() =>
    document.documentElement.classList.contains('dark')
  );
  await page.getByRole('button', { name: /switch to (light|dark) theme/i }).click();
  const afterIsDark = await page.evaluate(() =>
    document.documentElement.classList.contains('dark')
  );
  expect(afterIsDark).toBe(!initialIsDark);
});

test('footer shows Ollama connected dot and model count', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('2 models')).toBeVisible();
  // The connection dot has title "Ollama connected" when reachable
  await expect(page.locator('[title="Ollama connected"]')).toBeVisible();
});

test('GitHub link points at the repo', async ({ page }) => {
  await page.goto('/');
  const link = page.getByRole('link', { name: 'View source on GitHub' });
  await expect(link).toHaveAttribute('href', 'https://github.com/seheart/octopus');
  await expect(link).toHaveAttribute('target', '_blank');
});
