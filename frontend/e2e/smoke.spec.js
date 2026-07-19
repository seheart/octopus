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

  await page.route('**/api/ollama', (route) =>
    route.fulfill({
      json: { reachable: true, version: '0.17.4', url: 'http://127.0.0.1:11434' }
    })
  );

  await page.route('**/api/host', (route) =>
    route.fulfill({
      json: {
        cpu: { model: 'Intel i7-12700K', cores: 20 },
        memory: {
          total_bytes: 64 * 1024 ** 3,
          available_bytes: 40 * 1024 ** 3,
          used_bytes: 24 * 1024 ** 3
        },
        disk: {
          total_bytes: 1000 * 1024 ** 3,
          used_bytes: 600 * 1024 ** 3,
          free_bytes: 400 * 1024 ** 3
        },
        uptime_seconds: 90000
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
  await expect(nav.getByRole('button', { name: 'chat', exact: true })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'models', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Settings' })).toBeVisible();
});

test('footer nav routes to Storage, System, Diagnostic', async ({ page }) => {
  await page.goto('/');
  const footerNav = page.getByRole('navigation', { name: 'Footer navigation' });

  await footerNav.getByRole('button', { name: 'Storage', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Storage', exact: true })).toBeVisible();

  await footerNav.getByRole('button', { name: 'System', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'System', exact: true })).toBeVisible();

  await footerNav.getByRole('button', { name: 'Diagnostic', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Diagnostic', exact: true })).toBeVisible();
});

test('footer nav routes to Design, Labs, Roadmap, About', async ({ page }) => {
  await page.goto('/');
  const footerNav = page.getByRole('navigation', { name: 'Footer navigation' });

  await footerNav.getByRole('button', { name: 'Design', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Design System' })).toBeVisible();

  await footerNav.getByRole('button', { name: 'Labs', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Labs', exact: true })).toBeVisible();

  await footerNav.getByRole('button', { name: 'Roadmap', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Roadmap', exact: true })).toBeVisible();

  await footerNav.getByRole('button', { name: 'About', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'About', exact: true })).toBeVisible();
});

test('system page shows host, ollama, gpu, inventory', async ({ page }) => {
  await page.goto('/#/system');
  await expect(page.getByRole('heading', { name: 'System', exact: true })).toBeVisible();
  await expect(page.getByText('Intel i7-12700K')).toBeVisible();
  await expect(page.getByText('0.17.4')).toBeVisible();
  await expect(page.getByText('NVIDIA RTX 5070')).toBeVisible();
});

test('models page lists available models', async ({ page }) => {
  await page.goto('/#/models');
  await expect(page.getByRole('heading', { name: 'Models' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Use llama3.1:8b in chat' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Use qwen3:14b in chat' })).toBeVisible();
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
