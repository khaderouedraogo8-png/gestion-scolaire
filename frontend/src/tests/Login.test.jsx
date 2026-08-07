import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Login from '../pages/auth/Login';

const mockLogin = vi.fn();
const mockClearError = vi.fn();

vi.mock('../hooks/useAuth', () => ({
  default: () => ({
    login: mockLogin,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    clearError: mockClearError,
  }),
}));

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
}

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('affiche le formulaire de connexion', () => {
    renderLogin();

    expect(screen.getByRole('heading', { name: /connexion/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/adresse email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mot de passe/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /se connecter/i })).toBeInTheDocument();
  });

  it('affiche des erreurs de validation si les champs sont vides', async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole('button', { name: /se connecter/i }));

    expect(await screen.findByText(/l'email est requis/i)).toBeInTheDocument();
    expect(screen.getByText(/le mot de passe est requis/i)).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('appelle login avec email et mot de passe valides', async () => {
    mockLogin.mockResolvedValue({ user: { doit_changer_mdp: false } });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/adresse email/i), 'admin@ecole.fr');
    await user.type(screen.getByLabelText(/mot de passe/i), 'secret123');
    await user.click(screen.getByRole('button', { name: /se connecter/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin@ecole.fr', 'secret123');
    });
  });
});
