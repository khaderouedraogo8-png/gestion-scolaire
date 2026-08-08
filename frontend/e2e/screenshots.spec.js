/**
 * Captures d'écran des pages principales pour revue UI.
 * Usage : npm run screenshots
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const authFile = 'e2e/.auth/admin.json';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(__dirname, '../../docs/ui-screenshots');

const PAGES_AUTH = [
  { name: '01-dashboard', url: '/dashboard', heading: 'Tableau de bord' },
  { name: '02-classes', url: '/classes', heading: 'Classes' },
  { name: '03-notes-evaluations', url: '/notes/evaluations', heading: 'Évaluations' },
  { name: '04-notes-bulletins', url: '/notes/bulletins', heading: 'Bulletins' },
  { name: '05-finance-frais', url: '/finance/frais', heading: 'Frais scolaires' },
  { name: '06-finance-encaissement', url: '/finance/encaissement', heading: 'Encaissement' },
  { name: '07-finance-arrieres', url: '/finance/arrieres', heading: 'Arriérés' },
  { name: '08-absences', url: '/absences', heading: 'Absences' },
  { name: '09-documents', url: '/documents', heading: 'Documents administratifs' },
  { name: '10-notifications', url: '/notifications', heading: 'Notifications' },
  { name: '11-config-etablissement', url: '/config/etablissement', heading: 'Établissement' },
  { name: '12-config-classes', url: '/config/classes', heading: 'Classes' },
  { name: '13-emploi-enseignants', url: '/emploi/enseignants', heading: 'Enseignants' },
];

test.describe('Captures UI — login (sans session)', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeAll(() => {
    fs.mkdirSync(outDir, { recursive: true });
  });

  test('00-login', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: path.join(outDir, '00-login.png'), fullPage: true });
  });
});

test.describe('Captures UI — desktop', () => {
  test.describe.configure({ mode: 'serial' });

  test.use({ storageState: authFile, viewport: { width: 1440, height: 900 } });

  test.afterEach(async ({ context }) => {
    await context.storageState({ path: authFile });
  });

  for (const { name, url, heading } of PAGES_AUTH) {
    test(name, async ({ page }) => {
      await page.goto(url);
      await expect(page.getByRole('heading', { name: heading })).toBeVisible({ timeout: 15000 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `${name}.png`), fullPage: true });
    });
  }
});

test.describe('Captures UI — mobile', () => {
  test.describe.configure({ mode: 'serial' });

  test.use({ storageState: authFile, viewport: { width: 390, height: 844 } });

  test.afterEach(async ({ context }) => {
    await context.storageState({ path: authFile });
  });

  test('14-dashboard-mobile', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Tableau de bord' })).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: path.join(outDir, '14-dashboard-mobile.png'), fullPage: true });
  });

  test('15-eleves-mobile', async ({ page }) => {
    await page.goto('/classes');
    await expect(page.getByRole('heading', { name: 'Classes' })).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: path.join(outDir, '15-eleves-mobile.png'), fullPage: true });
  });
});
