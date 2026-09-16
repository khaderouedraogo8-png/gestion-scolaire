import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import GradingRulesets from '../pages/config/GradingRulesets';
import GradingRulesetDetail, { displayGradeValue } from '../pages/config/GradingRulesetDetail';
import ProtectedRoute from '../components/ProtectedRoute';
import { ToastProvider } from '../components/Toast';
import {
  ENGINE_MISSING_POLICY_INFO,
  formatScaleMax,
  formatWeight,
  roundingModeLabel,
  rulesetStatusLabel,
  sumWeights,
  weightsAreValid,
} from '../utils/gradingLabels';
import { apiErrorMessage } from '../utils/academicLabels';

const mockListRulesets = vi.fn();
const mockCreateRuleset = vi.fn();
const mockGetRuleset = vi.fn();
const mockActivateRuleset = vi.fn();
const mockListEvaluationTypes = vi.fn();

let authRole = 'administrateur';
const mockHasAnyRole = vi.fn((roles) => roles.includes(authRole));

vi.mock('../services/api/grading', () => ({
  gradingApi: {
    listRulesets: (...args) => mockListRulesets(...args),
    createRuleset: (...args) => mockCreateRuleset(...args),
    getRuleset: (...args) => mockGetRuleset(...args),
    updateRuleset: vi.fn(),
    activateRuleset: (...args) => mockActivateRuleset(...args),
    archiveRuleset: vi.fn(),
    listEvaluationTypes: (...args) => mockListEvaluationTypes(...args),
    addComponent: vi.fn(),
    updateComponent: vi.fn(),
    deleteComponent: vi.fn(),
    resolve: vi.fn(),
  },
}));

vi.mock('../services/api/config', () => ({
  configApi: {
    listAnnees: vi.fn().mockResolvedValue([{ id: 'year-1', libelle: '2025-2026', est_active: true }]),
    listPrograms: vi
      .fn()
      .mockResolvedValue([{ id: 'prog-1', code: 'GEN', name: 'Général', is_active: true }]),
    listNiveaux: vi.fn().mockResolvedValue([{ id: 'niv-1', libelle: '6ème' }]),
  },
}));

vi.mock('../services/api/notes', () => ({
  notesApi: {
    listMatieres: vi.fn().mockResolvedValue([{ id: 'mat-1', libelle: 'Mathématiques', code: 'MATH' }]),
  },
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    hasAnyRole: (...args) => mockHasAnyRole(...args),
    hasRole: (r) => r === authRole,
    user: { role: authRole },
  }),
  default: () => ({
    hasAnyRole: (...args) => mockHasAnyRole(...args),
    hasRole: (r) => r === authRole,
    user: { role: authRole },
  }),
}));

vi.mock('../store/authStore', () => ({
  useAuthStore: (selector) => {
    const state = {
      isAuthenticated: true,
      user: { role: authRole, doit_changer_mdp: false },
      hasAnyRole: (roles) => roles.includes(authRole),
      hasRole: (r) => r === authRole,
    };
    return typeof selector === 'function' ? selector(state) : state;
  },
  getAccessToken: () => 'token',
  setAccessToken: vi.fn(),
}));

const SAMPLE_RULESET = {
  id: 'rs-1',
  code: 'LDC-GEN',
  name: 'Pondération générale',
  description: 'Test',
  status: 'draft',
  version: 1,
  academic_year_id: 'year-1',
  program_id: 'prog-1',
  level_id: null,
  subject_id: null,
  scale_max: '20.00',
  rounding_mode: 'half_up',
  rounding_precision: 2,
  created_at: '2026-01-01T10:00:00Z',
  updated_at: '2026-01-02T10:00:00Z',
  components: [
    {
      id: 'c1',
      code: 'DEV',
      label: 'Devoir',
      evaluation_type_id: 'et-devoir',
      evaluation_type: { id: 'et-devoir', code: 'devoir', label: 'Devoir' },
      evaluation_context: 'normal',
      weight: '60.00',
      sequence: 1,
      is_required: true,
    },
    {
      id: 'c2',
      code: 'COMP',
      label: 'Composition',
      evaluation_type_id: 'et-comp',
      evaluation_type: { id: 'et-comp', code: 'composition', label: 'Composition' },
      evaluation_context: 'normal',
      weight: '40.00',
      sequence: 2,
      is_required: true,
    },
  ],
  components_count: 2,
};

function wrap(initial = '/config/regles-notation') {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/config/regles-notation" element={<GradingRulesets />} />
          <Route path="/config/regles-notation/:id" element={<GradingRulesetDetail />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

function wrapProtected() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={['/config/regles-notation']}>
        <Routes>
          <Route
            path="/config/regles-notation"
            element={
              <ProtectedRoute roles={['administrateur', 'directeur', 'super_admin']}>
                <GradingRulesets />
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

async function fillCreateBasics(user) {
  await user.type(document.getElementById('field-code'), 'LDC-GEN');
  await user.type(document.getElementById('field-name'), 'Pondération générale');
  await user.selectOptions(document.getElementById('field-academic_year_id'), 'year-1');
}

async function fillComponent(user, index, { code, label, typeId, weight }) {
  await user.clear(document.getElementById(`field-comp_label_${index}`));
  await user.type(document.getElementById(`field-comp_label_${index}`), label);
  await user.selectOptions(document.getElementById(`field-comp_type_${index}`), typeId);
  await user.clear(document.getElementById(`field-comp_weight_${index}`));
  await user.type(document.getElementById(`field-comp_weight_${index}`), String(weight));
  await user.clear(document.getElementById(`field-comp_code_${index}`));
  await user.type(document.getElementById(`field-comp_code_${index}`), code);
}

describe('gradingLabels helpers', () => {
  it('valide 60/40 et refuse 90', () => {
    expect(weightsAreValid([{ weight: 60 }, { weight: 40 }])).toBe(true);
    expect(sumWeights([{ weight: 60 }, { weight: 30 }])).toBe(90);
    expect(weightsAreValid([{ weight: 60 }, { weight: 30 }])).toBe(false);
  });

  it('valide 30/20/50', () => {
    expect(weightsAreValid([{ weight: 30 }, { weight: 20 }, { weight: 50 }])).toBe(true);
  });

  it('affiche scale_max = 100 clairement', () => {
    expect(formatScaleMax(100)).toBe('Note maximale : 100');
    expect(formatScaleMax('20.00')).toContain('20');
  });

  it('affiche les paramètres d’arrondi', () => {
    expect(roundingModeLabel('half_up')).toMatch(/HALF_UP/i);
    expect(rulesetStatusLabel('draft')).toBe('Brouillon');
  });

  it('missing n’est jamais affiché comme 0', () => {
    expect(displayGradeValue(null)).toBe('—');
    expect(displayGradeValue(undefined)).toBe('—');
    expect(displayGradeValue('')).toBe('—');
    expect(displayGradeValue(0)).toBe('0');
    expect(formatWeight(null)).toBe('—');
  });

  it('décrit les politiques missing du moteur (BLOCK/EXCLUDE sémantiques UI)', () => {
    expect(ENGINE_MISSING_POLICY_INFO.length).toBeGreaterThanOrEqual(2);
    const blob = ENGINE_MISSING_POLICY_INFO.map((p) => `${p.name} ${p.effect} ${p.description}`).join(
      ' '
    );
    expect(blob).toMatch(/manquante/i);
    expect(blob).toMatch(/incomplet|renormal/i);
  });
});

describe('apiErrorMessage grading', () => {
  it('gère 403', () => {
    expect(
      apiErrorMessage({ response: { status: 403, data: { message: 'Forbidden tenant' } } }, 'fallback')
    ).toBe('Forbidden tenant');
  });

  it('gère 409 concurrence/version', () => {
    expect(
      apiErrorMessage(
        {
          response: {
            status: 409,
            data: { message: 'Impossible d’activer : une autre version est déjà active.' },
          },
        },
        'fallback'
      )
    ).toMatch(/déjà active/i);
  });
});

describe('GradingRulesets list', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authRole = 'administrateur';
    mockHasAnyRole.mockImplementation((roles) => roles.includes(authRole));
    mockListEvaluationTypes.mockResolvedValue({
      items: [
        { id: 'et-devoir', code: 'devoir', label: 'Devoir' },
        { id: 'et-comp', code: 'composition', label: 'Composition' },
        { id: 'et-tp', code: 'tp', label: 'TP' },
      ],
    });
    mockListRulesets.mockResolvedValue({
      items: [SAMPLE_RULESET],
      page: 1,
      per_page: 25,
      total: 1,
      pages: 1,
    });
  });

  it('charge la liste des Rulesets', async () => {
    wrap();
    expect(await screen.findByRole('heading', { name: /règles de notation/i })).toBeInTheDocument();
    await waitFor(() => expect(mockListRulesets).toHaveBeenCalled());
    expect(await screen.findByText('Pondération générale')).toBeInTheDocument();
    expect(screen.getAllByText('Brouillon').length).toBeGreaterThan(0);
  });

  it('refuse l’accès configuration pour un rôle non autorisé', async () => {
    authRole = 'enseignant';
    wrapProtected();
    expect(await screen.findByText(/accès non autorisé/i)).toBeInTheDocument();
    expect(mockListRulesets).not.toHaveBeenCalled();
  });

  it('crée un Ruleset 60/40 correctement envoyé à l’API', async () => {
    const user = userEvent.setup();
    mockCreateRuleset.mockResolvedValue({ ...SAMPLE_RULESET, id: 'rs-new' });
    wrap();
    await screen.findByText('Pondération générale');
    await user.click(screen.getByRole('button', { name: /nouveau ruleset/i }));
    expect(await screen.findByRole('heading', { name: /nouveau ruleset/i })).toBeInTheDocument();

    await fillCreateBasics(user);
    await fillComponent(user, 0, {
      code: 'DEV',
      label: 'Devoir',
      typeId: 'et-devoir',
      weight: 60,
    });
    await user.click(screen.getByRole('button', { name: /^\+ ajouter$/i }));
    await fillComponent(user, 1, {
      code: 'COMP',
      label: 'Composition',
      typeId: 'et-comp',
      weight: 40,
    });

    await user.click(screen.getByRole('button', { name: /créer le brouillon/i }));
    await waitFor(() => expect(mockCreateRuleset).toHaveBeenCalled());
    const payload = mockCreateRuleset.mock.calls[0][0];
    expect(payload.components.map((c) => Number(c.weight))).toEqual([60, 40]);
    expect(payload).not.toHaveProperty('missing_grade_policy');
    expect(payload.rounding_mode).toBe('half_up');
  });

  it('bloque une création avec poids incorrect (90 %)', async () => {
    const user = userEvent.setup();
    wrap();
    await screen.findByText('Pondération générale');
    await user.click(screen.getByRole('button', { name: /nouveau ruleset/i }));
    await screen.findByRole('heading', { name: /nouveau ruleset/i });

    await fillCreateBasics(user);
    await fillComponent(user, 0, {
      code: 'DEV',
      label: 'Devoir',
      typeId: 'et-devoir',
      weight: 90,
    });

    await user.click(screen.getByRole('button', { name: /créer le brouillon/i }));
    expect(mockCreateRuleset).not.toHaveBeenCalled();
    expect(await screen.findByText(/doit être 100/i)).toBeInTheDocument();
  });

  it('envoie 30/20/50 correctement', async () => {
    const user = userEvent.setup();
    mockCreateRuleset.mockResolvedValue({ ...SAMPLE_RULESET, id: 'rs-302050' });
    wrap();
    await screen.findByText('Pondération générale');
    await user.click(screen.getByRole('button', { name: /nouveau ruleset/i }));
    await screen.findByRole('heading', { name: /nouveau ruleset/i });

    await fillCreateBasics(user);
    await fillComponent(user, 0, { code: 'DEV', label: 'Devoir', typeId: 'et-devoir', weight: 30 });
    await user.click(screen.getByRole('button', { name: /^\+ ajouter$/i }));
    await fillComponent(user, 1, { code: 'TP', label: 'TP', typeId: 'et-tp', weight: 20 });
    await user.click(screen.getByRole('button', { name: /^\+ ajouter$/i }));
    await fillComponent(user, 2, {
      code: 'COMP',
      label: 'Composition',
      typeId: 'et-comp',
      weight: 50,
    });

    await user.click(screen.getByRole('button', { name: /créer le brouillon/i }));
    await waitFor(() => expect(mockCreateRuleset).toHaveBeenCalled());
    expect(mockCreateRuleset.mock.calls[0][0].components.map((c) => Number(c.weight))).toEqual([
      30, 20, 50,
    ]);
  });
});

describe('GradingRulesetDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authRole = 'administrateur';
    mockHasAnyRole.mockImplementation((roles) => roles.includes(authRole));
    mockListEvaluationTypes.mockResolvedValue({
      items: [
        { id: 'et-devoir', code: 'devoir', label: 'Devoir' },
        { id: 'et-comp', code: 'composition', label: 'Composition' },
      ],
    });
    mockGetRuleset.mockResolvedValue(SAMPLE_RULESET);
    mockListRulesets.mockResolvedValue({
      items: [SAMPLE_RULESET, { ...SAMPLE_RULESET, id: 'rs-2', version: 2, status: 'active' }],
      page: 1,
      pages: 1,
      total: 2,
    });
  });

  it('affiche scale, rounding, composantes et historique', async () => {
    wrap('/config/regles-notation/rs-1');
    expect(await screen.findByRole('heading', { name: 'Pondération générale' })).toBeInTheDocument();
    expect(screen.getAllByText(/note maximale : 20/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/half_up/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Devoir').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/60\.00 %/).length).toBeGreaterThan(0);
    expect(screen.getByText(/historique des versions/i)).toBeInTheDocument();
    expect(screen.getAllByText(/notes manquantes/i).length).toBeGreaterThan(0);
  });

  it('gère une erreur 403 au chargement détail (isolation tenant UI)', async () => {
    mockGetRuleset.mockRejectedValue({
      response: { status: 403, data: { message: 'Accès refusé pour ce tenant.' } },
    });
    wrap('/config/regles-notation/rs-1');
    expect(await screen.findByText(/accès non autorisé/i)).toBeInTheDocument();
    expect(screen.getByText(/accès refusé pour ce tenant/i)).toBeInTheDocument();
  });

  it('gère une erreur 409 à l’activation', async () => {
    const user = userEvent.setup();
    mockActivateRuleset.mockRejectedValue({
      response: {
        status: 409,
        data: { message: 'Impossible d’activer ce Ruleset : conflit de version.' },
      },
    });
    wrap('/config/regles-notation/rs-1');
    await screen.findByRole('heading', { name: 'Pondération générale' });
    await user.click(screen.getByRole('button', { name: /^activer$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /^activer$/i }));
    await waitFor(() => expect(mockActivateRuleset).toHaveBeenCalledWith('rs-1'));
    expect(await screen.findByText(/conflit de version/i)).toBeInTheDocument();
  });

  it('active une version après confirmation', async () => {
    const user = userEvent.setup();
    mockActivateRuleset.mockResolvedValue({ ...SAMPLE_RULESET, status: 'active' });
    wrap('/config/regles-notation/rs-1');
    await screen.findByRole('heading', { name: 'Pondération générale' });
    await user.click(screen.getByRole('button', { name: /^activer$/i }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /^activer$/i }));
    await waitFor(() => expect(mockActivateRuleset).toHaveBeenCalledWith('rs-1'));
  });
});
