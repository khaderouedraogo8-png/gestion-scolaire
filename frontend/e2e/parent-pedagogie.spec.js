import { test, expect } from '@playwright/test';

const PARENT_EMAIL = 'parent@demo.local';
const PARENT_PASSWORD = 'Parent123!';

async function loginAsParent(page) {
  await page.goto('/login');
  await page.locator('#field-email').fill(PARENT_EMAIL);
  await page.locator('#field-password').fill(PARENT_PASSWORD);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await page.waitForURL(/\/parent/, { timeout: 15000 });
}

test.describe('Portail parent — programme pédagogique', () => {
  test('carte et menu mènent au programme pédagogique', async ({ page }) => {
    await loginAsParent(page);
    await expect(page.getByRole('heading', { name: 'Espace parent' })).toBeVisible();
    await page.getByRole('link', { name: /Programme pédagogique/i }).first().click();
    await expect(page).toHaveURL(/\/parent\/pedagogie/);
    await expect(page.getByRole('heading', { name: 'Programme pédagogique' })).toBeVisible();
  });

  test('onglets devoirs, compositions et cahier en lecture seule', async ({ page }) => {
    await loginAsParent(page);
    await page.goto('/parent/pedagogie');
    await expect(page.getByRole('heading', { name: 'Programme pédagogique' })).toBeVisible({
      timeout: 15000,
    });

    await page.getByRole('button', { name: 'Devoirs' }).click();
    await expect(page.getByText('Planning récurrent des devoirs')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Ajouter' })).toHaveCount(0);

    await page.getByRole('button', { name: 'Compositions' }).click();
    await expect(page.getByRole('button', { name: 'Calendrier PDF' })).toBeVisible();

    await page.getByRole('button', { name: 'Cahier de texte' }).click();
    await expect(page.getByText('Contenu des séances enregistrées')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Enregistrer la séance' })).toHaveCount(0);
  });
});
