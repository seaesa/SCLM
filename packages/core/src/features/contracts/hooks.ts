import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import type {
  ContractCategory,
  PaymentFilter,
  StatementFilter,
  RenewalFilter,
  ContractSort,
  Lifecycle,
  ListContractInstrumentsData,
  ListContractsData,
} from "@workspace/api-client"
import {
  addContractInstrumentMutation,
  approveContractInstrumentMutation,
  createContractMutation,
  deleteContractInstrumentMutation,
  deleteContractMutation,
  getDocumentSetQueryKey,
  getContractOptions,
  getContractQueryKey,
  listContractFieldsOptions,
  listContractInstrumentsOptions,
  listContractInstrumentsQueryKey,
  listContractsOptions,
  listContractsQueryKey,
  rejectContractInstrumentMutation,
  removeContractFileMutation,
  setContractInstrumentSigningMutation,
  submitContractInstrumentMutation,
  writeContractFactsMutation,
} from "@workspace/api-client/query"
import { zListContractsQuery } from "@workspace/api-client/zod"

import { searchTerm, usePaging } from "../../lib/paging"

export type ContractFilters = NonNullable<ListContractsData["query"]>
export type InstrumentFilters = NonNullable<ListContractInstrumentsData["query"]>

/** Field definitions rarely change; keep them for the session. */
const FIELD_SPECS_STALE_MS = Number.POSITIVE_INFINITY

export function useContracts(filters: ContractFilters = {}, options?: { enabled?: boolean }) {
  return useQuery({
    ...listContractsOptions({ query: filters }),
    placeholderData: keepPreviousData,
    enabled: options?.enabled,
  })
}

/** Quick views over the contract table: each is one question people ask every day. */
export type ContractView = "all" | "awaiting_approval" | "awaiting_signature" | "incomplete"

/** Whose partners: the signed-in accountant's, nobody's yet, or a given user's id. */
export type ContractOwnerFilter = "mine" | "none" | (string & {})

/** ISO dates, both ends inclusive; either may be open. */
export interface DateRange {
  from?: string
  to?: string
}

/** Filters that narrow any view; shown together in the advanced panel. */
export interface ContractAdvancedFilters {
  lifecycle?: Lifecycle
  /** Any of these; empty means every category. */
  categories: ContractCategory[]
  signed: DateRange
  ends: DateRange
  notice: DateRange
  renewal?: RenewalFilter
  owner?: ContractOwnerFilter
  /** Any of these credit-term buckets. */
  payments: PaymentFilter[]
  /** Any of these statement cut-offs. */
  statements: StatementFilter[]
}

export const EMPTY_ADVANCED_FILTERS: ContractAdvancedFilters = {
  categories: [],
  signed: {},
  ends: {},
  notice: {},
  payments: [],
  statements: [],
}

/** How many filters narrow the list. */
export function countAdvancedFilters(filters: ContractAdvancedFilters): number {
  return [
    filters.lifecycle,
    filters.categories.length > 0 ? filters.categories : undefined,
    filters.signed.from,
    filters.signed.to,
    filters.ends.from,
    filters.ends.to,
    filters.notice.from,
    filters.notice.to,
    filters.renewal,
    filters.owner,
    filters.payments.length > 0 ? filters.payments : undefined,
    filters.statements.length > 0 ? filters.statements : undefined,
  ].filter((value) => value !== undefined).length
}

function ownerIdOf(owner: ContractOwnerFilter | undefined, currentUserId: string | undefined) {
  if (owner === "mine") return currentUserId
  return owner === "none" ? null : owner
}

/** The contract table's view, filters, sort and page; changing any of them returns to page 1. */
export function useContractList(initialView: ContractView, currentUserId: string | undefined) {
  const paging = usePaging()
  const [view, setViewState] = useState(initialView)
  const [advanced, setAdvancedState] = useState(EMPTY_ADVANCED_FILTERS)
  const [search, setSearchText] = useState("")
  const [sort, setSortState] = useState<ContractSort>("newest")
  const owner = advanced.owner
  const query = useContracts({
    q: searchTerm(zListContractsQuery.shape.q, search),
    lifecycle: advanced.lifecycle,
    categories: advanced.categories.length > 0 ? advanced.categories : undefined,
    signedFrom: advanced.signed.from,
    signedTo: advanced.signed.to,
    endFrom: advanced.ends.from,
    endTo: advanced.ends.to,
    noticeFrom: advanced.notice.from,
    noticeTo: advanced.notice.to,
    renewal: advanced.renewal,
    payments: advanced.payments.length > 0 ? advanced.payments : undefined,
    statements: advanced.statements.length > 0 ? advanced.statements : undefined,
    isAwaitingApproval: view === "awaiting_approval" ? true : undefined,
    isAwaitingSignature: view === "awaiting_signature" ? true : undefined,
    isIncomplete: view === "incomplete" ? true : undefined,
    ownerId: ownerIdOf(owner, currentUserId) ?? undefined,
    isUnassigned: owner === "none" ? true : undefined,
    sort,
    page: paging.page,
    pageSize: paging.pageSize,
  })
  const resetting =
    <T>(set: (value: T) => void) =>
    (value: T) => {
      set(value)
      paging.resetPage()
    }
  return {
    query,
    paging,
    view,
    setView: resetting(setViewState),
    advanced,
    setAdvanced: resetting(setAdvancedState),
    search,
    setSearch: resetting(setSearchText),
    sort,
    setSort: resetting(setSortState),
  }
}

export function useInstruments(filters: InstrumentFilters, options?: { enabled?: boolean }) {
  return useQuery({
    ...listContractInstrumentsOptions({ query: filters }),
    placeholderData: keepPreviousData,
    enabled: options?.enabled,
  })
}

export function useContract(contractId: string) {
  return useQuery(getContractOptions({ path: { contractId } }))
}

export function useContractFields() {
  return useQuery({ ...listContractFieldsOptions(), staleTime: FIELD_SPECS_STALE_MS })
}

export function useCreateContract() {
  const queryClient = useQueryClient()
  return useMutation({
    ...createContractMutation(),
    onSuccess: () => {
      const [{ _id }] = listContractsQueryKey()
      return queryClient.invalidateQueries({ queryKey: [{ _id }] })
    },
  })
}

/** Every change to a contract returns or affects its detail: refresh it (and the lists). */
function useContractChange<T>(contractId: string, mutation: T) {
  const queryClient = useQueryClient()
  return {
    ...mutation,
    onSuccess: () => {
      const [{ _id }] = listContractsQueryKey()
      const [{ _id: instrumentsId }] = listContractInstrumentsQueryKey()
      return Promise.all([
        queryClient.invalidateQueries({ queryKey: getContractQueryKey({ path: { contractId } }) }),
        queryClient.invalidateQueries({ queryKey: [{ _id }] }),
        queryClient.invalidateQueries({ queryKey: [{ _id: instrumentsId }] }),
      ])
    },
  }
}

export function useAddContractInstrument(contractId: string) {
  return useMutation(useContractChange(contractId, addContractInstrumentMutation()))
}

export function useWriteContractFacts(contractId: string) {
  return useMutation(useContractChange(contractId, writeContractFactsMutation()))
}

/** Approval and signing are per document: the contract itself or one of its addenda. */
export function useSubmitInstrument(contractId: string) {
  return useMutation(useContractChange(contractId, submitContractInstrumentMutation()))
}

export function useApproveInstrument(contractId: string) {
  return useMutation(useContractChange(contractId, approveContractInstrumentMutation()))
}

export function useRejectInstrument(contractId: string) {
  return useMutation(useContractChange(contractId, rejectContractInstrumentMutation()))
}

export function useSetInstrumentSigning(contractId: string) {
  return useMutation(useContractChange(contractId, setContractInstrumentSigningMutation()))
}

/** A document entered by mistake: deleted while it is a draft, cancelled once it counts. */
export function useDeleteInstrument(contractId: string) {
  return useMutation(useContractChange(contractId, deleteContractInstrumentMutation()))
}

/** Unlink a file no document uses from the contract's files. */
export function useRemoveContractFile(contractId: string, dossierId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    ...removeContractFileMutation(),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: getDocumentSetQueryKey({ path: { setId: dossierId } }),
      }),
  })
}

/** Starts the contract that replaces this one; the old one ends when the new one starts. */
export function useDeleteContract() {
  const queryClient = useQueryClient()
  return useMutation({
    ...deleteContractMutation(),
    onSuccess: () => {
      const [{ _id }] = listContractsQueryKey()
      return queryClient.invalidateQueries({ queryKey: [{ _id }] })
    },
  })
}
