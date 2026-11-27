"use client"

import { useState } from "react"
import { toast } from "sonner"

import { useInviteUserForm } from "@workspace/core/users"
import { useTranslation } from "@workspace/i18n"

import { FormInput } from "@/components/design-system/form/form-input"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { DialogFormFooter } from "@/features/pricing/components/dialog-form-parts"

import { RolesField } from "./roles-field"

/** Create an account; the person gets an email to set their own password. */
export function InviteUserDialog() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>{t("users.invite")}</DialogTrigger>
      <DialogContent>{open && <InviteForm onDone={() => setOpen(false)} />}</DialogContent>
    </Dialog>
  )
}

function InviteForm({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = useInviteUserForm({
    onInvited: () => {
      toast.success(t("users.invited"))
      onDone()
    },
  })
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t("users.invite")}</DialogTitle>
      </DialogHeader>
      <FormInput control={form.control} name="fullName" label={t("users.fullName")} />
      <FormInput control={form.control} name="email" type="email" label={t("users.email")} />
      <RolesField control={form.control} name="roles" />
      <DialogFormFooter
        errors={form.formState.errors}
        isSubmitting={form.formState.isSubmitting}
        submitLabel={t("users.invite")}
      />
    </form>
  )
}
