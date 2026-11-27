import { zUserAdminUpdate, zUserInvite } from "@workspace/api-client/zod"

export const userInviteFormSchema = zUserInvite

export const userAdminFormSchema = zUserAdminUpdate
