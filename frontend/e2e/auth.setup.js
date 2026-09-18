import { test as setup, expect } from '@playwright/test';
import { loginWithCredentials } from './helpers';

const ADMIN_EMAIL = 'admin@ecole.local';
const ADMIN_PASSWORD = 'Admin123!';
/** Mot de passe distinct si le compte exige un changement (même mdp souvent refusé). */
const ADMIN_PASSWORD_ROTATED = 'Admin123!E2E';
const authFile = 'e2e/.auth/admin.json';

const POST_LOGIN_URL =
  /\/(dashboard|change-password|parent|enseignant|eleve|classes|platform)/;

setup('authenticate as admin', async ({ page }) => {
  await loginWithCredentials(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.waitForURL(POST_LOGIN_URL, { timeout: 30000 });
  if (page.url().includes('change-password')) {
    await page.locator('input[name="currentPassword"]').fill(ADMIN_PASSWORD);
    await page.locator('input[name="newPassword"]').fill(ADMIN_PASSWORD_ROTATED);
    await page.locator('input[name="confirmPassword"]').fill(ADMIN_PASSWORD_ROTATED);
    await page.getByRole('button', { name: /Enregistrer le mot de passe/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30000 });
  } else if (!page.url().includes('/dashboard')) {
    // Compte déjà rotaté : retenter avec le mot de passe E2E
    await loginWithCredentials(page, ADMIN_EMAIL, ADMIN_PASSWORD_ROTATED);
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
  }
  await expect(page.locator('main').getByRole('heading', { level: 1 })).toBeVisible({
    timeout: 20000,
  });
  await page.context().storageState({ path: authFile });
});
