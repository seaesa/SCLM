"use client"

import Link from "next/link"
import { useState } from "react"

import type { ContractRead } from "@workspace/api-client"
import { useInstruments } from "@workspace/core/contracts"
import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody } from "@/components/ui/table"

import { AnnexRow, AnnexTableHeader } from "./annex-table"

const PREVIEW_SIZE = 5
const FULL_SIZE = 100

/** The latest annexes of one contract, newest first, under labelled columns. */
export function ContractAnnexes({ contract }: { contract: ContractRead }) {
  const { t } = useTranslation()
  const [size, setSize] = useState(PREVIEW_SIZE)
  const { data, isPending } = useInstruments({ contractId: contract.id, pageSize: size })
  if (isPending) return <Skeleton className="h-16 w-full" />
  const annexes = data?.items ?? []
  const total = data?.total ?? 0
  return (
    <div className="flex flex-col gap-2">
      {annexes.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("contracts.annexes.none")}</p>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-background">
          <Table>
            <AnnexTableHeader />
            <TableBody>
              {annexes.map((annex) => (
                <AnnexRow key={annex.id} annex={annex} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <div className="flex gap-2">
        <Button nativeButton={false} size="sm" render={<Link href={`/contracts/${contract.id}`} />}>
          {t("contracts.open")}
        </Button>
        {total > annexes.length ? (
          <Button variant="outline" size="sm" onClick={() => setSize(FULL_SIZE)}>
            {t("contracts.annexes.showAll", { count: total })}
          </Button>
        ) : null}
      </div>
    </div>
  )
}
