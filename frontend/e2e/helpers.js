import { expect } from '@playwright/test';

/** Lien de navigation dans la barre latérale */
export function sidebarLink(page, name) {
  return page.locator('aside nav').getByRole('link', { name, exact: true });
}

/** Onglet d'une fiche classe (TabBar) */
export function classTab(page, name) {
  return page.getByRole('tab', { name });
}

/** Attendre un titre de page principal (PageHeader / DetailHeader) */
export async function expectPageTitle(page, title, timeout = 15000) {
  await expect(page.locator('main').getByRole('heading', { level: 1, name: title })).toBeVisible({
    timeout,
  });
}

/** Connexion via la page /login */
export async function loginWithCredentials(page, email, password) {
  await page.goto('/login');
  const emailField = page.locator('#field-email');
  const passwordField = page.locator('#field-password');
  await expect(emailField).toBeVisible({ timeout: 15000 });
  await emailField.fill(email);
  await passwordField.fill(password);
  await page.getByRole('button', { name: 'Se connecter' }).click();
}
