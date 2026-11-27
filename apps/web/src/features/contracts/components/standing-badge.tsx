"use client"

import type { Standing } from "@workspace/api-client"
import { useTranslation } from "@workspace/i18n"

import { Badge } from "@/components/ui/badge"

const VARIANT: Record<Standing, "default" | "secondary" | "outline"> = {
  applying: "default",
  in_force: "secondary",
  pending: "outline",
  superseded: "outline",
  lapsed: "outline",
  revoked: "outline",
}

/** Where an annex stands today: what still applies is solid, what no longer does is muted. */
export function StandingBadge({
  standing,
  replacedByCode,
}: {
  standing: Standing | null
  replacedByCode: string | null
}) {
  const { t } = useTranslation()
  if (!standing) return null
  const isPast = standing === "superseded" || standing === "lapsed" || standing === "revoked"
  return (
    <Badge variant={VARIANT[standing]} className={isPast ? "text-muted-foreground" : undefined}>
      {t(`contracts.annexes.standing.${standing}`, { code: replacedByCode ?? "—" })}
    </Badge>
  )
}
