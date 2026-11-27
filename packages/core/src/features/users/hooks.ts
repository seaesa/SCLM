import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import type { ListUsersData, Role } from "@workspace/api-client"
import {
  administerUserMutation,
  inviteUserMutation,
  listUsersOptions,
  listUsersQueryKey,
  sendUserPasswordEmailMutation,
} from "@workspace/api-client/query"
import { zListUsersQuery } from "@workspace/api-client/zod"

import { searchTerm, usePaging } from "../../lib/paging"

export type UserFilters = NonNullable<ListUsersData["query"]>

/** Every role, in the order the admin screen lists them. */
export const ROLES = ["accountant", "director", "admin"] as const satisfies readonly Role[]

/** User admin screen state: name or email search + role + page. */
export function useUserList() {
  const paging = usePaging()
  const [search, setSearchText] = useState("")
  const [role, setRoleFilter] = useState<Role | undefined>()
  const query = useQuery({
    ...listUsersOptions({
      query: {
        q: searchTerm(zListUsersQuery.shape.q, search),
        role,
        page: paging.page,
        pageSize: paging.pageSize,
      },
    }),
    placeholderData: keepPreviousData,
  })
  return {
    query,
    paging,
    search,
    setSearch: (text: string) => {
      setSearchText(text)
      paging.resetPage()
    },
    role,
    setRole: (next: Role | undefined) => {
      setRoleFilter(next)
      paging.resetPage()
    },
  }
}

function useUserChange<T>(mutation: T) {
  const queryClient = useQueryClient()
  return {
    ...mutation,
    onSuccess: () => {
      const [{ _id }] = listUsersQueryKey()
      return queryClient.invalidateQueries({ queryKey: [{ _id }] })
    },
  }
}

export function useInviteUser() {
  return useMutation(useUserChange(inviteUserMutation()))
}

export function useAdministerUser() {
  return useMutation(useUserChange(administerUserMutation()))
}

export function useSendUserPasswordEmail() {
  return useMutation(sendUserPasswordEmailMutation())
}
