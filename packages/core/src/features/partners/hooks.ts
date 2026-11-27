import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import type { ListPartnersData } from "@workspace/api-client"
import {
  assignPartnerOwnerMutation,
  getPartnerOptions,
  listContractsQueryKey,
  listPartnerOwnerCandidatesOptions,
  listPartnersOptions,
  listPartnersQueryKey,
} from "@workspace/api-client/query"
import { zListPartnersQuery } from "@workspace/api-client/zod"

import { searchTerm, usePaging } from "../../lib/paging"

export type PartnerFilters = NonNullable<ListPartnersData["query"]>

/** Role tabs above the partner list; `key` is the i18n suffix (`partners.roles.<key>`). */
export const PARTNER_ROLE_FILTERS = [
  { key: "all", role: undefined },
  { key: "customer", role: "customer" },
  { key: "supplier", role: "supplier" },
] as const

export type PartnerRoleFilter = (typeof PARTNER_ROLE_FILTERS)[number]["key"]

export function usePartners(filters: PartnerFilters = {}, options?: { enabled?: boolean }) {
  return useQuery({
    ...listPartnersOptions({ query: filters }),
    placeholderData: keepPreviousData,
    enabled: options?.enabled,
  })
}

/** Who a partner list is narrowed to: anyone, one accountant, or nobody yet. */
export type PartnerOwnerFilter = { kind: "any" } | { kind: "owner"; id: string } | { kind: "none" }

/** Partner list screen state: search text + role tab + owner + page. */
export function usePartnerList() {
  const paging = usePaging()
  const [search, setSearchText] = useState("")
  const [role, setRoleFilter] = useState<PartnerRoleFilter>("all")
  const [owner, setOwnerFilter] = useState<PartnerOwnerFilter>({ kind: "any" })
  const query = usePartners({
    q: searchTerm(zListPartnersQuery.shape.q, search),
    role: PARTNER_ROLE_FILTERS.find((f) => f.key === role)?.role,
    ownerId: owner.kind === "owner" ? owner.id : undefined,
    isUnassigned: owner.kind === "none" ? true : undefined,
    page: paging.page,
    pageSize: paging.pageSize,
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
    setRole: (next: PartnerRoleFilter) => {
      setRoleFilter(next)
      paging.resetPage()
    },
    owner,
    setOwner: (next: PartnerOwnerFilter) => {
      setOwnerFilter(next)
      paging.resetPage()
    },
  }
}

/** Hand partners (and so their contracts) to one accountant, or to nobody. */
export function useAssignPartnerOwner() {
  const queryClient = useQueryClient()
  return useMutation({
    ...assignPartnerOwnerMutation(),
    onSuccess: () => {
      const [{ _id: partnersId }] = listPartnersQueryKey()
      const [{ _id: contractsId }] = listContractsQueryKey()
      return Promise.all([
        queryClient.invalidateQueries({ queryKey: [{ _id: partnersId }] }),
        queryClient.invalidateQueries({ queryKey: [{ _id: contractsId }] }),
      ])
    },
  })
}

/** Matching partners for a picker: the first page of a search, nothing until two characters. */
export function usePartnerSearch(text: string, role?: PartnerFilters["role"]) {
  const q = searchTerm(zListPartnersQuery.shape.q, text)
  const query = usePartners({ q, role, pageSize: 20 }, { enabled: q !== undefined })
  return { query, hasTerm: q !== undefined }
}

export function usePartner(partnerId: string | undefined) {
  return useQuery({
    ...getPartnerOptions({ path: { partnerId: partnerId ?? "" } }),
    enabled: partnerId !== undefined,
  })
}

/** People a partner can be put in charge of: everyone who handles contracts. */
export function usePartnerOwnerCandidates(options?: { enabled?: boolean }) {
  return useQuery({ ...listPartnerOwnerCandidatesOptions(), enabled: options?.enabled })
}
