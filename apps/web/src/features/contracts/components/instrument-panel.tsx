"use client"

import { ArrowLeft01Icon, ArrowRight01Icon, UnfoldMoreIcon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useState } from "react"

import type { ContractDetail, FieldSpecRead, InstrumentRead } from "@workspace/api-client"
import { useHasPermission } from "@workspace/core/auth"
import { formatDate } from "@workspace/core/lib/date"
import { useTranslation } from "@workspace/i18n"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

import { DocumentRemoval } from "./document-removal"
import { FactRow } from "./fact-row"
import { InstrumentWorkflow } from "./instrument-workflow"
import { StandingBadge } from "./standing-badge"

interface InstrumentPanelProps {
  contract: ContractDetail
  instrument: InstrumentRead
  specs: FieldSpecRead[]
  onSelect: (instrumentId: string) => void
}

/** One document at a time: pick it, read its scan on the right, type its facts here. */
export function InstrumentPanel({ contract, instrument, specs, onSelect }: InstrumentPanelProps) {
  const { t } = useTranslation()
  const canEdit = useHasPermission("contracts:register")
  const documents = contract.instruments
  const index = documents.findIndex((document) => document.id === instrument.id)
  const values = new Map(instrument.values.map((value) => [value.key, value.value]))
  const ownSpecs = specs.filter(
    (spec) => spec.instrument === instrument.kind && isShown(spec.key, values, instrument)
  )
  // An annex can replace or annul other annexes of the contract, named by their codes.
  const annexCodes = documents
    .filter((d) => d.kind !== "contract" && d.id !== instrument.id && d.code)
    .map((d) => d.code as string)
  const step = (by: number) => {
    const next = documents[index + by]
    if (next) onSelect(next.id)
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center gap-1">
        <DocumentPicker documents={documents} current={instrument} onSelect={onSelect} />
        <Button
          variant="outline"
          size="icon-sm"
          aria-label={t("contracts.panel.previous")}
          disabled={index <= 0}
          onClick={() => step(-1)}
        >
          <HugeiconsIcon icon={ArrowLeft01Icon} />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          aria-label={t("contracts.panel.next")}
          disabled={index >= documents.length - 1}
          onClick={() => step(1)}
        >
          <HugeiconsIcon icon={ArrowRight01Icon} />
        </Button>
        <span className="ml-1 text-xs whitespace-nowrap text-muted-foreground tabular-nums">
          {index + 1}/{documents.length}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{t(`contracts.instrumentKind.${instrument.kind}`)}</Badge>
        {instrument.missing.length > 0 ? (
          <Badge variant="destructive">
            {t("contracts.missingFacts", { count: instrument.missing.length })}
          </Badge>
        ) : null}
        <StandingBadge standing={instrument.standing} replacedByCode={instrument.replacedByCode} />
        {canEdit ? (
          <div className="ml-auto">
            <DocumentRemoval
              contractId={contract.id}
              instrument={instrument}
              onRemoved={onSelect}
              next={documents.find((d) => d.id !== instrument.id)?.id}
            />
          </div>
        ) : null}
      </div>
      <div className="rounded-xl border px-2">
        {ownSpecs.map((spec) => (
          <FactRow
            key={spec.key}
            contractId={contract.id}
            instrumentId={instrument.id}
            spec={spec}
            value={values.get(spec.key) ?? null}
            canEdit={canEdit}
            codes={spec.key === "revokes" || spec.key === "replaces" ? annexCodes : undefined}
            isMissing={instrument.missing.includes(spec.key)}
            businessDays={
              spec.key === "payment_days"
                ? (values.get("payment_business_days") ?? null)
                : undefined
            }
          />
        ))}
      </div>
      <InstrumentWorkflow
        contractId={contract.id}
        instrument={instrument}
        events={contract.events}
        dossierId={contract.dossierId}
      />
    </section>
  )
}

interface DocumentPickerProps {
  documents: InstrumentRead[]
  current: InstrumentRead
  onSelect: (instrumentId: string) => void
}

function DocumentPicker({ documents, current, onSelect }: DocumentPickerProps) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger
        render={<Button variant="outline" className="min-w-0 flex-1 justify-between font-mono" />}
      >
        <span className="truncate">
          {documentTitle(current, t(`contracts.instrumentKind.${current.kind}`))}
        </span>
        <HugeiconsIcon icon={UnfoldMoreIcon} data-icon="inline-end" />
      </PopoverTrigger>
      <PopoverContent className="w-(--anchor-width) min-w-80 p-0" align="start">
        <Command>
          <CommandInput placeholder={t("contracts.panel.search")} />
          <CommandList>
            <CommandEmpty>{t("contracts.panel.none")}</CommandEmpty>
            {PICKER_GROUPS.map((group) => {
              const members = documents.filter((document) => pickerGroup(document) === group)
              if (members.length === 0) return null
              return (
                <CommandGroup key={group} heading={t(`contracts.panel.groups.${group}`)}>
                  {members.map((document) => (
                    <CommandItem
                      key={document.id}
                      value={`${document.code ?? ""} ${document.number ?? ""} ${document.summary ?? ""}`}
                      data-checked={document.id === current.id}
                      onSelect={() => {
                        onSelect(document.id)
                        setIsOpen(false)
                      }}
                    >
                      <div className="flex min-w-0 flex-1 flex-col">
                        <span className="font-mono text-[13px]">
                          {documentTitle(document, t(`contracts.instrumentKind.${document.kind}`))}
                        </span>
                        <span className="truncate text-xs text-muted-foreground">
                          {t(`contracts.instrumentKind.${document.kind}`)}
                          {document.effectiveFrom ? ` · ${formatDate(document.effectiveFrom)}` : ""}
                          {document.number
                            ? ` · ${t("contracts.panel.printed", { number: document.number })}`
                            : ""}
                        </span>
                      </div>
                      <StandingBadge standing={document.standing} replacedByCode={null} />
                      {document.missing.length > 0 ? (
                        <Badge variant="destructive">{document.missing.length}</Badge>
                      ) : null}
                    </CommandItem>
                  ))}
                </CommandGroup>
              )
            })}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

const PICKER_GROUPS = ["contract", "current", "past", "termination"] as const
type PickerGroup = (typeof PICKER_GROUPS)[number]
const PAST: ReadonlySet<string> = new Set(["superseded", "lapsed", "revoked"])

/** Where a document sits in the picker: what governs now apart from what no longer does. */
function pickerGroup(document: InstrumentRead): PickerGroup {
  if (document.kind === "contract" || document.kind === "termination") return document.kind
  return document.standing && PAST.has(document.standing) ? "past" : "current"
}

function documentTitle(document: InstrumentRead, kindLabel: string) {
  return document.code ?? kindLabel
}

/** A field that only matters with another one is shown when that one calls for it, or when it
 * already holds a value. */
function isShown(
  key: string,
  values: Map<string, string | null>,
  instrument: InstrumentRead
): boolean {
  // Picked next to the credit term, in the same row.
  if (key === "payment_business_days") return false
  if (values.get(key)) return true
  switch (key) {
    case "renewal_months":
    case "renewal_notice_days":
      return values.get("renewal") === "automatic"
    case "extends_to":
      return instrument.adjustments.includes("term")
    case "revokes":
      return instrument.adjustments.includes("revoke")
    // How the credit is counted only matters once it is known.
    case "payment_from":
      return Boolean(values.get("payment_days"))
    default:
      return true
  }
}
