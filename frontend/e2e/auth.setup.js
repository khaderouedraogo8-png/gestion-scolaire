import { test as setup, expect } from '@playwright/test';

const ADMIN_EMAIL = 'admin@ecole.local';
const ADMIN_PASSWORD = 'Admin123!';
const authFile = 'e2e/.auth/admin.json';

setup('authenticate as admin', async ({ page }) => {
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
  await page.context().storageState({ path: authFile });
});
