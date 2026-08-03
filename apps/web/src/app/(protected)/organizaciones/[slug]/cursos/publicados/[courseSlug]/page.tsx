import PublishedCourseView from '../../../biblioteca/[courseSlug]/page';

export default function PublishedCoursePage(
  props: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>,
) {
  return PublishedCourseView(props);
}
