import { test, expect } from '@playwright/test';
import { classTab, expectPageTitle, sidebarLink } from './helpers';

const authFile = 'e2e/.auth/admin.json';

test.describe('Navigation Cycle → Classe', () => {
  test.use({ storageState: authFile });

  test.afterEach(async ({ context }) => {
    await context.storageState({ path: authFile });
  });

  test('dashboard → clic ligne classe → onglet Absences', async ({ page }) => {
    await page.goto('/dashboard');
    await expectPageTitle(page, 'Tableau de bord');

    const classLink = page.locator('a[href*="onglet=absences"]').first();
    const linkCount = await classLink.count();

    if (linkCount === 0) {
      await page.goto('/classes/premier');
      await expectPageTitle(page, 'Premier cycle');
      const firstClass = page.locator('a[href*="/classes/premier/"]').first();
      await firstClass.click();
      await expect(page).toHaveURL(/\/classes\/premier\//);
      await classTab(page, 'Absences').click();
      await expect(classTab(page, 'Absences')).toHaveAttribute('aria-selected', 'true');
      return;
    }

    await classLink.click();
    await expect(page).toHaveURL(/onglet=absences/);
    await expect(classTab(page, 'Absences')).toBeVisible();
  });

  test('sidebar Élèves mène à /classes', async ({ page }) => {
    await page.goto('/dashboard');
    await expectPageTitle(page, 'Tableau de bord');
    await sidebarLink(page, 'Élèves').click();
    await expect(page).toHaveURL(/\/classes$/);
    await expectPageTitle(page, 'Classes');
  });
});
