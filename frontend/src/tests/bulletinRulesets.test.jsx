import { describe, expect, it } from 'vitest';
import { formatBulletinRulesets } from '../utils/bulletinRulesets';

describe('formatBulletinRulesets (PR13/PR15-C)', () => {
  it('returns Sans ruleset when snapshot empty (not Legacy MV)', () => {
    expect(formatBulletinRulesets([])).toMatchObject({ label: 'Sans ruleset' });
    expect(formatBulletinRulesets(null)).toMatchObject({ label: 'Sans ruleset' });
  });

  it('formats code and version', () => {
    const out = formatBulletinRulesets([
      { ruleset_id: 'x', code: 'STD', version: 2, subject_ids: ['a'] },
    ]);
    expect(out.label).toBe('STD v2');
    expect(out.title).toBe('STD v2');
  });

  it('truncates long lists', () => {
    const out = formatBulletinRulesets([
      { code: 'A', version: 1 },
      { code: 'B', version: 1 },
      { code: 'C', version: 1 },
    ]);
    expect(out.label).toBe('A v1, B v1 +1');
  });
});
