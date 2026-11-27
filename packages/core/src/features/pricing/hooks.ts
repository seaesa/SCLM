import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { ListFuelPricesData } from "@workspace/api-client"
import {
  correctPriceLineMutation,
  createFuelClauseMutation,
  createFuelPriceMutation,
  createPriceLinesMutation,
  createPriceTableMutation,
  deleteFuelPriceMutation,
  syncFuelPricesMutation,
  getContractPricingOptions,
  getContractPricingQueryKey,
  getFuelAdjustmentOptions,
  getFuelAdjustmentQueryKey,
  listFuelPricesOptions,
  listFuelPricesQueryKey,
  withdrawFuelClauseMutation,
  withdrawPriceLineMutation,
  withdrawPriceTableMutation,
} from "@workspace/api-client/query"

export type FuelPriceFilters = NonNullable<ListFuelPricesData["query"]>
export function useContractPricing(contractId: string, { enabled = true } = {}) {
  return useQuery({ ...getContractPricingOptions({ path: { contractId } }), enabled })
}

export function useFuelAdjustment(contractId: string, on: string | undefined) {
  return useQuery({
    ...getFuelAdjustmentOptions({ path: { contractId }, query: { on: on ?? "" } }),
    enabled: on !== undefined,
  })
}

function prefix(key: readonly [{ _id: string }]) {
  return [{ _id: key[0]._id }]
}

/** A price or fuel change alters the contract's pricing, and its fuel proposal. */
function usePricingChange<T>(contractId: string, mutation: T) {
  const queryClient = useQueryClient()
  return {
    ...mutation,
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({
          queryKey: getContractPricingQueryKey({ path: { contractId } }),
        }),
        queryClient.invalidateQueries({
          queryKey: prefix(getFuelAdjustmentQueryKey({ path: { contractId }, query: { on: "" } })),
        }),
      ]),
  }
}

export function useCreatePriceTable(contractId: string) {
  return useMutation(usePricingChange(contractId, createPriceTableMutation()))
}

export function useWithdrawPriceTable(contractId: string) {
  return useMutation(usePricingChange(contractId, withdrawPriceTableMutation()))
}

export function useCreatePriceLines(contractId: string) {
  return useMutation(usePricingChange(contractId, createPriceLinesMutation()))
}

export function useCorrectPriceLine(contractId: string) {
  return useMutation(usePricingChange(contractId, correctPriceLineMutation()))
}

export function useWithdrawPriceLine(contractId: string) {
  return useMutation(usePricingChange(contractId, withdrawPriceLineMutation()))
}

export function useCreateFuelClause(contractId: string) {
  return useMutation(usePricingChange(contractId, createFuelClauseMutation()))
}

export function useWithdrawFuelClause(contractId: string) {
  return useMutation(usePricingChange(contractId, withdrawFuelClauseMutation()))
}

export function useFuelPrices(filters: FuelPriceFilters = {}) {
  return useQuery({
    ...listFuelPricesOptions({ query: filters }),
    placeholderData: keepPreviousData,
  })
}

/** Entered fuel prices feed every contract's proposal: refresh the list and all proposals. */
function useFuelPriceChange<T>(mutation: T) {
  const queryClient = useQueryClient()
  return {
    ...mutation,
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: prefix(listFuelPricesQueryKey()) }),
        queryClient.invalidateQueries({
          queryKey: prefix(
            getFuelAdjustmentQueryKey({ path: { contractId: "" }, query: { on: "" } })
          ),
        }),
      ]),
  }
}

export function useCreateFuelPrice() {
  return useMutation(useFuelPriceChange(createFuelPriceMutation()))
}

/** Fetch the prices Petrolimex publishes now (the server also does this every hour). */
export function useSyncFuelPrices() {
  return useMutation(useFuelPriceChange(syncFuelPricesMutation()))
}

export function useDeleteFuelPrice() {
  return useMutation(useFuelPriceChange(deleteFuelPriceMutation()))
}
