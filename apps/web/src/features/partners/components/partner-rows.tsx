"use client"

import type { PartnerRead } from "@workspace/api-client"
import { useTranslation } from "@workspace/i18n"

import { Badge } from "@/components/ui/badge"

/** Code, name, tax code and role badges of a partner, for list rows. */
export function PartnerSummaryLine({ partner }: { partner: PartnerRead }) {
  const { t } = useTranslation()
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
      <span className="font-mono text-sm text-muted-foreground">{partner.code}</span>
      <span className="truncate font-medium">{partner.name}</span>
      {partner.taxCode && <span className="text-sm text-muted-foreground">{partner.taxCode}</span>}
      {partner.isCustomer && <Badge variant="secondary">{t("partners.roles.customer")}</Badge>}
      {partner.isSupplier && <Badge variant="secondary">{t("partners.roles.supplier")}</Badge>}
      {!partner.isActive && <Badge variant="outline">{t("partners.inactive")}</Badge>}
    </div>
  )
}
