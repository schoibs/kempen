import type { Metadata } from "next";

import { CampaignDetailClient } from "@/components/CampaignDetailClient";

interface CampaignPageProps {
  params: Promise<{ campaignId: string }>;
}

export const metadata: Metadata = {
  title: "Campaign workspace",
};

export default async function CampaignDetailPage({ params }: CampaignPageProps) {
  const { campaignId } = await params;
  return <CampaignDetailClient campaignId={campaignId} />;
}
