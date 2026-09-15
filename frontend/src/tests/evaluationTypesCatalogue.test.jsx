import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import EvaluationList from '../pages/notes/EvaluationList';
import { ToastProvider } from '../components/Toast';

const mockListEvaluations = vi.fn();
const mockCreateEvaluation = vi.fn();
const mockListMatieres = vi.fn();
const mockListClasses = vi.fn();
const mockListAnnees = vi.fn();
const mockListTrimestres = vi.fn();
const mockListEvaluationTypes = vi.fn();

vi.mock('../services/api/notes', () => ({
  notesApi: {
    listEvaluations: (...a) => mockListEvaluations(...a),
    createEvaluation: (...a) => mockCreateEvaluation(...a),
    listMatieres: (...a) => mockListMatieres(...a),
  },
}));

vi.mock('../services/api/config', () => ({
  configApi: {
    listClasses: (...a) => mockListClasses(...a),
    listAnnees: (...a) => mockListAnnees(...a),
    listTrimestres: (...a) => mockListTrimestres(...a),
  },
}));

vi.mock('../services/api/grading', () => ({
  gradingApi: {
    listEvaluationTypes: (...a) => mockListEvaluationTypes(...a),
  },
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    isAdmin: true,
    isEnseignant: false,
    hasAnyRole: () => true,
  }),
  default: () => ({
    isAdmin: true,
    isEnseignant: false,
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <EvaluationList />
      </ToastProvider>
    </MemoryRouter>
  );
}

describe('EvaluationList types catalogue (PR14)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListEvaluations.mockResolvedValue({ items: [] });
    mockListMatieres.mockResolvedValue({ items: [{ id: 'm1', libelle: 'Math' }] });
    mockListClasses.mockResolvedValue({ items: [{ id: 'c1', libelle: '6ème A' }] });
    mockListAnnees.mockResolvedValue([{ id: 'y1', libelle: '2025-2026', est_active: true }]);
    mockListTrimestres.mockResolvedValue({
      items: [{ id: 'p1', numero: 1, label: 'Trimestre 1' }],
    });
    mockListEvaluationTypes.mockResolvedValue({
      items: [
        { id: 't1', code: 'devoir', label: 'Devoir' },
        { id: 't2', code: 'composition', label: 'Composition' },
        { id: 't3', code: 'tp', label: 'Travaux pratiques' },
      ],
    });
    mockCreateEvaluation.mockResolvedValue({ id: 'e1' });
  });

  it('charge le catalogue evaluation-types et propose composition', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(mockListEvaluationTypes).toHaveBeenCalled());
    await user.click(screen.getByRole('button', { name: /Nouvelle évaluation/i }));
    const typeSelect = screen.getByLabelText(/Type d'évaluation/i);
    expect(typeSelect).toBeInTheDocument();
    expect(withinOptions(typeSelect)).toContain('composition');
    expect(withinOptions(typeSelect)).toContain('tp');
  });

  it('envoie le code catalogue à la création (pas de poids hardcodé)', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(mockListEvaluationTypes).toHaveBeenCalled());
    await user.click(screen.getByRole('button', { name: /Nouvelle évaluation/i }));
    await user.type(screen.getByLabelText(/Libellé/i), 'Composition T1');
    await user.selectOptions(screen.getByLabelText(/^Classe/i), 'c1');
    await user.selectOptions(screen.getByLabelText(/^Matière/i), 'm1');
    await user.selectOptions(screen.getByLabelText(/Trimestre/i), 'p1');
    await user.selectOptions(screen.getByLabelText(/Type d'évaluation/i), 'composition');
    await user.click(screen.getByRole('button', { name: /^Créer$/i }));
    await waitFor(() => expect(mockCreateEvaluation).toHaveBeenCalled());
    const payload = mockCreateEvaluation.mock.calls[0][0];
    expect(payload.type_evaluation).toBe('composition');
    expect(payload).not.toHaveProperty('weight');
    expect(payload).not.toHaveProperty('poids');
  });
});

function withinOptions(select) {
  return Array.from(select.querySelectorAll('option')).map((o) => o.value);
}
