"use client"

import type { PartnerRead } from "@workspace/api-client"
import { useTranslation } from "@workspace/i18n"

const INFO_FIELDS = ["code", "legalName", "taxCode", "address", "email", "phone"] as const

/** What the source of record (MISA) says about a partner. */
export function PartnerInfo({ partner }: { partner: PartnerRead }) {
  const { t } = useTranslation()
  return (
    <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
      {INFO_FIELDS.map((field) => (
        <div key={field} className="flex min-w-0 flex-col">
          <dt className="text-xs text-muted-foreground">{t(`partners.fields.${field}`)}</dt>
          <dd className="break-words">{partner[field] ?? "—"}</dd>
        </div>
      ))}
    </dl>
  )
}
