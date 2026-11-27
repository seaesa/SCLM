"use client"

import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form"

import type { Role } from "@workspace/api-client"
import { ROLES } from "@workspace/core/users"
import { translateMessage, useTranslation } from "@workspace/i18n"

import { Checkbox } from "@/components/ui/checkbox"
import {
  Field,
  FieldContent,
  FieldError,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field"

interface RolesFieldProps<T extends FieldValues> {
  control: Control<T>
  name: FieldPath<T>
}

/** Every business role as a checkbox; a user holds the union of what their roles allow. */
export function RolesField<T extends FieldValues>({ control, name }: RolesFieldProps<T>) {
  const { t } = useTranslation()
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => {
        const roles: Role[] = Array.isArray(field.value) ? field.value : []
        return (
          <FieldSet data-invalid={fieldState.invalid}>
            <FieldLegend variant="label">{t("users.roles")}</FieldLegend>
            <div className="grid gap-3 sm:grid-cols-3">
              {ROLES.map((role) => (
                <Field key={role} orientation="horizontal">
                  <Checkbox
                    id={`role-${role}`}
                    checked={roles.includes(role)}
                    onCheckedChange={(checked) =>
                      field.onChange(
                        checked ? [...roles, role] : roles.filter((held) => held !== role)
                      )
                    }
                  />
                  <FieldContent>
                    <FieldLabel htmlFor={`role-${role}`}>{t(`roles.${role}`)}</FieldLabel>
                  </FieldContent>
                </Field>
              ))}
            </div>
            <FieldError>{translateMessage(fieldState.error?.message)}</FieldError>
          </FieldSet>
        )
      }}
    />
  )
}
