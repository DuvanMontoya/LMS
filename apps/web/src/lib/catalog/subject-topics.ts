export function conceptIdsBySubjectTopic(
  subjectTopicIds: ReadonlySet<string>,
  associations: ReadonlyArray<{
    concept_ids: string[];
    entity_id: string;
  }>,
) {
  return new Map(
    associations
      .filter((association) => subjectTopicIds.has(association.entity_id))
      .map((association) => [association.entity_id, association.concept_ids]),
  );
}
