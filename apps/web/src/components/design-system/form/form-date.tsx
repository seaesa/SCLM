"use client"

import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form"

import { translateMessage, useTranslation } from "@workspace/i18n"

import { DatePicker } from "@/components/design-system/date-picker"
import { Field, FieldError, FieldLabel } from "@/components/ui/field"

interface FormDateProps<T extends FieldValues> {
  control: Control<T>
  name: FieldPath<T>
  label: string
  /** Distinct per page when the same field name appears twice (two dialogs). */
  id?: string
}

/** A date field (ISO `yyyy-MM-dd`, empty string when cleared) bound to react-hook-form. */
export function FormDate<T extends FieldValues>({ control, name, label, id }: FormDateProps<T>) {
  useTranslation() // re-render error messages when the language changes
  const inputId = id ?? name
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel htmlFor={inputId}>{label}</FieldLabel>
          <DatePicker
            id={inputId}
            value={typeof field.value === "string" && field.value !== "" ? field.value : null}
            onChange={(value) => field.onChange(value ?? "")}
            aria-invalid={fieldState.invalid}
          />
          <FieldError>{translateMessage(fieldState.error?.message)}</FieldError>
        </Field>
      )}
    />
  )
}
