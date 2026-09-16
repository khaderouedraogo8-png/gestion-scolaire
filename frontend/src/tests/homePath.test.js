import { describe, expect, it } from 'vitest';
import { homePathForRole } from '../utils/homePath';

describe('homePathForRole', () => {
  it('redirige parent vers /parent', () => {
    expect(homePathForRole('parent')).toBe('/parent');
  });

  it('redirige enseignant vers /dashboard (plus de 403)', () => {
    expect(homePathForRole('enseignant')).toBe('/dashboard');
  });

  it('redirige direction et comptable vers /dashboard', () => {
    expect(homePathForRole('directeur')).toBe('/dashboard');
    expect(homePathForRole('administrateur')).toBe('/dashboard');
    expect(homePathForRole('agent_comptable')).toBe('/dashboard');
    expect(homePathForRole('secretariat')).toBe('/dashboard');
  });

  it('redirige super_admin vers plateforme', () => {
    expect(homePathForRole('super_admin')).toBe('/platform/schools');
  });
});
