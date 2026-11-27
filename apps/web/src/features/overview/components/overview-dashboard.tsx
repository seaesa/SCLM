"use client"

import type { Route } from "next"
import Link from "next/link"

import type { ContractStatus, Overview } from "@workspace/api-client"
import { formatDate } from "@workspace/core/lib/date"
import { formatNumber } from "@workspace/core/lib/number"
import { useOverview } from "@workspace/core/overview"
import { useTranslation } from "@workspace/i18n"

import { ListStates } from "@/components/design-system/list-states"
import { PageBody, PageHeader } from "@/components/design-system/page-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

// Fixed order so a status keeps its row whatever the counts are.
const STATUS_ORDER: ContractStatus[] = [
  "active",
  "not_yet_effective",
  "draft",
  "undetermined",
  "expired",
  "replaced",
  "terminated",
]

export function OverviewDashboard() {
  const { t } = useTranslation()
  const overview = useOverview()
  return (
    <>
      <PageHeader
        title={t("overview.title")}
        description={
          overview.data ? t("overview.asOf", { date: formatDate(overview.data.on) }) : undefined
        }
      />
      <PageBody>
        <ListStates
          isPending={overview.isPending}
          isError={overview.isError}
          isEmpty={false}
          onRetry={() => void overview.refetch()}
        >
          {overview.data && <Dashboard data={overview.data} />}
        </ListStates>
      </PageBody>
    </>
  )
}

function Dashboard({ data }: { data: Overview }) {
  const { t } = useTranslation()
  const counts = new Map<ContractStatus, number>()
  // An automatically renewed contract is still in force: count it with the active ones.
  for (const item of data.contracts.byStatus) {
    const status = item.status === "auto_renewed" ? "active" : item.status
    counts.set(status, (counts.get(status) ?? 0) + item.count)
  }
  const inForce = counts.get("active") ?? 0
  const total = data.contracts.byStatus.reduce((sum, item) => sum + item.count, 0)
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatTile label={t("overview.inForce")} value={inForce} of={total} href="/contracts" />
        <StatTile
          label={t("overview.expiring")}
          value={data.contracts.expiringSoon}
          href="/contracts?view=due"
        />
        <StatTile
          label={t("overview.noticeSoon")}
          value={data.contracts.noticeSoon}
          href="/contracts?view=due"
        />
        <StatTile
          label={t("overview.awaitingApproval")}
          value={data.contracts.awaitingApproval}
          href="/contracts?view=awaiting_approval"
        />
        <StatTile
          label={t("overview.awaitingSignature")}
          value={data.contracts.awaitingSignature}
          href="/contracts?view=awaiting_signature"
        />
      </div>
      <StatusBars counts={counts} total={total} />
    </div>
  )
}

interface StatTileProps {
  label: string
  value: number
  of?: number
  href: Route
}

function StatTile({ label, value, of, href }: StatTileProps) {
  const { t } = useTranslation()
  const share = of ? Math.round((value / of) * 100) : undefined
  return (
    <Link href={href} className="group rounded-xl outline-none focus-visible:ring-2">
      <Card className="h-full transition-colors group-hover:bg-muted/40">
        <CardHeader>
          <CardDescription>{label}</CardDescription>
          <CardTitle className="text-3xl tabular-nums">
            {formatNumber(value)}
            {of !== undefined && (
              <span className="ml-1 text-base font-normal text-muted-foreground">
                / {formatNumber(of)}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {share !== undefined && (
            <Progress value={share} aria-label={t("overview.share", { share })} />
          )}
        </CardContent>
      </Card>
    </Link>
  )
}

function StatusBars({ counts, total }: { counts: Map<ContractStatus, number>; total: number }) {
  const { t } = useTranslation()
  const max = Math.max(1, ...counts.values())
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("overview.byStatus")}</CardTitle>
      </CardHeader>
      <CardContent>
        {total === 0 ? (
          <p className="text-sm text-muted-foreground">{t("overview.noContracts")}</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {STATUS_ORDER.map((status) => {
              const count = counts.get(status) ?? 0
              const label = t(`contracts.status.${status}`)
              return (
                <li
                  key={status}
                  className="grid grid-cols-[9rem_1fr_3rem] items-center gap-3 text-sm"
                  title={`${label}: ${formatNumber(count)}`}
                >
                  <span className="truncate text-muted-foreground">{label}</span>
                  <span className="h-2 rounded-full bg-muted">
                    <span
                      className="block h-full rounded-full bg-primary"
                      style={{ width: `${(count / max) * 100}%` }}
                    />
                  </span>
                  <span className="text-right tabular-nums">{formatNumber(count)}</span>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
