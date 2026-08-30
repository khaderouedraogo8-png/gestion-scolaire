import { test, expect } from '@playwright/test';
import { classTab, expectPageTitle, loginWithCredentials } from './helpers';

const PARENT_EMAIL = 'parent@demo.local';
const PARENT_PASSWORD = 'Parent123!';

async function loginAsParent(page) {
  await loginWithCredentials(page, PARENT_EMAIL, PARENT_PASSWORD);
  await page.waitForURL(/\/parent/, { timeout: 15000 });
}

test.describe('Portail parent — programme pédagogique', () => {
  test('carte et menu mènent au programme pédagogique', async ({ page }) => {
    await loginAsParent(page);
    await expect(page.getByRole('heading', { level: 1, name: /^Bonjour,/ })).toBeVisible();
    await page.getByRole('link', { name: /Programme pédagogique/i }).first().click();
    await expect(page).toHaveURL(/\/parent\/pedagogie/);
    await expectPageTitle(page, 'Programme pédagogique');
  });

  test('onglets devoirs, compositions et cahier en lecture seule', async ({ page }) => {
    await loginAsParent(page);
    await page.goto('/parent/pedagogie');
    await expectPageTitle(page, 'Programme pédagogique');

    await classTab(page, 'Devoirs').click();
    await expect(page.getByText('Planning récurrent des devoirs')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Ajouter' })).toHaveCount(0);

    await classTab(page, 'Compositions').click();
    await expect(page.getByRole('button', { name: 'Calendrier PDF' })).toBeVisible();

    await classTab(page, 'Cahier de texte').click();
    await expect(page.getByText('Contenu des séances enregistrées')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Enregistrer la séance' })).toHaveCount(0);
  });
});
