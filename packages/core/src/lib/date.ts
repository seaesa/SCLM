import { format, formatDistanceToNow, parseISO, type Locale as DateLocale } from "date-fns"
import { vi } from "date-fns/locale"

import { i18n } from "@workspace/i18n"

type DateInput = string | Date | null | undefined

const DATE_LOCALES: Record<string, DateLocale> = { vi }
/** date-fns locale of the current language, for calendars and formatting. */
export const dateLocale = () => DATE_LOCALES[i18n.language] ?? vi

const toDate = (value: Exclude<DateInput, null | undefined>) =>
  typeof value === "string" ? parseISO(value) : value

/** Localized short date by default ("P": 31/10/2026 in vi, 10/31/2026 in en). */
/** Day-first in every language: dates come from Vietnamese documents and are typed that way. */
export function formatDate(value: DateInput, pattern = "dd/MM/yyyy") {
  return value ? format(toDate(value), pattern, { locale: dateLocale() }) : ""
}

export function formatRelative(value: DateInput) {
  return value ? formatDistanceToNow(toDate(value), { addSuffix: true, locale: dateLocale() }) : ""
}

/** Today in the reader's own time zone as `yyyy-MM-dd` (toISOString would give the UTC day). */
export const todayIso = () => format(new Date(), "yyyy-MM-dd")
