"use client"

import { useState } from "react"
import { toast } from "sonner"

import { describeApiError } from "@workspace/core/lib/form"
import { useAssignPartnerOwner, usePartnerOwnerCandidates } from "@workspace/core/partners"
import { useTranslation } from "@workspace/i18n"

import { ChoiceSelect } from "@/components/design-system/choice-select"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

const NOBODY = "nobody"

/** Hand the selected partners, and so their contracts, to one accountant (or to nobody). */
export function AssignOwnerDialog({
  partnerIds,
  onAssigned,
}: {
  partnerIds: string[]
  onAssigned: () => void
}) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [owner, setOwner] = useState<string>()
  const accountants = usePartnerOwnerCandidates({ enabled: isOpen })
  const assign = useAssignPartnerOwner()
  const options = [
    { value: NOBODY, label: t("partners.owner.nobody") },
    ...(accountants.data ?? []).map((user) => ({ value: user.id, label: user.name })),
  ]
  const save = () =>
    assign.mutate(
      { body: { partnerIds, ownerId: owner === NOBODY ? null : (owner ?? null) } },
      {
        onSuccess: () => {
          toast.success(t("partners.owner.saved"))
          setIsOpen(false)
          setOwner(undefined)
          onAssigned()
        },
        onError: (error) => toast.error(describeApiError(error)),
      }
    )
  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger render={<Button size="sm" disabled={partnerIds.length === 0} />}>
        {t("partners.owner.assign")}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("partners.owner.assign")}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          {t("partners.owner.selected", { count: partnerIds.length })}
        </p>
        <ChoiceSelect
          label={t("partners.owner.pick")}
          placeholder={t("partners.owner.pick")}
          value={owner}
          onChange={setOwner}
          options={options}
          className="w-full"
        />
        <DialogFooter>
          <Button onClick={save} disabled={owner === undefined || assign.isPending}>
            {t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
