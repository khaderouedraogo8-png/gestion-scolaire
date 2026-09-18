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

/** Connexion via la page /login — attend la réponse API avant navigation SPA. */
export async function loginWithCredentials(page, email, password) {
  await page.goto('/login');
  const emailField = page.locator('#field-email');
  const passwordField = page.locator('#field-password');
  await expect(emailField).toBeVisible({ timeout: 20000 });
  await emailField.fill(email);
  await passwordField.fill(password);
  const loginResponse = page.waitForResponse(
    (r) => r.url().includes('/api/login') && r.request().method() === 'POST',
    { timeout: 20000 },
  );
  await page.getByRole('button', { name: 'Se connecter' }).click();
  const res = await loginResponse;
  if (!res.ok()) {
    const body = await res.text().catch(() => '');
    throw new Error(`Login API ${res.status()}: ${body.slice(0, 200)}`);
  }
}
