"use client"

import { useState } from "react"
import { toast } from "sonner"

import { useWithdrawForm } from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { FormRootError } from "@/components/design-system/form/form-root-error"
import { FormTextarea } from "@/components/design-system/form/form-textarea"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface WithdrawDialogProps {
  title: string
  /** Once the contract is published, the reason is kept with the withdrawn row. */
  needsReason: boolean
  onWithdraw: (reason: string | null) => Promise<unknown>
  trigger?: React.ReactElement
}

export function WithdrawDialog({ trigger, ...props }: WithdrawDialogProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={trigger ?? <Button size="sm" variant="ghost" />}>
        {t("pricing.withdraw")}
      </DialogTrigger>
      <DialogContent>
        {open && <WithdrawForm {...props} onDone={() => setOpen(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function WithdrawForm({
  title,
  needsReason,
  onWithdraw,
  onDone,
}: Omit<WithdrawDialogProps, "trigger"> & { onDone: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = useWithdrawForm(onWithdraw, {
    onSaved: () => {
      toast.success(t("pricing.withdrawnToast"))
      onDone()
    },
  })
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>
      {needsReason && (
        <FormTextarea control={form.control} name="reason" label={t("pricing.reason")} />
      )}
      <FormRootError errors={form.formState.errors} />
      <DialogFooter>
        <Button type="submit" variant="destructive" disabled={form.formState.isSubmitting}>
          {t("pricing.withdraw")}
        </Button>
      </DialogFooter>
    </form>
  )
}
