import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Programmes from '../pages/etablissement/Programmes';
import Periodes from '../pages/etablissement/Periodes';
import Niveaux from '../pages/etablissement/Niveaux';
import Classes from '../pages/etablissement/Classes';
import { ToastProvider } from '../components/Toast';
import {
  apiErrorMessage,
  formatNiveauWithProgram,
  periodTypeLabel,
} from '../utils/academicLabels';

const mockListPrograms = vi.fn();
const mockCreateProgram = vi.fn();
const mockUpdateProgram = vi.fn();
const mockDeactivateProgram = vi.fn();
const mockListPeriodes = vi.fn();
const mockCreatePeriode = vi.fn();
const mockListAnnees = vi.fn();
const mockListNiveaux = vi.fn();
const mockCreateNiveau = vi.fn();
const mockUpdateNiveau = vi.fn();
const mockListClasses = vi.fn();
const mockCreateClasse = vi.fn();

vi.mock('../services/api/config', () => ({
  configApi: {
    listPrograms: (...args) => mockListPrograms(...args),
    createProgram: (...args) => mockCreateProgram(...args),
    updateProgram: (...args) => mockUpdateProgram(...args),
    deactivateProgram: (...args) => mockDeactivateProgram(...args),
    getProgram: vi.fn(),
    listPeriodes: (...args) => mockListPeriodes(...args),
    createPeriode: (...args) => mockCreatePeriode(...args),
    updatePeriode: vi.fn(),
    deactivatePeriode: vi.fn(),
    listAnnees: (...args) => mockListAnnees(...args),
    listNiveaux: (...args) => mockListNiveaux(...args),
    createNiveau: (...args) => mockCreateNiveau(...args),
    updateNiveau: (...args) => mockUpdateNiveau(...args),
    listClasses: (...args) => mockListClasses(...args),
    createClasse: (...args) => mockCreateClasse(...args),
    updateClasse: vi.fn(),
  },
}));

vi.mock('../services/api/emploi', () => ({
  emploiApi: {
    listEnseignants: vi.fn().mockResolvedValue([]),
  },
}));

function wrap(ui, initial = '/etablissement/programmes') {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/etablissement/programmes" element={<Programmes />} />
          <Route path="/etablissement/periodes" element={<Periodes />} />
          <Route path="/etablissement/niveaux" element={<Niveaux />} />
          <Route path="/etablissement/classes" element={<Classes />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>
  );
}

const GENERAL = {
  id: 'p-gen',
  code: 'GENERAL',
  name: 'Général',
  program_type: 'general',
  period_type_default: 'trimestre',
  is_active: true,
  levels_count: 2,
  classes_count: 3,
};

const TECH = {
  id: 'p-tech',
  code: 'TECH',
  name: 'Technique',
  program_type: 'technique',
  period_type_default: 'semestre',
  is_active: true,
  levels_count: 1,
  classes_count: 0,
};

describe('academicLabels helpers', () => {
  it('formate niveau · programme', () => {
    expect(
      formatNiveauWithProgram({ libelle: '2nde', id_program: 'p-gen' }, { 'p-gen': GENERAL })
    ).toBe('2nde · Général');
  });

  it('libellés période > 3 / semestre / custom', () => {
    expect(periodTypeLabel('semestre')).toBe('Semestre');
    expect(periodTypeLabel('custom')).toBe('Personnalisée');
    expect(periodTypeLabel('annuel')).toBe('Annuelle');
  });

  it('mappe 403 / 404 / 409 / réseau', () => {
    expect(apiErrorMessage({ response: { status: 403, data: {} } })).toMatch(/non autorisé/i);
    expect(apiErrorMessage({ response: { status: 404, data: {} } })).toMatch(/introuvable/i);
    expect(
      apiErrorMessage({
        response: { status: 409, data: { message: 'Conflit séquence' } },
      })
    ).toBe('Conflit séquence');
    expect(apiErrorMessage({ request: {} })).toMatch(/réseau/i);
  });
});

describe('Programmes page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListPrograms.mockResolvedValue({ items: [GENERAL, TECH] });
  });

  it('affiche les programmes avec badge historique GENERAL', async () => {
    wrap(<Programmes />);
    expect(await screen.findByText('TECH')).toBeInTheDocument();
    expect(screen.getByText('Historique')).toBeInTheDocument();
    expect(screen.getByText(/2 niv\./)).toBeInTheDocument();
  });

  it('crée un programme', async () => {
    const user = userEvent.setup();
    mockCreateProgram.mockResolvedValue({ ...TECH, id: 'new' });
    wrap(<Programmes />);
    await screen.findByText('TECH');
    await user.click(screen.getByRole('button', { name: /nouveau programme/i }));
    await user.type(screen.getByLabelText(/code/i), 'PRO');
    await user.type(screen.getByLabelText(/^nom/i), 'Professionnel');
    await user.click(screen.getByRole('button', { name: /^créer$/i }));
    await waitFor(() => {
      expect(mockCreateProgram).toHaveBeenCalled();
    });
    expect(mockCreateProgram.mock.calls[0][0].code).toBe('PRO');
  });

  it('modifie un programme', async () => {
    const user = userEvent.setup();
    mockUpdateProgram.mockResolvedValue(TECH);
    wrap(<Programmes />);
    await screen.findByText('TECH');
    const row = screen.getByText('TECH').closest('tr');
    await user.click(within(row).getByRole('button', { name: /modifier/i }));
    const nameInput = screen.getByLabelText(/^nom/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'Technique industrielles');
    await user.click(screen.getByRole('button', { name: /enregistrer/i }));
    await waitFor(() => expect(mockUpdateProgram).toHaveBeenCalled());
  });

  it('désactive un programme non-GENERAL après confirmation', async () => {
    const user = userEvent.setup();
    mockDeactivateProgram.mockResolvedValue({ ...TECH, is_active: false });
    wrap(<Programmes />);
    await screen.findByText('TECH');
    const row = screen.getByText('TECH').closest('tr');
    await user.click(within(row).getByRole('button', { name: /désactiver/i }));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText(/sera désactivé/i)).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /^désactiver$/i }));
    await waitFor(() => expect(mockDeactivateProgram).toHaveBeenCalledWith('p-tech'));
  });

  it('gère empty state', async () => {
    mockListPrograms.mockResolvedValue({ items: [] });
    wrap(<Programmes />);
    expect(await screen.findByText(/aucun programme pour cette école/i)).toBeInTheDocument();
  });

  it('gère erreur de chargement', async () => {
    mockListPrograms.mockRejectedValue({ response: { status: 403, data: {} } });
    wrap(<Programmes />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('affiche conflit 409 à la création', async () => {
    const user = userEvent.setup();
    mockCreateProgram.mockRejectedValue({
      response: { status: 409, data: { message: 'Un programme avec le code « TECH » existe déjà.' } },
    });
    wrap(<Programmes />);
    await screen.findByText('TECH');
    await user.click(screen.getByRole('button', { name: /nouveau programme/i }));
    await user.type(screen.getByLabelText(/code/i), 'TECH');
    await user.type(screen.getByLabelText(/^nom/i), 'Dup');
    await user.click(screen.getByRole('button', { name: /^créer$/i }));
    expect(await screen.findByText(/existe déjà/i)).toBeInTheDocument();
  });
});

describe('Périodes page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListAnnees.mockResolvedValue({
      items: [{ id: 'a1', libelle: '2025-2026', est_active: true }],
    });
    mockListPrograms.mockResolvedValue({ items: [GENERAL, TECH] });
    mockListPeriodes.mockResolvedValue({
      items: [
        {
          id: 'per1',
          sequence: 1,
          code: 'T1',
          label: 'Trimestre 1',
          period_type: 'trimestre',
          date_debut: '2025-09-01',
          date_fin: '2025-12-15',
          is_active: true,
          id_annee: 'a1',
          id_program: 'p-gen',
        },
        {
          id: 'per4',
          sequence: 4,
          code: 'P4',
          label: 'Période 4',
          period_type: 'custom',
          date_debut: '2026-04-01',
          date_fin: '2026-06-30',
          is_active: true,
          id_annee: 'a1',
          id_program: 'p-gen',
        },
        {
          id: 'sem1',
          sequence: 1,
          code: 'S1',
          label: 'Semestre 1',
          period_type: 'semestre',
          date_debut: '2025-09-01',
          date_fin: '2026-01-31',
          is_active: true,
          id_annee: 'a1',
          id_program: 'p-tech',
        },
      ],
    });
  });

  it('affiche périodes y compris séquence > 3 et custom', async () => {
    wrap(<Periodes />, '/etablissement/periodes?annee=a1&program=p-gen');
    expect(await screen.findByText('Trimestre 1')).toBeInTheDocument();
    expect(screen.getByText('Période 4')).toBeInTheDocument();
    expect(screen.getByText('Personnalisée')).toBeInTheDocument();
  });

  it('crée une période semestre', async () => {
    const user = userEvent.setup();
    mockCreatePeriode.mockResolvedValue({ id: 'new' });
    wrap(<Periodes />, '/etablissement/periodes?annee=a1&program=p-tech');
    await screen.findByText('Semestre 1');
    await user.click(screen.getByRole('button', { name: /nouvelle période/i }));
    await user.clear(screen.getByLabelText(/^code/i));
    await user.type(screen.getByLabelText(/^code/i), 'S2');
    await user.clear(screen.getByLabelText(/^libellé/i));
    await user.type(screen.getByLabelText(/^libellé/i), 'Semestre 2');
    await user.selectOptions(screen.getByLabelText(/^type/i), 'semestre');
    await user.type(screen.getByLabelText(/date début/i), '2026-02-01');
    await user.type(screen.getByLabelText(/date fin/i), '2026-06-30');
    await user.click(screen.getByRole('button', { name: /^créer$/i }));
    await waitFor(() => expect(mockCreatePeriode).toHaveBeenCalled());
    expect(mockCreatePeriode.mock.calls[0][0].period_type).toBe('semestre');
  });

  it('bloque dates invalides côté UX', async () => {
    const user = userEvent.setup();
    wrap(<Periodes />, '/etablissement/periodes?annee=a1&program=p-gen');
    await screen.findByText('Trimestre 1');
    await user.click(screen.getByRole('button', { name: /nouvelle période/i }));
    await user.type(screen.getByLabelText(/^code/i), 'T2');
    await user.type(screen.getByLabelText(/^libellé/i), 'Trimestre 2');
    await user.type(screen.getByLabelText(/date début/i), '2026-06-01');
    await user.type(screen.getByLabelText(/date fin/i), '2026-01-01');
    await user.click(screen.getByRole('button', { name: /^créer$/i }));
    expect(
      await screen.findByText(/date de fin doit être postérieure/i)
    ).toBeInTheDocument();
    expect(mockCreatePeriode).not.toHaveBeenCalled();
  });
});

describe('Niveaux / Classes programme coherence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListPrograms.mockResolvedValue({ items: [GENERAL, TECH] });
    mockListNiveaux.mockResolvedValue([
      { id: 'n1', libelle: '2nde', ordre: 1, cycle: 'second', id_program: 'p-gen' },
      { id: 'n2', libelle: '2nde', ordre: 1, cycle: 'second', id_program: 'p-tech' },
    ]);
    mockListAnnees.mockResolvedValue({
      items: [{ id: 'a1', libelle: '2025-2026', est_active: true }],
    });
    mockListClasses.mockResolvedValue([]);
  });

  it('affiche 2nde · Général et 2nde · Technique', async () => {
    wrap(<Niveaux />, '/etablissement/niveaux');
    expect(await screen.findByText('2nde · Général')).toBeInTheDocument();
    expect(screen.getByText('2nde · Technique')).toBeInTheDocument();
  });

  it('filtre les niveaux du formulaire classe selon le programme', async () => {
    const user = userEvent.setup();
    wrap(<Classes />, '/etablissement/classes');
    await waitFor(() => expect(mockListClasses).toHaveBeenCalled());
    await user.click(screen.getByRole('button', { name: /nouvelle classe/i }));
    await user.selectOptions(screen.getByLabelText(/^programme/i), 'p-tech');
    const niveauSelect = screen.getByLabelText(/^niveau/i);
    const options = within(niveauSelect).getAllByRole('option');
    const labels = options.map((o) => o.textContent);
    expect(labels.some((l) => l.includes('Technique'))).toBe(true);
    expect(labels.some((l) => l.includes('Général'))).toBe(false);
  });
});
