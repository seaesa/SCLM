"use client"

import type { FieldChoice, FieldSpecRead } from "@workspace/api-client"
import { formatDate } from "@workspace/core/lib/date"
import { formatNumber } from "@workspace/core/lib/number"
import { useTranslation } from "@workspace/i18n"

/** What a choice field can hold: the API's choices, and yes/no for a boolean. */
export type ChoiceKey = FieldChoice | "true" | "false"

/** A choice as a person reads it; a bare number is a day of the month (a statement cutoff). */
export function useChoiceLabel() {
  const { t } = useTranslation()
  return (key: ChoiceKey) =>
    isDayOfMonth(key)
      ? t("contracts.choices.dayOfMonth", { day: key })
      : t(`contracts.choices.${key}`)
}

function isDayOfMonth(key: ChoiceKey): key is Extract<ChoiceKey, `${number}`> {
  return /^\d+$/.test(key)
}

/** A stored value as a person reads it: localized date or amount, translated choices. */
export function FieldValueText({ spec, value }: { spec?: FieldSpecRead; value: string }) {
  const choice = useChoiceLabel()
  // Stored values of a choice field were checked against its choices when written.
  const asChoice = (text: string) => choice(text as ChoiceKey)
  if (spec?.type === "date") return formatDate(value)
  if (spec?.type === "amount") return formatNumber(Number(value))
  if (spec?.type === "choices") return value.split(",").map(asChoice).join(", ")
  if (spec?.type === "choice" || spec?.type === "boolean") return asChoice(value)
  return value
}
