"use client"

import type { ContractDetail } from "@workspace/api-client"
import { useHasPermission } from "@workspace/core/auth"
import { useContractPricing } from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { Skeleton } from "@/components/ui/skeleton"
import { IS_PRICING_VISIBLE } from "@/config"

import { FuelSection } from "./fuel-section"
import { PriceTableCard } from "./price-table-card"
import { PriceTableDialog } from "./price-table-dialog"

/** Whether this user may see the prices of a contract on this side (selling vs buying). */
export function useCanSeePrices(contract: Pick<ContractDetail, "side"> | undefined) {
  const canSell = useHasPermission("sell-prices:read")
  const canBuy = useHasPermission("buy-prices:read")
  if (!IS_PRICING_VISIBLE) return false
  return contract?.side === "customer" ? canSell : contract?.side === "supplier" && canBuy
}

interface PricingPanelProps {
  contract: ContractDetail
  /** Show a document's file at a page, when a price or clause citation is clicked. */
  onShowPage: (instrumentId: string, page: number) => void
}

/** The price tables and fuel clauses read from the contract's documents, in recording order. */
export function PricingPanel({ contract, onShowPage }: PricingPanelProps) {
  const { t } = useTranslation()
  const canEdit = useHasPermission("contracts:register")
  const { data, isPending, isError } = useContractPricing(contract.id)
  const isPublished = contract.status !== "draft"

  if (isPending) return <Skeleton className="h-48 w-full" />
  if (isError || !data) {
    return <p className="text-sm text-destructive">{t("list.loadError")}</p>
  }
  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-medium">{t("pricing.tables")}</h2>
          {canEdit && contract.instruments.length > 0 ? (
            <PriceTableDialog contractId={contract.id} instruments={contract.instruments} />
          ) : null}
        </div>
        {data.tables.length === 0 ? (
          <p className="rounded-xl border border-dashed p-4 text-center text-sm text-muted-foreground">
            {t("pricing.noTables")}
          </p>
        ) : (
          data.tables.map((table, index) => (
            <PriceTableCard
              key={table.id}
              table={table}
              instrument={contract.instruments.find((i) => i.id === table.instrumentId)}
              contractId={contract.id}
              isPublished={isPublished}
              canEdit={canEdit}
              defaultOpen={index === data.tables.length - 1}
              onShowPage={(page) => onShowPage(table.instrumentId, page)}
            />
          ))
        )}
      </section>
      <FuelSection
        contract={contract}
        clauses={data.fuelClauses}
        canEdit={canEdit}
        onShowPage={onShowPage}
      />
    </div>
  )
}
