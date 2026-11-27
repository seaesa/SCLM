import type { Metadata } from "next"

import { PartnerList } from "@/features/partners/components/partner-list"
import { getServerT } from "@/lib/i18n-server"

export async function generateMetadata(): Promise<Metadata> {
  const t = await getServerT()
  return { title: t("partners.title") }
}

export default function PartnersPage() {
  return <PartnerList />
}
