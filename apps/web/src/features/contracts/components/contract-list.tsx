"use client"

import type { ContractSort } from "@workspace/api-client"
import { useCurrentUser, useHasPermission } from "@workspace/core/auth"
import {
  countAdvancedFilters,
  EMPTY_ADVANCED_FILTERS,
  useContractList,
  type ContractAdvancedFilters,
  type ContractView,
} from "@workspace/core/contracts"
import { usePartnerOwnerCandidates } from "@workspace/core/partners"
import { useTranslation } from "@workspace/i18n"

import {
  ChoiceFilter,
  MultiChoiceFilter,
  DateRangeFilter,
} from "@/components/design-system/facet-filter"
import { ListStates } from "@/components/design-system/list-states"
import { PageBody, PageHeader } from "@/components/design-system/page-header"
import { ListPagination } from "@/components/design-system/pagination"
import { SortMenu } from "@/components/design-system/sort-menu"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

import {
  CONTRACT_CATEGORIES,
  CONTRACT_VIEWS,
  isContractView,
  LIFECYCLES,
  PAYMENT_FILTERS,
  RENEWAL_FILTERS,
  STATEMENT_FILTERS,
} from "../constants"
import { ContractTable } from "./contract-table"
import { NewContractDialog } from "./new-contract-dialog"

// Shortcuts on the end and notice date filters: what is coming up soon.
const NEXT_DAYS = [7, 30, 60, 90] as const
const SORTS = ["newest", "end_on", "notice_on", "code"] as const satisfies readonly ContractSort[]

/** The contract table with its views, filters and sort. */
export function ContractList({ initialView }: { initialView: ContractView }) {
  const { t } = useTranslation()
  return (
    <>
      <PageHeader title={t("contracts.title")} actions={<NewContractDialog />} />
      <PageBody>
        <ContractsView initialView={initialView} />
      </PageBody>
    </>
  )
}

function ContractsView({ initialView }: { initialView: ContractView }) {
  const { t } = useTranslation()
  const { data: user } = useCurrentUser()
  const list = useContractList(initialView, user?.id)
  const { query, advanced } = list
  // Other accountants by name for those who assign them; everyone can pick "mine" or "nobody".
  const canSeeOwners = useHasPermission("partners:assign")
  const { data: candidates = [] } = usePartnerOwnerCandidates({ enabled: canSeeOwners })
  const ownerOptions = [
    { value: "mine", label: t("contracts.owners.mine") },
    { value: "none", label: t("contracts.owners.none") },
    ...candidates
      .filter((candidate) => candidate.id !== user?.id)
      .map((candidate) => ({ value: candidate.id, label: candidate.name })),
  ]
  const set = (patch: Partial<ContractAdvancedFilters>) =>
    list.setAdvanced({ ...advanced, ...patch })
  const filtered = countAdvancedFilters(advanced) > 0
  const toolbar = (
    <div className="flex min-w-0 flex-1 flex-col gap-2">
      <div className="flex items-center gap-2">
        <Input
          type="search"
          value={list.search}
          onChange={(event) => list.setSearch(event.target.value)}
          placeholder={t("contracts.searchPlaceholder")}
          aria-label={t("contracts.searchPlaceholder")}
          className="h-8 w-full sm:w-64"
        />
        <div className="ml-auto">
          <SortMenu
            value={list.sort}
            onChange={list.setSort}
            options={SORTS.map((key) => ({ value: key, label: t(`contracts.sort.${key}`) }))}
          />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <ChoiceFilter
          label={t("contracts.columns.status")}
          value={advanced.lifecycle}
          options={LIFECYCLES.map((key) => ({
            value: key,
            label: t(`contracts.lifecycle.${key}`),
          }))}
          onChange={(lifecycle) => set({ lifecycle })}
        />
        <MultiChoiceFilter
          label={t("contracts.columns.category")}
          value={advanced.categories}
          options={CONTRACT_CATEGORIES.map((key) => ({
            value: key,
            label: t(`contracts.category.${key}`),
          }))}
          onChange={(categories) => set({ categories })}
        />
        <DateRangeFilter
          label={t("contracts.dates.signed")}
          value={advanced.signed}
          onChange={(signed) => set({ signed })}
        />
        <DateRangeFilter
          label={t("contracts.dates.ends")}
          value={advanced.ends}
          onChange={(ends) => set({ ends })}
          nextDays={NEXT_DAYS}
        />
        <DateRangeFilter
          label={t("contracts.noticeOnLabel")}
          value={advanced.notice}
          onChange={(notice) => set({ notice })}
          nextDays={NEXT_DAYS}
        />
        <ChoiceFilter
          label={t("contracts.filters.renewal")}
          value={advanced.renewal}
          options={RENEWAL_FILTERS.map((key) => ({
            value: key,
            label: t(`contracts.renewalFilter.${key}`),
          }))}
          onChange={(renewal) => set({ renewal })}
        />
        <MultiChoiceFilter
          label={t("contracts.columns.payment")}
          value={advanced.payments}
          options={PAYMENT_FILTERS.map((key) => ({
            value: key,
            label: t(`contracts.paymentFilter.${key}`),
          }))}
          onChange={(payments) => set({ payments })}
        />
        <MultiChoiceFilter
          label={t("contracts.fields.statement_cutoff")}
          value={advanced.statements}
          options={STATEMENT_FILTERS.map((key) => ({
            value: key,
            label: t(`contracts.statementFilter.${key}`),
          }))}
          onChange={(statements) => set({ statements })}
        />
        <ChoiceFilter
          label={t("contracts.columns.owner")}
          value={advanced.owner}
          options={ownerOptions}
          onChange={(owner) => set({ owner })}
        />
        {filtered ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => list.setAdvanced(EMPTY_ADVANCED_FILTERS)}
          >
            {t("filters.resetAll")}
          </Button>
        ) : null}
      </div>
    </div>
  )
  return (
    <>
      <Tabs value={list.view} onValueChange={(view) => isContractView(view) && list.setView(view)}>
        <TabsList variant="line" className="w-full justify-start overflow-x-auto border-b">
          {CONTRACT_VIEWS.map((view) => (
            <TabsTrigger key={view} value={view} className="flex-none">
              {t(`contracts.views.${view}`)}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <ListStates
        isPending={query.isPending}
        isError={query.isError}
        isEmpty={false}
        onRetry={() => void query.refetch()}
      >
        <ContractTable
          contracts={query.data?.items ?? []}
          toolbar={toolbar}
          footer={
            <ListPagination
              total={query.data?.total ?? 0}
              paging={list.paging}
              emptyText={t("contracts.empty")}
            />
          }
        />
      </ListStates>
    </>
  )
}
