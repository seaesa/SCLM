import type { Metadata } from "next"
import { redirect } from "next/navigation"

import { IS_OVERVIEW_VISIBLE } from "@/config"
import { OverviewDashboard } from "@/features/overview/components/overview-dashboard"
import { getServerT } from "@/lib/i18n-server"

export async function generateMetadata(): Promise<Metadata> {
  const t = await getServerT()
  return { title: t("overview.title") }
}

export default function OverviewPage() {
  if (!IS_OVERVIEW_VISIBLE) redirect("/contracts")
  return <OverviewDashboard />
}
