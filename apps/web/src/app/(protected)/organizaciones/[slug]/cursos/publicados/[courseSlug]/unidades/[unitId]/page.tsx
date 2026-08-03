import PublishedUnitView from '../../../../../biblioteca/[courseSlug]/unidades/[unitId]/page';

export default function PublishedUnitPage(
  props: Readonly<{
    params: Promise<{ courseSlug: string; slug: string; unitId: string }>;
  }>,
) {
  return PublishedUnitView(props);
}
