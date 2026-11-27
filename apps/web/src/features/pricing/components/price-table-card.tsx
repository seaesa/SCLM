"use client"

import { ArrowDown01Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { createContext, use } from "react"

import type { InstrumentRead, PriceLineRead, PriceTableRead } from "@workspace/api-client"
import { formatDate } from "@workspace/core/lib/date"
import { useWithdrawPriceLine, useWithdrawPriceTable } from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { DataTable, type DataColumn } from "@/components/design-system/data-table/data-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

import { instrumentLabel } from "./instrument-select"
import { PasteLinesDialog } from "./paste-lines-dialog"
import { priceLineColumns } from "./price-line-columns"
import { PriceLineDialog } from "./price-line-dialog"
import { WithdrawDialog } from "./withdraw-dialog"

interface TableContext {
  contractId: string
  isPublished: boolean
  canEdit: boolean
  onShowPage: (page: number) => void
}

// Column cells are module-level components; they read the card they belong to from here.
const PriceTableContext = createContext<TableContext | null>(null)

function useTableContext() {
  const context = use(PriceTableContext)
  if (!context) throw new Error("Price line cells must render inside a PriceTableCard")
  return context
}

function PageCell({ page }: { page: number }) {
  const { t } = useTranslation()
  const { onShowPage } = useTableContext()
  return (
    <button
      type="button"
      className="text-xs text-primary underline-offset-4 hover:underline"
      onClick={() => onShowPage(page)}
    >
      {t("contracts.page", { page })}
    </button>
  )
}

function LineActions({ line }: { line: PriceLineRead }) {
  const { t } = useTranslation()
  const { contractId, isPublished, canEdit } = useTableContext()
  const withdraw = useWithdrawPriceLine(contractId)
  if (!canEdit) return null
  return (
    <div className="flex justify-end gap-1">
      <PriceLineDialog contractId={contractId} line={line} isPublished={isPublished} />
      <WithdrawDialog
        title={t("pricing.withdrawLine")}
        needsReason={isPublished}
        onWithdraw={(reason) =>
          withdraw.mutateAsync({ path: { lineId: line.id }, body: { reason } })
        }
      />
    </div>
  )
}

const LINE_COLUMNS: DataColumn<PriceLineRead>[] = [
  ...priceLineColumns((line: PriceLineRead) => line),
  {
    id: "page",
    label: "pricing.page",
    accessorKey: "page",
    cell: ({ row }) => <PageCell page={row.original.page} />,
  },
  {
    id: "actions",
    label: "pricing.actions",
    enableSorting: false,
    enableHiding: false,
    cell: ({ row }) => <LineActions line={row.original} />,
  },
]

const HIDDEN_COLUMNS = ["service", "note"]

interface PriceTableCardProps extends TableContext {
  table: PriceTableRead
  instrument?: InstrumentRead
  defaultOpen?: boolean
}

/** One printed price table: when it applies, how it combines with earlier ones, and its lines. */
export function PriceTableCard({
  table,
  instrument,
  defaultOpen,
  ...context
}: PriceTableCardProps) {
  const { t } = useTranslation()
  const withdraw = useWithdrawPriceTable(context.contractId)
  return (
    <PriceTableContext value={context}>
      <Collapsible defaultOpen={defaultOpen} className="group/table rounded-xl border bg-card">
        <div className="flex flex-wrap items-start gap-3 p-3">
          <CollapsibleTrigger
            render={<Button variant="ghost" size="icon-sm" aria-label={t("table.expand")} />}
          >
            <HugeiconsIcon
              icon={ArrowDown01Icon}
              className="transition-transform group-data-[closed]/table:-rotate-90"
            />
          </CollapsibleTrigger>
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">
                {t("pricing.effectiveRange", {
                  from: formatDate(table.effectiveFrom),
                  to: table.effectiveTo ? formatDate(table.effectiveTo) : t("pricing.openEnded"),
                })}
              </span>
              <Badge variant="outline">{t(`pricing.mode.${table.mode}`)}</Badge>
              <Badge variant="secondary">
                {t("pricing.lineCount", { count: table.lines.length })}
              </Badge>
            </div>
            <p className="flex flex-wrap items-baseline gap-x-2 text-sm text-muted-foreground">
              {instrument ? instrumentLabel(instrument, t) : null}
              <PageCell page={table.page} />
              {table.quote ? <q className="truncate text-xs">{table.quote}</q> : null}
            </p>
            {table.note ? <p className="text-xs text-muted-foreground">{table.note}</p> : null}
          </div>
          {context.canEdit ? (
            <div className="flex gap-1">
              <PasteLinesDialog contractId={context.contractId} table={table} />
              <WithdrawDialog
                title={t("pricing.withdrawTable")}
                needsReason={context.isPublished}
                onWithdraw={(reason) =>
                  withdraw.mutateAsync({ path: { tableId: table.id }, body: { reason } })
                }
              />
            </div>
          ) : null}
        </div>
        <CollapsibleContent className="border-t p-3">
          {table.lines.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">{t("pricing.noLines")}</p>
          ) : (
            <DataTable
              columns={LINE_COLUMNS}
              data={table.lines}
              getRowId={(line) => line.id}
              hiddenColumns={HIDDEN_COLUMNS}
            />
          )}
        </CollapsibleContent>
      </Collapsible>
    </PriceTableContext>
  )
}
