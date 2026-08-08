import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = 'admin@ecole.local';
const ADMIN_PASSWORD = 'Admin123!';

async function loginAsAdmin(page) {
  await page.goto('/login');
  await page.locator('#field-email').fill(ADMIN_EMAIL);
  await page.locator('#field-password').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await page.waitForURL(/\/(dashboard|change-password)/, { timeout: 15000 });
  if (page.url().includes('change-password')) {
    await page.locator('input[name="currentPassword"]').fill(ADMIN_PASSWORD);
    await page.locator('input[name="newPassword"]').fill(ADMIN_PASSWORD);
    await page.locator('input[name="confirmPassword"]').fill(ADMIN_PASSWORD);
    await page.getByRole('button', { name: /Enregistrer le mot de passe/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
  }
}

test.describe('Page de connexion', () => {
  test('affiche le formulaire de connexion', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Connexion' })).toBeVisible();
    await expect(page.locator('#field-email')).toBeVisible();
    await expect(page.locator('#field-password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible();
  });

  test('redirige vers le dashboard après connexion réussie', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.getByRole('heading', { name: 'Tableau de bord' })).toBeVisible();
  });
});
