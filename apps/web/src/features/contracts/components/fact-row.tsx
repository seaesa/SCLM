"use client"

import { CheckmarkCircle02Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useState, type KeyboardEvent } from "react"

import type { FieldSpecRead } from "@workspace/api-client"
import { useWriteContractFacts } from "@workspace/core/contracts"
import { describeApiError } from "@workspace/core/lib/form"
import { useTranslation } from "@workspace/i18n"

import { ChoiceSelect } from "@/components/design-system/choice-select"
import { DatePicker } from "@/components/design-system/date-picker"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

import { FieldValueText, useChoiceLabel, type ChoiceKey } from "./field-value-text"

const BOOLEAN_CHOICES: ChoiceKey[] = ["true", "false"]
const LONG_TEXT = new Set(["summary", "scope"])
interface FactRowProps {
  contractId: string
  instrumentId: string
  spec: FieldSpecRead
  value: string | null
  canEdit: boolean
  /** Codes to pick from, for a fact naming other documents. */
  codes?: string[]
  /** A key fact the document has nothing for yet. */
  isMissing: boolean
  /** For the credit term: whether its days are working days ("true"), picked in the same row. */
  businessDays?: string | null
}

/** One fact of a document, edited where it is shown and saved on its own. */
export function FactRow({
  contractId,
  instrumentId,
  spec,
  value,
  canEdit,
  codes,
  isMissing,
  businessDays,
}: FactRowProps) {
  const { t } = useTranslation()
  const write = useWriteContractFacts(contractId)
  const [isSaved, setIsSaved] = useState(false)
  const [error, setError] = useState<string>()
  const current = value ?? ""
  const id = `fact-${instrumentId}-${spec.key}`
  const label = t(`contracts.fields.${spec.key}`)

  const submit = async (values: Record<string, string>) => {
    setIsSaved(false)
    setError(undefined)
    try {
      await write.mutateAsync({ path: { instrumentId }, body: { values } })
      setIsSaved(true)
    } catch (caught) {
      setError(describeApiError(caught))
    }
  }
  const save = async (next: string) => {
    if (next !== current) await submit({ [spec.key]: next })
  }

  const isCreditTerm = spec.key === "payment_days"
  let text = value ? <FieldValueText spec={spec} value={value} /> : "—"
  if (isCreditTerm && value) {
    text = t(
      businessDays === "true" ? "contracts.payment.businessDays" : "contracts.payment.days",
      { count: Number(value) }
    )
  }
  let field = <p className="px-2 py-1.5 text-sm">{text}</p>
  if (canEdit && isCreditTerm) {
    field = (
      <CreditTermInput
        id={id}
        label={label}
        days={current}
        businessDays={businessDays === "true"}
        onSubmit={submit}
      />
    )
  } else if (canEdit) {
    field = (
      <FactInput id={id} spec={spec} label={label} value={current} onSave={save} codes={codes} />
    )
  }

  return (
    <div className="grid grid-cols-[9rem_minmax(0,1fr)] items-start gap-x-3 py-1 sm:grid-cols-[11rem_minmax(0,1fr)]">
      <label
        htmlFor={id}
        className={cn(
          "pt-2 text-sm text-muted-foreground",
          isMissing && "font-medium text-destructive"
        )}
      >
        {label}
      </label>
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex min-w-0 items-center gap-2">
          <div className="min-w-0 flex-1">{field}</div>
          {write.isPending ? <Spinner className="size-4 text-muted-foreground" /> : null}
          {isSaved && !write.isPending ? (
            <HugeiconsIcon
              icon={CheckmarkCircle02Icon}
              className="size-4 text-emerald-600"
              aria-label={t("contracts.facts.saved")}
            />
          ) : null}
        </div>
        {error ? <p className="px-2 text-xs text-destructive">{error}</p> : null}
      </div>
    </div>
  )
}

interface FactInputProps {
  id: string
  spec: FieldSpecRead
  label: string
  value: string
  onSave: (value: string) => Promise<void>
  codes?: string[]
}

function FactInput({ id, spec, label, value, onSave, codes }: FactInputProps) {
  const { t } = useTranslation()
  const choices = spec.type === "boolean" ? BOOLEAN_CHOICES : spec.choices
  const choiceLabel = useChoiceLabel()

  if (codes && spec.type === "text" && spec.key === "replaces") {
    return (
      <ChoicesSelect
        id={id}
        label={label}
        choices={codes}
        choiceLabel={(code) => code}
        value={value}
        onSave={onSave}
      />
    )
  }
  if (codes) {
    return (
      <ChoiceSelect
        label={label}
        value={value || undefined}
        onChange={(next) => void onSave(next ?? "")}
        placeholder={t("contracts.fieldDialog.choose")}
        options={codes.map((code) => ({ value: code, label: code }))}
        className="w-full"
      />
    )
  }
  if (spec.type === "date") {
    return <DatePicker id={id} value={value || null} onChange={(next) => void onSave(next ?? "")} />
  }
  if (spec.type === "choices") {
    return (
      <ChoicesSelect
        id={id}
        label={label}
        choices={choices}
        choiceLabel={choiceLabel}
        value={value}
        onSave={onSave}
      />
    )
  }
  if (choices.length > 0) {
    return (
      <ChoiceSelect
        label={label}
        // An unstated renewal clause means the contract does not renew.
        value={value || (choices.includes("none") ? "none" : undefined)}
        onChange={(next) => void onSave(next === "none" ? "" : (next ?? ""))}
        placeholder={t("contracts.fieldDialog.choose")}
        options={choices.map((key) => ({ value: key, label: choiceLabel(key) }))}
        className="w-full"
      />
    )
  }
  // Enter saves, Escape puts the stored value back; leaving the box (Tab) saves.
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (event.key === "Escape") {
      event.currentTarget.value = value
      event.currentTarget.blur()
    } else if (event.key === "Enter" && !(event.shiftKey && LONG_TEXT.has(spec.key))) {
      event.preventDefault()
      event.currentTarget.blur()
    }
  }
  if (LONG_TEXT.has(spec.key)) {
    return (
      <Textarea
        key={value}
        id={id}
        rows={2}
        defaultValue={value}
        placeholder="—"
        className="min-h-14 resize-y"
        onBlur={(event) => void onSave(event.target.value.trim())}
        onKeyDown={handleKeyDown}
      />
    )
  }
  return (
    <Input
      key={value}
      id={id}
      defaultValue={value}
      placeholder="—"
      inputMode={spec.type === "integer" || spec.type === "amount" ? "numeric" : undefined}
      onBlur={(event) => void onSave(event.target.value.trim())}
      onKeyDown={handleKeyDown}
    />
  )
}

interface CreditTermInputProps {
  id: string
  label: string
  days: string
  businessDays: boolean
  onSubmit: (values: Record<string, string>) => Promise<void>
}

/** The credit term in one row: its number of days, and whether they are calendar or working days. */
function CreditTermInput({ id, label, days, businessDays, onSubmit }: CreditTermInputProps) {
  const { t } = useTranslation()
  const unit = businessDays ? "business" : "calendar"
  const saveDays = (next: string) => {
    if (next === days) return
    // Without a number of days there is nothing to count in working days.
    void onSubmit(next ? { payment_days: next } : { payment_days: "", payment_business_days: "" })
  }
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Input
        key={days}
        id={id}
        defaultValue={days}
        placeholder="—"
        inputMode="numeric"
        className="min-w-0 flex-1"
        onBlur={(event) => saveDays(event.target.value.trim())}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.currentTarget.value = days
            event.currentTarget.blur()
          } else if (event.key === "Enter") {
            event.preventDefault()
            event.currentTarget.blur()
          }
        }}
      />
      <ChoiceSelect
        label={t("contracts.payment.unit")}
        value={unit}
        onChange={(next) =>
          void onSubmit({ payment_business_days: next === "business" ? "true" : "" })
        }
        options={[
          { value: "calendar", label: t("contracts.payment.calendarUnit") },
          { value: "business", label: t("contracts.payment.businessUnit") },
        ]}
        className={cn("w-36 shrink-0", !days && "pointer-events-none opacity-50")}
      />
      <span className="sr-only">{label}</span>
    </div>
  )
}

interface ChoicesSelectProps<K extends string> {
  id: string
  label: string
  choices: readonly K[]
  choiceLabel: (key: K) => string
  value: string
  onSave: (value: string) => Promise<void>
}

/** Several choices in one box; each tick is saved at once. */
function ChoicesSelect<K extends string>({
  id,
  label,
  choices,
  choiceLabel,
  value,
  onSave,
}: ChoicesSelectProps<K>) {
  const picked: string[] = value ? value.split(",") : []
  const toggle = (key: K, isPicked: boolean) => {
    const next = isPicked ? [...picked, key] : picked.filter((item) => item !== key)
    void onSave(choices.filter((choice) => next.includes(choice)).join(","))
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button id={id} variant="outline" aria-label={label} className="w-full justify-start" />
        }
      >
        <span className="truncate">
          {picked.length > 0
            ? choices
                .filter((choice) => picked.includes(choice))
                .map(choiceLabel)
                .join(", ")
            : "—"}
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="min-w-(--anchor-width)">
        <DropdownMenuGroup>
          {choices.map((key) => (
            <DropdownMenuCheckboxItem
              key={key}
              checked={picked.includes(key)}
              closeOnClick={false}
              onCheckedChange={(checked) => toggle(key, checked)}
            >
              {choiceLabel(key)}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
