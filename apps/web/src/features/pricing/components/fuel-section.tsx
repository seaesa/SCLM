"use client"

import { useState } from "react"

import type { AdjustedLine, ContractDetail, FuelClauseRead } from "@workspace/api-client"
import { formatDate, todayIso } from "@workspace/core/lib/date"
import { formatNumber } from "@workspace/core/lib/number"
import { useFuelAdjustment, useWithdrawFuelClause } from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { DataTable, type DataColumn } from "@/components/design-system/data-table/data-table"
import { DatePicker } from "@/components/design-system/date-picker"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

import { FuelClauseDialog } from "./fuel-clause-dialog"
import { priceLineColumns } from "./price-line-columns"
import { formatAmount, formatChange, formatShare } from "./pricing-format"
import { WithdrawDialog } from "./withdraw-dialog"

const LINE_COLUMNS = priceLineColumns((row: AdjustedLine) => row.line)
const lineColumn = (id: string) => LINE_COLUMNS.filter((column) => column.id === id)

// The proposed price sits next to the current one: in the narrow pricing pane the
// trailing columns scroll out of view, and these two are what the reader compares.
const ADJUSTED_COLUMNS: DataColumn<AdjustedLine>[] = [
  ...lineColumn("origin"),
  ...lineColumn("destination"),
  ...lineColumn("unitPrice"),
  {
    id: "proposedPrice",
    label: "pricing.fuel.proposedPrice",
    accessorFn: (row) => Number(row.proposedPrice),
    cell: ({ row }) => (
      <span className="font-semibold text-primary tabular-nums">
        {formatAmount(row.original.proposedPrice)}
      </span>
    ),
  },
  ...lineColumn("vehicle"),
]

interface FuelSectionProps {
  contract: ContractDetail
  clauses: FuelClauseRead[]
  canEdit: boolean
  onShowPage: (instrumentId: string, page: number) => void
}

/** The fuel clauses recorded for the contract and what they propose on a chosen date. */
export function FuelSection({ contract, clauses, canEdit, onShowPage }: FuelSectionProps) {
  const { t } = useTranslation()
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-medium">{t("pricing.fuel.title")}</h2>
        {canEdit && contract.instruments.length > 0 ? (
          <FuelClauseDialog contractId={contract.id} instruments={contract.instruments} />
        ) : null}
      </div>
      {clauses.length === 0 ? (
        <p className="rounded-xl border border-dashed p-4 text-center text-sm text-muted-foreground">
          {t("pricing.fuel.noClause")}
        </p>
      ) : (
        clauses.map((clause, index) => (
          <FuelClauseCard
            key={clause.id}
            clause={clause}
            isGoverning={index === clauses.length - 1}
            isPublished={contract.status !== "draft"}
            canEdit={canEdit}
            onShowPage={(page) => onShowPage(clause.instrumentId, page)}
          />
        ))
      )}
      {clauses.length > 0 ? <FuelAdjustmentCard contractId={contract.id} /> : null}
    </section>
  )
}

function FuelClauseCard({
  clause,
  isGoverning,
  isPublished,
  canEdit,
  onShowPage,
}: {
  clause: FuelClauseRead
  isGoverning: boolean
  isPublished: boolean
  canEdit: boolean
  onShowPage: (page: number) => void
}) {
  const { t } = useTranslation()
  const withdraw = useWithdrawFuelClause(clause.contractId)
  const terms = [
    { label: t("pricing.fuel.basePrice"), value: formatAmount(clause.basePrice) },
    { label: t("pricing.fuel.baseOn"), value: formatDate(clause.baseOn) },
    { label: t("pricing.fuel.share"), value: formatShare(clause.share) },
    { label: t("pricing.fuel.threshold"), value: `±${formatShare(clause.threshold)}` },
    {
      label: t("pricing.fuel.reference"),
      value: t(clause.isCumulative ? "pricing.fuel.cumulative" : "pricing.fuel.stepwise"),
    },
    { label: t("pricing.fuel.lagDays"), value: String(clause.lagDays) },
    { label: t("pricing.fuel.rounding"), value: t(`pricing.rounding.${clause.rounding}`) },
  ]
  return (
    <div className={cn("rounded-xl border bg-card", isGoverning && "ring-2 ring-primary/30")}>
      <div className="flex flex-wrap items-center gap-2 border-b p-3">
        <span className="font-medium">{clause.fuelType}</span>
        {isGoverning ? <Badge>{t("pricing.fuel.governing")}</Badge> : null}
        <button
          type="button"
          className="text-xs text-primary underline-offset-4 hover:underline"
          onClick={() => onShowPage(clause.page)}
        >
          {t("contracts.page", { page: clause.page })}
        </button>
        <span className="flex-1" />
        {canEdit ? (
          <WithdrawDialog
            title={t("pricing.fuel.withdrawClause")}
            needsReason={isPublished}
            onWithdraw={(reason) =>
              withdraw.mutateAsync({ path: { clauseId: clause.id }, body: { reason } })
            }
          />
        ) : null}
      </div>
      <dl className="grid grid-cols-2 sm:grid-cols-4">
        {terms.map((term) => (
          <div key={term.label} className="flex flex-col gap-0.5 border-b px-3 py-2">
            <dt className="text-xs text-muted-foreground">{term.label}</dt>
            <dd className="text-sm font-medium tabular-nums">{term.value}</dd>
          </div>
        ))}
      </dl>
      {clause.quote ? (
        <q className="block px-3 py-2 text-xs text-muted-foreground">{clause.quote}</q>
      ) : null}
    </div>
  )
}

function FuelAdjustmentCard({ contractId }: { contractId: string }) {
  const { t } = useTranslation()
  const [on, setOn] = useState(todayIso)
  const { data, isPending, isError } = useFuelAdjustment(contractId, on)
  const proposal = data?.proposal
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium">{t("pricing.fuel.adjustment")}</h3>
        <div className="w-48">
          <DatePicker
            id="fuel-adjustment-on"
            value={on}
            onChange={(value) => value && setOn(value)}
          />
        </div>
      </div>
      {isPending ? <Skeleton className="h-16 w-full" /> : null}
      {isError ? <p className="text-sm text-destructive">{t("list.loadError")}</p> : null}
      {data && !proposal ? (
        <p className="text-sm text-muted-foreground">{t("pricing.fuel.noProposal")}</p>
      ) : null}
      {proposal ? (
        <>
          <Alert>
            <AlertTitle>
              {t("pricing.fuel.proposalTitle", {
                change: formatChange(proposal.change),
                date: formatDate(proposal.effectiveOn),
              })}
            </AlertTitle>
            <AlertDescription>
              {t("pricing.fuel.proposalDetail", {
                fuelOn: formatDate(proposal.fuelOn),
                fuelPrice: formatAmount(proposal.fuelPrice),
                referencePrice: formatAmount(proposal.referencePrice),
                factor: formatNumber(Number(proposal.factor), { maximumFractionDigits: 4 }),
              })}
            </AlertDescription>
          </Alert>
          {data.lines.length > 0 ? (
            <DataTable
              columns={ADJUSTED_COLUMNS}
              data={data.lines}
              getRowId={(row) => row.line.id}
            />
          ) : null}
        </>
      ) : null}
    </div>
  )
}
