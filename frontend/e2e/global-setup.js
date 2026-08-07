/** Préparation E2E — vérifie que l'API répond avant les tests. */
export default async function globalSetup() {
  const res = await fetch('http://localhost:5000/api/health');
  if (!res.ok) {
    throw new Error('Backend indisponible pour les tests E2E');
  }
}
