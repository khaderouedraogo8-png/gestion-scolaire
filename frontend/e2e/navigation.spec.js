import { test, expect } from '@playwright/test';

const authFile = 'e2e/.auth/admin.json';

test.describe('Navigation Cycle → Classe', () => {
  test.use({ storageState: authFile });

  test('dashboard → clic ligne classe → onglet Absences', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Tableau de bord' })).toBeVisible({ timeout: 15000 });

    const classLink = page.locator('a[href*="onglet=absences"]').first();
    const linkCount = await classLink.count();

    if (linkCount === 0) {
      await page.goto('/classes/premier');
      await expect(page.getByRole('heading', { name: 'Premier cycle' })).toBeVisible();
      const firstClass = page.locator('a[href*="/classes/premier/"]').first();
      await firstClass.click();
      await expect(page.getByRole('button', { name: 'Absences' })).toBeVisible();
      await page.getByRole('button', { name: 'Absences' }).click();
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      return;
    }

    await classLink.click();
    await expect(page).toHaveURL(/onglet=absences/);
    await expect(page.getByRole('button', { name: 'Absences' })).toBeVisible();
  });

  test('sidebar Élèves mène à /classes', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: 'Élèves' }).click();
    await expect(page).toHaveURL(/\/classes$/);
    await expect(page.getByRole('heading', { name: 'Classes' })).toBeVisible();
  });
});
