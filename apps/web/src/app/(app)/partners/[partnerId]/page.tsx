import type { Metadata } from "next"

import { PartnerDetail } from "@/features/partners/components/partner-detail"
import { getServerT } from "@/lib/i18n-server"

export async function generateMetadata(): Promise<Metadata> {
  const t = await getServerT()
  return { title: t("partners.title") }
}

export default async function PartnerPage({ params }: { params: Promise<{ partnerId: string }> }) {
  const { partnerId } = await params
  return <PartnerDetail partnerId={partnerId} />
}
