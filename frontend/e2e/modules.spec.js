import { test, expect } from '@playwright/test';
import { expectPageTitle, sidebarLink } from './helpers';

const authFile = 'e2e/.auth/admin.json';

test.describe.configure({ mode: 'serial' });

test.describe('Modules principaux', () => {
  test.use({ storageState: authFile });

  test.afterEach(async ({ context }) => {
    await context.storageState({ path: authFile });
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await expectPageTitle(page, 'Tableau de bord');
  });

  test('charge la liste des élèves', async ({ page }) => {
    await sidebarLink(page, 'Élèves').click();
    await expectPageTitle(page, 'Classes');
  });

  test('charge les évaluations', async ({ page }) => {
    await sidebarLink(page, 'Notes & Bulletins').click();
    await expectPageTitle(page, 'Évaluations');
    await expect(page.getByRole('link', { name: /Saisir notes/ }).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test('charge les frais scolaires', async ({ page }) => {
    await sidebarLink(page, 'Finance').click();
    await expectPageTitle(page, 'Frais scolaires');
    await expect(page.getByRole('button', { name: /Ajouter échéance/ }).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test('charge les absences', async ({ page }) => {
    await sidebarLink(page, 'Absences & Discipline').click();
    await expectPageTitle(page, 'Absences');
    await expect(page.getByRole('button', { name: '+ Signaler une absence' })).toBeVisible();
  });
});
