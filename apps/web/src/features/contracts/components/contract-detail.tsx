"use client"

import { differenceInCalendarDays, parseISO } from "date-fns"
import Link from "next/link"
import { useState } from "react"

import type { ContractDetail as ContractDetailRead } from "@workspace/api-client"
import { useHasPermission } from "@workspace/core/auth"
import { useContract, useContractFields } from "@workspace/core/contracts"
import { useDocumentSet } from "@workspace/core/documents"
import { formatDate, todayIso } from "@workspace/core/lib/date"
import { usePartner } from "@workspace/core/partners"
import { useTranslation } from "@workspace/i18n"

import { PageBody, PageHeader } from "@/components/design-system/page-header"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DocumentFileViewer } from "@/features/documents/components/document-file-viewer"
import { PartnerInfo } from "@/features/partners/components/partner-info"
import { PricingPanel, useCanSeePrices } from "@/features/pricing/components/pricing-panel"
import { cn } from "@/lib/utils"

import { AddInstrumentDialog } from "./add-instrument-dialog"
import { ContractHistory } from "./contract-history"
import { ContractStatusBadge } from "./contract-status-badge"
import { DeleteContractButton } from "./delete-contract-button"
import { InstrumentPanel } from "./instrument-panel"
import { MissingFactsBadge } from "./missing-facts-badge"
import { NewContractDialog } from "./new-contract-dialog"

export function ContractDetail({
  contractId,
  initialDocumentId,
}: {
  contractId: string
  initialDocumentId?: string
}) {
  const { t } = useTranslation()
  const { data: contract, isPending } = useContract(contractId)
  const { data: specs = [] } = useContractFields()
  const { data: dossier } = useDocumentSet(contract?.dossierId ?? "")
  const canRegister = useHasPermission("contracts:register")
  const [selectedId, setSelectedId] = useState(initialDocumentId)
  const canSeePrices = useCanSeePrices(contract)

  if (isPending || !contract) {
    return (
      <PageBody>
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-64 w-full" />
      </PageBody>
    )
  }
  const documents = contract.instruments
  const selected =
    documents.find((document) => document.id === selectedId) ??
    documents.find((document) => document.kind === "contract") ??
    documents[0]
  const fileId = selected?.fileId ?? dossier?.files[0]?.id
  const file = dossier?.files.find((f) => f.id === fileId)
  const selectByFile = (id: string) => {
    const document = documents.find((d) => d.fileId === id)
    if (document) setSelectedId(document.id)
  }

  return (
    <>
      <PageHeader
        parents={[{ href: "/contracts", label: t("nav.contracts") }]}
        title={contract.code ?? contract.number ?? contract.partner.name}
        description={
          <Link href={`/partners/${contract.partner.id}`} className="hover:underline">
            {contract.partner.code} · {contract.partner.name}
          </Link>
        }
        meta={
          <>
            <ContractStatusBadge status={contract.status} />
            <Badge variant="outline">{t(`contracts.category.${contract.category}`)}</Badge>
            <ContractTerm contract={contract} documentCount={documents.length} />
            <ContractLinks contract={contract} />
            <ApplyingDocuments contract={contract} onSelect={setSelectedId} />
          </>
        }
        actions={
          canRegister ? (
            <>
              {contract.canDelete ? <DeleteContractButton contractId={contract.id} /> : null}
              {contract.replacedById === null && contract.status !== "draft" ? (
                <NewContractDialog
                  replaces={{
                    id: contract.id,
                    category: contract.category,
                    side: contract.side,
                    partner: contract.partner,
                  }}
                />
              ) : null}
              <AddInstrumentDialog contractId={contract.id} dossierId={contract.dossierId} />
            </>
          ) : null
        }
      />
      <PageBody>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
          <Tabs defaultValue="documents" className="flex min-w-0 flex-col gap-3">
            <TabsList variant="line" className="w-full justify-start border-b">
              <TabsTrigger value="documents">{t("contracts.documentsTab")}</TabsTrigger>
              <TabsTrigger value="partner">{t("partners.title")}</TabsTrigger>
              {canSeePrices ? <TabsTrigger value="pricing">{t("pricing.tab")}</TabsTrigger> : null}
              <TabsTrigger value="history">{t("contracts.history.tab")}</TabsTrigger>
            </TabsList>
            <TabsContent value="documents">
              {selected ? (
                <InstrumentPanel
                  contract={contract}
                  instrument={selected}
                  specs={specs}
                  onSelect={setSelectedId}
                />
              ) : (
                <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                  {t("contracts.noInstruments")}
                </p>
              )}
            </TabsContent>
            <TabsContent value="partner">
              <ContractPartner partnerId={contract.partner.id} />
            </TabsContent>
            {canSeePrices ? (
              <TabsContent value="pricing">
                <PricingPanel
                  contract={contract}
                  onShowPage={(instrumentId) => setSelectedId(instrumentId)}
                />
              </TabsContent>
            ) : null}
            <TabsContent value="history">
              <ContractHistory events={contract.events} specs={specs} onShowFile={selectByFile} />
            </TabsContent>
          </Tabs>
          {fileId ? (
            <div className="xl:sticky xl:top-16 xl:h-[calc(100svh-5rem)] xl:self-start">
              <DocumentFileViewer
                setId={contract.dossierId}
                fileId={fileId}
                fileName={file?.path ?? "contract.pdf"}
                contentType={file?.contentType}
                className="h-[80vh] xl:h-full"
              />
            </div>
          ) : null}
        </div>
      </PageBody>
    </>
  )
}

/** What the system works out from all the documents together; none of it is typed here. */
/** The contract this one replaces, the one replacing it, and any it overlaps in time. */
function ContractLinks({ contract }: { contract: ContractDetailRead }) {
  const { t } = useTranslation()
  return (
    <>
      {contract.replaces ? (
        <Link href={`/contracts/${contract.replaces.id}`} className="text-sm hover:underline">
          {t("contracts.links.replaces", { code: contract.replaces.code ?? "—" })}
        </Link>
      ) : null}
      {contract.overlapping.length > 0 ? (
        <span className="flex flex-wrap items-center gap-1 text-sm font-medium text-destructive">
          {t("contracts.links.overlapping")}
          {contract.overlapping.map((other) => (
            <Link key={other.id} href={`/contracts/${other.id}`} className="underline">
              {other.code ?? "—"}
            </Link>
          ))}
        </span>
      ) : null}
    </>
  )
}

/** Where the contract stands, said the way people ask: ended, replaced, or until when. */
function ContractTerm({
  contract,
  documentCount,
}: {
  contract: ContractDetailRead
  documentCount: number
}) {
  const { t } = useTranslation()
  const left = contract.endOn
    ? differenceInCalendarDays(parseISO(contract.endOn), parseISO(todayIso()))
    : null
  const isRunning = contract.status === "active" || contract.status === "auto_renewed"
  return (
    <span className="flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground">
      <TermText contract={contract} />
      {contract.noticeOn ? (
        <span>
          · {t("contracts.noticeOnLabel")} {formatDate(contract.noticeOn)}
        </span>
      ) : null}
      <span>· {t("contracts.panel.documents", { count: documentCount })}</span>
      {isRunning && left !== null && left >= 0 ? (
        <span className={cn(left <= 30 ? "font-medium text-destructive" : "")}>
          · {t("contracts.daysLeft", { count: left })}
        </span>
      ) : null}
      <MissingFactsBadge facts={contract.missingFacts} />
    </span>
  )
}

function TermText({ contract }: { contract: ContractDetailRead }) {
  const { t } = useTranslation()
  const date = contract.endOn ? formatDate(contract.endOn) : null
  if (contract.status === "replaced" && contract.replacedBy) {
    return (
      <Link href={`/contracts/${contract.replacedBy.id}`} className="hover:underline">
        {t("contracts.term.replaced", {
          code: contract.replacedBy.code ?? "—",
          date: contract.replacedOn ? formatDate(contract.replacedOn) : "—",
        })}
      </Link>
    )
  }
  if (!date) {
    return contract.status === "active" ? <span>{t("contracts.term.noEnd")}</span> : null
  }
  const phrase =
    contract.status in TERM_PHRASES
      ? TERM_PHRASES[contract.status as keyof typeof TERM_PHRASES]
      : "contracts.term.endsOn"
  return <span>{t(phrase, { date })}</span>
}

const TERM_PHRASES = {
  auto_renewed: "contracts.term.inCycle",
  expired: "contracts.term.expired",
  terminated: "contracts.term.terminated",
  replaced: "contracts.term.expired",
} as const satisfies Partial<Record<ContractDetailRead["status"], string>>

/** The addenda behind today's prices, fuel base and end date; each opens beside its scan. */
function ApplyingDocuments({
  contract,
  onSelect,
}: {
  contract: ContractDetailRead
  onSelect: (instrumentId: string) => void
}) {
  const { t } = useTranslation()
  if (contract.applying.length === 0) return null
  return (
    <span className="flex basis-full flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <span className="text-muted-foreground">{t("contracts.annexes.applying")}:</span>
      {contract.applying.map((document) => (
        <button
          key={document.kind}
          type="button"
          className="underline-offset-4 hover:underline"
          onClick={() => onSelect(document.instrumentId)}
        >
          {t(`contracts.choices.${document.kind}`)}{" "}
          <span className="font-mono font-medium">{document.code ?? "—"}</span>
        </button>
      ))}
    </span>
  )
}

function ContractPartner({ partnerId }: { partnerId: string }) {
  const { data: partner } = usePartner(partnerId)
  return partner ? <PartnerInfo partner={partner} /> : <Skeleton className="h-32 w-full" />
}
