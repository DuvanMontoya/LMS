import type { components } from '@/lib/api/generated/platform';

type TopicNode = components['schemas']['Topic'];

export type CourseTopicOption = Omit<TopicNode, 'children'> & {
  ancestor_titles: string[];
  children: TopicNode['children'];
  subject_id: string;
  subject_name: string;
};

export function flattenCourseTopics(
  items: readonly TopicNode[],
  subject: { id: string; name: string },
  ancestorTitles: string[] = [],
): CourseTopicOption[] {
  return items.flatMap((topic) => {
    const children = Array.isArray(topic.children)
      ? (topic.children as TopicNode[])
      : [];
    return [
      {
        ...topic,
        ancestor_titles: ancestorTitles,
        subject_id: subject.id,
        subject_name: subject.name,
      },
      ...flattenCourseTopics(children, subject, [
        ...ancestorTitles,
        topic.title,
      ]),
    ];
  });
}
