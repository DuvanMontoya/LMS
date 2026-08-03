import { ScreenShareEgress } from '@/components/scheduling/screen-share-egress';

export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';
export const revalidate = 0;

export default function LiveKitEgressPage() {
  return <ScreenShareEgress />;
}
