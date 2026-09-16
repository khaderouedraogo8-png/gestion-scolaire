import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ResultatsAcademiques from '../pages/notes/ResultatsAcademiques';
import { ToastProvider } from '../components/Toast';

const mockListResultats = vi.fn();
const mockRecalculer = vi.fn();
const mockListEvaluations = vi.fn();
const mockListClasses = vi.fn();
const mockListAnnees = vi.fn();
const mockListTrimestres = vi.fn();
const mockListEleves = vi.fn();

vi.mock('../services/api/notes', () => ({
  notesApi: {
    listResultats: (...a) => mockListResultats(...a),
    recalculerResultats: (...a) => mockRecalculer(...a),
    listEvaluations: (...a) => mockListEvaluations(...a),
    getNotesGrid: vi.fn().mockResolvedValue({ notes: [] }),
  },
}));

vi.mock('../services/api/config', () => ({
  configApi: {
    listClasses: (...a) => mockListClasses(...a),
    listAnnees: (...a) => mockListAnnees(...a),
    listTrimestres: (...a) => mockListTrimestres(...a),
  },
}));

vi.mock('../services/api/eleves', () => ({
  elevesApi: {
    list: (...a) => mockListEleves(...a),
  },
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ isAdmin: true, isEnseignant: false }),
  default: () => ({ isAdmin: true, isEnseignant: false }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <ResultatsAcademiques />
      </ToastProvider>
    </MemoryRouter>
  );
}

describe('ResultatsAcademiques parcours (PR14)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListClasses.mockResolvedValue({ items: [{ id: 'c1', libelle: '6ème A' }] });
    mockListAnnees.mockResolvedValue([{ id: 'y1', libelle: '2025-2026', est_active: true }]);
    mockListTrimestres.mockResolvedValue({
      items: [{ id: 'p1', numero: 1, label: 'Trimestre 1' }],
    });
    mockListEleves.mockResolvedValue({
      items: [{ id: 'el1', prenom: 'Awa', nom: 'Traoré', matricule: 'M1' }],
    });
    mockListEvaluations.mockResolvedValue({ items: [] });
    mockListResultats.mockResolvedValue({
      items: [
        {
          id: 'r1',
          id_matiere: 'm1',
          matiere_libelle: 'Mathématiques',
          moyenne: null,
          coefficient: 2,
          ruleset_code: 'STD',
          ruleset_version: 1,
          source: 'rules_engine',
          incomplete: true,
          is_stale: false,
        },
      ],
      has_stale: false,
      total: 1,
    });
    mockRecalculer.mockResolvedValue({
      items: [
        {
          id_eleve: 'el1',
          results: [
            {
              id: 'r1',
              id_matiere: 'm1',
              matiere_libelle: 'Mathématiques',
              moyenne: 13.6,
              coefficient: 2,
              ruleset_code: 'STD',
              ruleset_version: 1,
              source: 'rules_engine',
              incomplete: false,
              is_stale: false,
            },
          ],
        },
      ],
      total: 1,
    });
  });

  it('charge les résultats via API sans calculer côté client', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(mockListClasses).toHaveBeenCalled());
    await user.selectOptions(screen.getByLabelText(/^Classe/i), 'c1');
    await waitFor(() => expect(mockListEleves).toHaveBeenCalled());
    await user.selectOptions(screen.getByLabelText(/^Élève/i), 'el1');
    await waitFor(() => expect(mockListResultats).toHaveBeenCalled());
    const args = mockListResultats.mock.calls.at(-1)[0];
    expect(args).toMatchObject({
      id_classe: 'c1',
      id_eleve: 'el1',
      id_period: 'p1',
    });
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.queryByText('0.00/20')).not.toBeInTheDocument();
  });

  it('recalcule via endpoint backend', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(mockListClasses).toHaveBeenCalled());
    await user.selectOptions(screen.getByLabelText(/^Classe/i), 'c1');
    await waitFor(() => expect(mockListEleves).toHaveBeenCalled());
    await user.selectOptions(screen.getByLabelText(/^Élève/i), 'el1');
    await waitFor(() => expect(mockListResultats).toHaveBeenCalled());
    await user.click(screen.getByRole('button', { name: /Recalculer/i }));
    await waitFor(() => expect(mockRecalculer).toHaveBeenCalled());
    expect(mockRecalculer.mock.calls[0][0]).toMatchObject({
      id_classe: 'c1',
      id_period: 'p1',
      id_eleve: 'el1',
    });
    await waitFor(() => expect(screen.getByText('13.60/20')).toBeInTheDocument());
  });
});
