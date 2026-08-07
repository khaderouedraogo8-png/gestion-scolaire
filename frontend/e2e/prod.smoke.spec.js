import { test, expect } from '@playwright/test';

test.describe('Prod smoke', () => {
  test('page login accessible', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Connexion' })).toBeVisible();
  });

  test('login admin et tableau de bord', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/Adresse email/i).fill('admin@ecole.local');
    await page.getByLabel(/Mot de passe/i).fill('Admin123!');
    await page.getByRole('button', { name: 'Se connecter' }).click();
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.getByRole('heading', { name: 'Tableau de bord' })).toBeVisible();
  });

  test('API health via nginx', async ({ request }) => {
    const res = await request.get('/api/health');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('ok');
    expect(body.redis).toBe('ok');
  });

  test('swagger désactivé en prod', async ({ request }) => {
    const res = await request.get('/api/docs');
    expect(res.status()).toBe(404);
  });
});
