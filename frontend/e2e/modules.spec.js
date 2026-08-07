import { test, expect } from '@playwright/test';

const authFile = 'e2e/.auth/admin.json';

test.describe.configure({ mode: 'serial' });

test.describe('Modules principaux', () => {
  test.use({ storageState: authFile });

  test.afterEach(async ({ context }) => {
    await context.storageState({ path: authFile });
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Tableau de bord' })).toBeVisible({
      timeout: 15000,
    });
  });

  test('charge la liste des élèves', async ({ page }) => {
    await page.getByRole('link', { name: /Élèves/ }).click();
    await expect(page.getByRole('heading', { name: 'Élèves' })).toBeVisible();
    await expect(page.getByText(/\d+–\d+ sur \d+|1 sur 1/)).toBeVisible({ timeout: 10000 });
  });

  test('charge les évaluations', async ({ page }) => {
    await page.getByRole('link', { name: /Notes & Bulletins/ }).click();
    await expect(page.getByRole('heading', { name: 'Évaluations' })).toBeVisible();
    await expect(page.getByRole('link', { name: /Saisir notes/ }).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test('charge les frais scolaires', async ({ page }) => {
    await page.getByRole('link', { name: /Finance/ }).click();
    await expect(page.getByRole('heading', { name: 'Frais scolaires' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Ajouter échéance/ }).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test('charge les absences', async ({ page }) => {
    await page.getByRole('link', { name: /Absences & Discipline/ }).click();
    await expect(page.getByRole('heading', { name: 'Absences' })).toBeVisible();
    await expect(page.getByRole('button', { name: '+ Signaler une absence' })).toBeVisible();
  });
});
