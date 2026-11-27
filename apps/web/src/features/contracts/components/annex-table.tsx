"use client"

import Link from "next/link"

import type { InstrumentListItem } from "@workspace/api-client"
import { formatDate } from "@workspace/core/lib/date"
import { useTranslation } from "@workspace/i18n"

import { Badge } from "@/components/ui/badge"
import { TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { InstrumentStateBadges } from "./instrument-state-badges"
import { StandingBadge } from "./standing-badge"

/** Column headings shared by the annexes of one contract and the addenda list. */
export function AnnexTableHeader() {
  const { t } = useTranslation()
  return (
    <TableHeader>
      <TableRow>
        <TableHead>{t("contracts.annexes.columns.code")}</TableHead>
        <TableHead>{t("contracts.annexes.columns.number")}</TableHead>
        <TableHead>{t("contracts.annexes.columns.kind")}</TableHead>
        <TableHead>{t("contracts.annexes.columns.effective")}</TableHead>
        <TableHead>{t("contracts.annexes.columns.adjustments")}</TableHead>
        <TableHead>{t("contracts.annexes.columns.state")}</TableHead>
      </TableRow>
    </TableHeader>
  )
}

/** One addendum, schedule or termination; the code opens it beside its scan. */
export function AnnexRow({ annex }: { annex: InstrumentListItem }) {
  const { t } = useTranslation()
  return (
    <TableRow>
      <TableCell className="max-w-80 whitespace-normal">
        <div className="flex flex-wrap items-center gap-1.5">
          <Link
            href={`/contracts/${annex.contractId}?doc=${annex.id}`}
            className="font-mono text-[13px] font-medium underline-offset-4 hover:underline"
          >
            {annex.code ?? "—"}
          </Link>
          <StandingBadge standing={annex.standing} replacedByCode={annex.replacedByCode} />
        </div>
        {annex.summary ? (
          <p className="line-clamp-2 text-xs text-muted-foreground">{annex.summary}</p>
        ) : null}
      </TableCell>
      <TableCell>{annex.number ?? "—"}</TableCell>
      <TableCell className="whitespace-nowrap">
        {t(`contracts.instrumentKind.${annex.kind}`)}
      </TableCell>
      <TableCell className="whitespace-nowrap">
        <DateSpan
          from={annex.effectiveFrom}
          to={annex.kind === "termination" ? annex.effectiveFrom : annex.effectiveTo}
        />
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          {annex.adjustments.map((adjustment) => (
            <Badge key={adjustment} variant="outline">
              {t(`contracts.choices.${adjustment}`)}
            </Badge>
          ))}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1.5">
          {annex.missingCount > 0 ? (
            <Badge variant="destructive">
              {t("contracts.missingFacts", { count: annex.missingCount })}
            </Badge>
          ) : null}
          <InstrumentStateBadges
            reviewState={annex.reviewState}
            signingState={annex.signingState}
          />
        </div>
      </TableCell>
    </TableRow>
  )
}

/** "Từ X" when only a start is known, "X → Y" for a period, one date when both are the same. */
export function DateSpan({ from, to }: { from?: string | null; to?: string | null }) {
  const { t } = useTranslation()
  if (!from && !to) return <span className="text-muted-foreground">—</span>
  if (from && (!to || to === from)) {
    return (
      <span className="tabular-nums">
        {to === from ? formatDate(from) : t("date.since", { date: formatDate(from) })}
      </span>
    )
  }
  if (!from)
    return (
      <span className="tabular-nums">{t("date.until", { date: formatDate(to as string) })}</span>
    )
  return (
    <span className="tabular-nums">
      {formatDate(from)} → {to ? formatDate(to) : null}
    </span>
  )
}
