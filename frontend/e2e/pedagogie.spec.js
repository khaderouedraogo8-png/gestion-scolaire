import { test, expect } from '@playwright/test';

const authFile = 'e2e/.auth/admin.json';

test.describe('Programme pédagogique', () => {
  test.use({ storageState: authFile });

  test.afterEach(async ({ context }) => {
    await context.storageState({ path: authFile });
  });

  async function openFirstClass(page) {
    await page.goto('/classes/premier');
    await expect(page.getByRole('heading', { name: 'Premier cycle' })).toBeVisible({ timeout: 15000 });
    const firstClass = page.locator('a[href*="/classes/premier/"]').first();
    await expect(firstClass).toBeVisible({ timeout: 10000 });
    await firstClass.click();
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  }

  test('onglets Devoirs et Compositions visibles', async ({ page }) => {
    await openFirstClass(page);
    await page.getByRole('button', { name: 'Devoirs' }).click();
    await expect(page.getByText('Planning récurrent des devoirs')).toBeVisible();
    await page.getByRole('button', { name: 'Compositions' }).click();
    await expect(page.getByRole('button', { name: 'Imprimer le calendrier' })).toBeVisible();
  });

  test('onglet Cahier de texte', async ({ page }) => {
    await openFirstClass(page);
    await page.getByRole('button', { name: 'Cahier de texte' }).click();
    await expect(page.getByText('Contenu des séances')).toBeVisible();
  });

  test('fiche enseignant depuis la liste', async ({ page }) => {
    await page.goto('/emploi/enseignants');
    await expect(page.getByRole('heading', { name: 'Enseignants' })).toBeVisible({ timeout: 15000 });
    const row = page.locator('tbody tr').first();
    if ((await row.count()) === 0) return;
    await row.click();
    await expect(page.getByRole('button', { name: 'Imprimer la fiche' })).toBeVisible();
  });

  test('calendrier scolaire en configuration', async ({ page }) => {
    await page.goto('/config/calendrier');
    await expect(page.getByRole('heading', { name: 'Calendrier scolaire' })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('button', { name: '+ Ajouter' })).toBeVisible();
  });
});
