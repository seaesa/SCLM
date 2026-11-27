"use client"

import type { ReviewState, SigningState } from "@workspace/api-client"
import { useTranslation } from "@workspace/i18n"

import { Badge } from "@/components/ui/badge"

/** Where a document stands: its approval (only for documents Spider drafted) and its signing. */
export function InstrumentStateBadges({
  reviewState,
  signingState,
}: {
  reviewState: ReviewState | null
  signingState: SigningState
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap gap-1.5">
      {reviewState ? (
        <Badge variant={reviewState === "rejected" ? "destructive" : "outline"}>
          {t(`contracts.review.state.${reviewState}`)}
        </Badge>
      ) : null}
      <Badge variant={signingState === "signed" ? "secondary" : "outline"}>
        {t(`contracts.signing.state.${signingState}`)}
      </Badge>
    </div>
  )
}
