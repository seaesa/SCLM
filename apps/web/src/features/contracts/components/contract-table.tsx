"use client"

import { differenceInCalendarDays, parseISO } from "date-fns"
import { useRouter } from "next/navigation"

import type { ContractRead } from "@workspace/api-client"
import { formatDate, todayIso } from "@workspace/core/lib/date"
import { useTranslation } from "@workspace/i18n"

import {
  DataTable,
  Translated,
  type DataColumn,
} from "@/components/design-system/data-table/data-table"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

import { DateSpan } from "./annex-table"
import { ContractAnnexes } from "./contract-annexes"
import { ContractValue } from "./contract-facts"
import { ContractStatusBadge } from "./contract-status-badge"
import { MissingFactsBadge } from "./missing-facts-badge"

// The server orders the list (see the sort control), so columns do not sort one page.
const COLUMNS: DataColumn<ContractRead>[] = [
  {
    id: "contract",
    label: "contracts.columns.contract",
    enableSorting: false,
    enableHiding: false,
    accessorFn: (row) => `${row.code ?? ""} ${row.partner.name}`,
    cell: ({ row }) => <ContractCell contract={row.original} />,
  },
  {
    id: "status",
    label: "contracts.columns.status",
    enableSorting: false,
    accessorKey: "status",
    cell: ({ row }) => <ContractStatusBadge status={row.original.status} />,
  },
  {
    id: "term",
    label: "contracts.columns.term",
    enableSorting: false,
    accessorFn: (row) => row.endOn ?? "",
    cell: ({ row }) => <TermCell contract={row.original} />,
  },
  {
    id: "noticeOn",
    label: "contracts.noticeOnLabel",
    enableSorting: false,
    accessorFn: (row) => row.noticeOn ?? "",
    cell: ({ row }) => <DateCell value={row.original.noticeOn} />,
  },
  {
    id: "payment",
    label: "contracts.columns.payment",
    enableSorting: false,
    accessorFn: (row) => row.paymentDays ?? "",
    cell: ({ row }) => <PaymentCell contract={row.original} />,
  },
  {
    id: "addenda",
    label: "contracts.columns.addenda",
    enableSorting: false,
    accessorKey: "addendumCount",
    cell: ({ row }) => <span className="tabular-nums">{row.original.addendumCount}</span>,
  },
  {
    id: "owner",
    label: "contracts.columns.owner",
    enableSorting: false,
    accessorFn: (row) => row.owner?.name ?? "",
    cell: ({ row }) => <OwnerCell name={row.original.owner?.name} />,
  },
  {
    id: "missing",
    label: "contracts.columns.missing",
    enableSorting: false,
    accessorKey: "missingCount",
    cell: ({ row }) => <MissingCell facts={row.original.missingFacts} />,
  },
  {
    id: "category",
    label: "contracts.columns.category",
    enableSorting: false,
    accessorKey: "category",
    cell: ({ row }) => <Translated label={`contracts.category.${row.original.category}`} />,
  },
  {
    id: "signedOn",
    label: "contracts.fields.signed_on",
    enableSorting: false,
    accessorFn: (row) => row.signedOn ?? "",
    cell: ({ row }) => <DateCell value={row.original.signedOn} />,
  },
  {
    id: "value",
    label: "contracts.fields.value_amount",
    enableSorting: false,
    accessorFn: (row) => row.valueAmount ?? "",
    cell: ({ row }) => <ContractValue contract={row.original} />,
  },
  {
    id: "number",
    label: "contracts.fields.number",
    enableSorting: false,
    accessorFn: (row) => row.number ?? "",
    cell: ({ row }) => row.original.number ?? "—",
  },
]

const HIDDEN_COLUMNS = ["category", "signedOn", "number", "value"]

/** Contracts as a table; a row opens the contract, the arrow unfolds its addenda. */
export function ContractTable({
  contracts,
  toolbar,
  footer,
}: {
  contracts: ContractRead[]
  toolbar?: React.ReactNode
  footer?: React.ReactNode
}) {
  const router = useRouter()
  return (
    <DataTable
      columns={COLUMNS}
      data={contracts}
      getRowId={(row) => row.id}
      hiddenColumns={HIDDEN_COLUMNS}
      onRowClick={(row) => router.push(`/contracts/${row.id}`)}
      toolbar={toolbar}
      footer={footer}
      renderExpanded={(contract) => <ContractAnnexes contract={contract} />}
    />
  )
}

/** Code over partner: the two things people recognise a contract by. */
function ContractCell({ contract }: { contract: ContractRead }) {
  const { t } = useTranslation()
  return (
    <div className="flex min-w-56 flex-col gap-0.5">
      <span className="font-mono text-[13px] font-medium whitespace-nowrap">
        {contract.code ?? t("contracts.noCode")}
      </span>
      <span className="line-clamp-1 text-xs text-muted-foreground">
        {contract.partner.code} · {contract.partner.name}
      </span>
    </div>
  )
}

function DateCell({ value }: { value: string | null }) {
  if (!value) return <span className="text-muted-foreground">—</span>
  return <span className="whitespace-nowrap tabular-nums">{formatDate(value)}</span>
}

/** From–to, with the days left while the contract still runs. */
function TermCell({ contract }: { contract: ContractRead }) {
  const { t } = useTranslation()
  const { effectiveFrom, endOn } = contract
  if (!effectiveFrom && !endOn) return <span className="text-muted-foreground">—</span>
  const left = endOn ? differenceInCalendarDays(parseISO(endOn), parseISO(todayIso())) : null
  const isRunning = contract.status === "active" || contract.status === "auto_renewed"
  return (
    <div className="flex flex-col gap-0.5 whitespace-nowrap">
      <span className="flex items-center gap-1.5">
        <DateSpan from={effectiveFrom} to={endOn} />
        {contract.status === "auto_renewed" ? (
          <Badge variant="outline">{t("contracts.renewedTag")}</Badge>
        ) : null}
      </span>
      {isRunning && left !== null && left >= 0 ? (
        <span className={cn("text-xs", left <= 30 ? "text-destructive" : "text-muted-foreground")}>
          {t("contracts.daysLeft", { count: left })}
        </span>
      ) : null}
    </div>
  )
}

/** Credit term over the cut-off it is counted from: what the accountant chases each month. */
function PaymentCell({ contract }: { contract: ContractRead }) {
  const { t } = useTranslation()
  const { paymentDays, paymentBusinessDays, paymentFrom, statementCutoff } = contract
  if (paymentDays === null && !statementCutoff) {
    return <span className="text-muted-foreground">—</span>
  }
  const days =
    paymentDays === null
      ? null
      : t(paymentBusinessDays ? "contracts.payment.businessDays" : "contracts.payment.days", {
          count: paymentDays,
        })
  // Where the days count from means nothing without the days; "other" has nothing short to say.
  const from =
    days && paymentFrom && paymentFrom !== "other" ? t(`contracts.payment.from.${paymentFrom}`) : ""
  let cutoff = ""
  if (statementCutoff === "month_end") cutoff = t("contracts.payment.cutoffMonthEnd")
  else if (statementCutoff) cutoff = t("contracts.payment.cutoffDay", { day: statementCutoff })
  return (
    <div className="flex flex-col gap-0.5 whitespace-nowrap">
      <span className="tabular-nums">{[days, from].filter(Boolean).join(" ") || "—"}</span>
      {cutoff ? <span className="text-xs text-muted-foreground">{cutoff}</span> : null}
    </div>
  )
}

function OwnerCell({ name }: { name?: string }) {
  if (!name) return <span className="text-muted-foreground">—</span>
  const initials = name
    .split(" ")
    .slice(-2)
    .map((word) => word[0])
    .join("")
  return (
    <div className="flex items-center gap-2 whitespace-nowrap">
      <span className="flex size-6 items-center justify-center rounded-full bg-muted text-[10px] font-medium">
        {initials}
      </span>
      {name}
    </div>
  )
}

function MissingCell({ facts }: { facts: ContractRead["missingFacts"] }) {
  if (facts.length === 0) return <span className="text-muted-foreground">—</span>
  return <MissingFactsBadge facts={facts} />
}
