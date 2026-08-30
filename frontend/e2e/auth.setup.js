import { test as setup, expect } from '@playwright/test';
import { loginWithCredentials } from './helpers';

const ADMIN_EMAIL = 'admin@ecole.local';
const ADMIN_PASSWORD = 'Admin123!';
const authFile = 'e2e/.auth/admin.json';

setup('authenticate as admin', async ({ page }) => {
  await loginWithCredentials(page, ADMIN_EMAIL, ADMIN_PASSWORD);
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
