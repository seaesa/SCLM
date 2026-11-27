"use client"

import { useState } from "react"
import { Controller } from "react-hook-form"
import { toast } from "sonner"

import type { InstrumentRead, Rounding } from "@workspace/api-client"
import { useFuelClauseForm } from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { FormDate } from "@/components/design-system/form/form-date"
import { FormInput } from "@/components/design-system/form/form-input"
import { FilterTabs } from "@/components/design-system/list-states"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Field, FieldLabel } from "@/components/ui/field"

import { CitationFields, DialogFormFooter } from "./dialog-form-parts"
import { InstrumentSelect } from "./instrument-select"

const ROUNDING_OPTIONS = [
  { key: "none" },
  { key: "down_100" },
  { key: "nearest_100" },
  { key: "down_1000" },
  { key: "nearest_1000" },
] as const satisfies readonly { key: Rounding }[]

const REFERENCES = [{ key: "cumulative" }, { key: "stepwise" }] as const

interface FuelClauseDialogProps {
  contractId: string
  instruments: InstrumentRead[]
}

export function FuelClauseDialog(props: FuelClauseDialogProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" variant="outline" />}>
        {t("pricing.fuel.addClause")}
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        {open && <FuelClauseForm {...props} onSaved={() => setOpen(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function FuelClauseForm({
  contractId,
  instruments,
  onSaved,
}: FuelClauseDialogProps & { onSaved: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = useFuelClauseForm(contractId, {
    instrumentId: instruments.at(-1)?.id ?? "",
    onSaved: () => {
      toast.success(t("pricing.saved"))
      onSaved()
    },
  })
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t("pricing.fuel.addClause")}</DialogTitle>
      </DialogHeader>
      <InstrumentSelect control={form.control} name="instrumentId" instruments={instruments} />
      <div className="grid grid-cols-2 gap-3">
        <FormInput
          control={form.control}
          name="fuelType"
          label={t("pricing.fuel.fuelType")}
          placeholder={t("pricing.fuel.fuelTypePlaceholder")}
        />
        <FormInput
          control={form.control}
          name="basePrice"
          inputMode="numeric"
          label={t("pricing.fuel.basePrice")}
        />
        <FormDate control={form.control} name="baseOn" label={t("pricing.fuel.baseOn")} />
        <FormInput
          control={form.control}
          name="share"
          inputMode="decimal"
          label={t("pricing.fuel.share")}
        />
        <FormInput
          control={form.control}
          name="threshold"
          inputMode="decimal"
          label={t("pricing.fuel.threshold")}
        />
        <FormInput
          control={form.control}
          name="lagDays"
          type="number"
          min={0}
          label={t("pricing.fuel.lagDays")}
        />
      </div>
      <Field>
        <FieldLabel>{t("pricing.fuel.reference")}</FieldLabel>
        <Controller
          control={form.control}
          name="isCumulative"
          render={({ field }) => (
            <FilterTabs
              options={REFERENCES}
              value={field.value ? "cumulative" : "stepwise"}
              onChange={(key) => field.onChange(key === "cumulative")}
              label={(key) => t(`pricing.fuel.${key}`)}
            />
          )}
        />
      </Field>
      <Field>
        <FieldLabel>{t("pricing.fuel.rounding")}</FieldLabel>
        <Controller
          control={form.control}
          name="rounding"
          render={({ field }) => (
            <FilterTabs
              options={ROUNDING_OPTIONS}
              value={field.value}
              onChange={field.onChange}
              label={(key) => t(`pricing.rounding.${key}`)}
            />
          )}
        />
      </Field>
      <CitationFields control={form.control} />
      <DialogFormFooter errors={form.formState.errors} isSubmitting={form.formState.isSubmitting} />
    </form>
  )
}
