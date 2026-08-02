import { describe, expect, it } from 'vitest';

import { conceptIdsBySubjectTopic } from './subject-topics';

describe('conceptIdsBySubjectTopic', () => {
  it('excludes associations owned by topics from another subject', () => {
    const result = conceptIdsBySubjectTopic(new Set(['integral-root']), [
      { concept_ids: ['antiderivative'], entity_id: 'integral-root' },
      { concept_ids: ['derivative'], entity_id: 'differential-root' },
    ]);

    expect([...result.entries()]).toEqual([
      ['integral-root', ['antiderivative']],
    ]);
    expect(result.has('differential-root')).toBe(false);
  });
});
