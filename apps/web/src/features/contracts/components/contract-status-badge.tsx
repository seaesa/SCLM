"use client"

import type { ContractStatus } from "@workspace/api-client"
import { useTranslation } from "@workspace/i18n"

import { Badge } from "@/components/ui/badge"

const STATUS_VARIANT: Record<ContractStatus, React.ComponentProps<typeof Badge>["variant"]> = {
  draft: "secondary",
  undetermined: "destructive",
  not_yet_effective: "outline",
  active: "default",
  auto_renewed: "default",
  expired: "outline",
  replaced: "outline",
  terminated: "outline",
}

export function ContractStatusBadge({ status }: { status: ContractStatus }) {
  const { t } = useTranslation()
  return (
    <Badge variant={STATUS_VARIANT[status]}>
      {t(`contracts.status.${status === "auto_renewed" ? "active" : status}`)}
    </Badge>
  )
}
