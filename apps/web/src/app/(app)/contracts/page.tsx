import type { Metadata } from "next"

import { ContractList } from "@/features/contracts/components/contract-list"
import { isContractView } from "@/features/contracts/constants"
import { getServerT } from "@/lib/i18n-server"

export async function generateMetadata(): Promise<Metadata> {
  const t = await getServerT()
  return { title: t("contracts.title") }
}

export default async function ContractsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>
}) {
  const { view } = await searchParams
  return <ContractList initialView={isContractView(view) ? view : "all"} />
}
