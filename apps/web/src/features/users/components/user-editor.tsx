"use client"

import { toast } from "sonner"

import type { UserRead } from "@workspace/api-client"
import { useCurrentUser } from "@workspace/core/auth"
import { describeApiError } from "@workspace/core/lib/form"
import { acceptLanguage } from "@workspace/core/lib/locale"
import { useSendUserPasswordEmail, useUserAdminForm } from "@workspace/core/users"
import { useTranslation } from "@workspace/i18n"

import { FormInput } from "@/components/design-system/form/form-input"
import { FormRootError } from "@/components/design-system/form/form-root-error"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"

import { RolesField } from "./roles-field"

/** Change a user's name, roles and access, inline under their row. */
export function UserEditor({ user }: { user: UserRead }) {
  const { t } = useTranslation()
  const { data: me } = useCurrentUser()
  const sendEmail = useSendUserPasswordEmail()
  const { form, onSubmit } = useUserAdminForm(user, {
    onSaved: () => toast.success(t("users.saved")),
  })
  const isActive = form.watch("isActive") ?? true
  return (
    <form onSubmit={onSubmit} className="flex max-w-3xl flex-col gap-4" noValidate>
      <FormInput control={form.control} name="fullName" label={t("users.fullName")} />
      <RolesField control={form.control} name="roles" />
      <label className="flex items-center gap-3 text-sm">
        <Switch
          checked={isActive}
          disabled={me?.id === user.id}
          onCheckedChange={(checked) => form.setValue("isActive", checked, { shouldDirty: true })}
        />
        <span>{t("users.active")}</span>
      </label>
      <FormRootError errors={form.formState.errors} />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={form.formState.isSubmitting || !form.formState.isDirty}>
          {t("users.save")}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={sendEmail.isPending}
          onClick={() =>
            sendEmail.mutate(
              { path: { userId: user.id }, headers: acceptLanguage() },
              {
                onSuccess: () => toast.success(t("users.passwordEmailSent")),
                onError: (error) => toast.error(describeApiError(error)),
              }
            )
          }
        >
          {t("users.sendPasswordEmail")}
        </Button>
      </div>
    </form>
  )
}
