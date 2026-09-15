import { describe, expect, it } from 'vitest';
import {
  formatMoyenneDisplay,
  formatResultSource,
  formatRulesetRef,
} from '../utils/academicResultsDisplay';

describe('academicResultsDisplay (PR14)', () => {
  it('does not display missing moyenne as zero', () => {
    expect(formatMoyenneDisplay(null)).toBe('—');
    expect(formatMoyenneDisplay(undefined)).toBe('—');
    expect(formatMoyenneDisplay(0)).toBe('0.00/20');
    expect(formatMoyenneDisplay(13.6)).toBe('13.60/20');
  });

  it('labels source without inventing weights', () => {
    expect(formatResultSource('rules_engine')).toBe('Ruleset');
    expect(formatResultSource('legacy')).toBe('Legacy');
  });

  it('formats ruleset ref from API fields only', () => {
    expect(formatRulesetRef({ ruleset_code: 'STD', ruleset_version: 2 })).toBe('STD v2');
    expect(formatRulesetRef({})).toBe('—');
  });
});
