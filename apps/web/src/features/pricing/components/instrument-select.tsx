"use client"

import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form"

import type { InstrumentRead } from "@workspace/api-client"
import { useTranslation } from "@workspace/i18n"

import { Field, FieldLabel } from "@/components/ui/field"

export function instrumentLabel(
  instrument: Pick<InstrumentRead, "kind" | "number">,
  t: ReturnType<typeof useTranslation>["t"]
) {
  const kind = t(`contracts.instrumentKind.${instrument.kind}`)
  return instrument.number ? `${kind} ${instrument.number}` : kind
}

/** Which document of the contract the price or clause is printed in. */
export function InstrumentSelect<T extends FieldValues>({
  control,
  name,
  instruments,
}: {
  control: Control<T>
  name: FieldPath<T>
  instruments: InstrumentRead[]
}) {
  const { t } = useTranslation()
  return (
    <Field>
      <FieldLabel htmlFor={name}>{t("pricing.instrument")}</FieldLabel>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <select
            id={name}
            className="h-9 rounded-md border bg-transparent px-2 text-sm"
            {...field}
          >
            {instruments.map((instrument) => (
              <option key={instrument.id} value={instrument.id}>
                {instrumentLabel(instrument, t)}
              </option>
            ))}
          </select>
        )}
      />
    </Field>
  )
}
