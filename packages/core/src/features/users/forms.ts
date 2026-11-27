import type { UserRead } from "@workspace/api-client"

import { useApiForm } from "../../lib/form"
import { acceptLanguage } from "../../lib/locale"
import { useAdministerUser, useInviteUser } from "./hooks"
import { userAdminFormSchema, userInviteFormSchema } from "./schemas"

/** Create an account; the API emails the person a link to choose their password. */
export function useInviteUserForm({ onInvited }: { onInvited?: () => void } = {}) {
  const invite = useInviteUser()
  return useApiForm(userInviteFormSchema, {
    defaultValues: { email: "", fullName: "", roles: [] },
    submit: (body) => invite.mutateAsync({ body, headers: acceptLanguage() }),
    onSuccess: () => onInvited?.(),
  })
}

/** Change a person's name, roles or whether the account may sign in. */
export function useUserAdminForm(user: UserRead, { onSaved }: { onSaved?: () => void } = {}) {
  const administer = useAdministerUser()
  return useApiForm(userAdminFormSchema, {
    defaultValues: { fullName: user.fullName, roles: user.roles, isActive: user.isActive },
    submit: (body) => administer.mutateAsync({ path: { userId: user.id }, body }),
    onSuccess: () => onSaved?.(),
  })
}
