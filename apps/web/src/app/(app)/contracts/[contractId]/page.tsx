import type { Metadata } from "next"

import { ContractDetail } from "@/features/contracts/components/contract-detail"
import { getServerT } from "@/lib/i18n-server"

export async function generateMetadata(): Promise<Metadata> {
  const t = await getServerT()
  return { title: t("contracts.title") }
}

export default async function ContractPage({
  params,
  searchParams,
}: {
  params: Promise<{ contractId: string }>
  searchParams: Promise<{ doc?: string | string[] }>
}) {
  const { contractId } = await params
  const { doc } = await searchParams
  return (
    <ContractDetail
      contractId={contractId}
      initialDocumentId={typeof doc === "string" ? doc : undefined}
    />
  )
}
