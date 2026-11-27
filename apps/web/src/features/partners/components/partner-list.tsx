"use client"

import { useRouter } from "next/navigation"
import { createContext, use, useMemo, useState } from "react"

import type { PartnerRead } from "@workspace/api-client"
import { useHasPermission } from "@workspace/core/auth"
import {
  PARTNER_ROLE_FILTERS,
  usePartnerList,
  usePartnerOwnerCandidates,
  type PartnerOwnerFilter,
} from "@workspace/core/partners"
import { useTranslation } from "@workspace/i18n"

import { ChoiceSelect } from "@/components/design-system/choice-select"
import { type DataColumn } from "@/components/design-system/data-table/data-table"
import { PagedTable } from "@/components/design-system/data-table/paged-table"
import { FilterTabs } from "@/components/design-system/list-states"
import { PageBody, PageHeader } from "@/components/design-system/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"

import { AssignOwnerDialog } from "./assign-owner-dialog"

interface Selection {
  ids: ReadonlySet<string>
  toggle: (id: string) => void
}

// The checkbox cells are module-level components; they read the selection from here.
const SelectionContext = createContext<Selection | null>(null)

function SelectCell({ partner }: { partner: PartnerRead }) {
  const { t } = useTranslation()
  const selection = use(SelectionContext)
  if (!selection) return null
  return (
    // The row opens the partner; ticking the box must not.
    // oxlint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- the checkbox inside handles the keyboard
    <div onClick={(event) => event.stopPropagation()}>
      <Checkbox
        checked={selection.ids.has(partner.id)}
        onCheckedChange={() => selection.toggle(partner.id)}
        aria-label={t("partners.owner.select")}
      />
    </div>
  )
}

const SELECT_COLUMN: DataColumn<PartnerRead> = {
  id: "select",
  label: "partners.owner.select",
  enableSorting: false,
  enableHiding: false,
  cell: ({ row }) => <SelectCell partner={row.original} />,
}

const COLUMNS: DataColumn<PartnerRead>[] = [
  {
    id: "code",
    label: "partners.fields.code",
    accessorKey: "code",
    cell: ({ row }) => <span className="font-mono text-xs">{row.original.code}</span>,
  },
  {
    id: "name",
    label: "partners.fields.name",
    accessorKey: "name",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
  },
  {
    id: "taxCode",
    label: "partners.fields.taxCode",
    accessorFn: (row) => row.taxCode ?? "",
    cell: ({ row }) => row.original.taxCode ?? "—",
  },
  {
    id: "roles",
    label: "partners.fields.roles",
    enableSorting: false,
    cell: ({ row }) => <PartnerRoleBadges partner={row.original} />,
  },
  {
    id: "owner",
    label: "partners.owner.column",
    accessorFn: (row) => row.owner?.name ?? "",
    cell: ({ row }) => row.original.owner?.name ?? "—",
  },
  {
    id: "phone",
    label: "partners.fields.phone",
    accessorFn: (row) => row.phone ?? "",
    cell: ({ row }) => row.original.phone ?? "—",
  },
]

const ANY_OWNER = "__any_owner__"
const NO_OWNER = "__no_owner__"

function ownerKey(owner: PartnerOwnerFilter) {
  if (owner.kind === "owner") return owner.id
  return owner.kind === "none" ? NO_OWNER : ANY_OWNER
}

function ownerFilter(key: string | undefined): PartnerOwnerFilter {
  if (key === undefined || key === ANY_OWNER) return { kind: "any" }
  return key === NO_OWNER ? { kind: "none" } : { kind: "owner", id: key }
}

export function PartnerList() {
  const { t } = useTranslation()
  const router = useRouter()
  const canAssign = useHasPermission("partners:assign")
  const accountants = usePartnerOwnerCandidates({ enabled: canAssign })
  const { query, paging, search, setSearch, role, setRole, owner, setOwner } = usePartnerList()
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
  // A context value: a new object every render would re-render every checkbox cell.
  const selection = useMemo<Selection | null>(
    () =>
      canAssign
        ? {
            ids: selected,
            toggle: (id) =>
              setSelected((current) => {
                const next = new Set(current)
                if (!next.delete(id)) next.add(id)
                return next
              }),
          }
        : null,
    [canAssign, selected]
  )
  const pageIds = (query.data?.items ?? []).map((partner) => partner.id)
  return (
    <SelectionContext value={selection}>
      <PageHeader
        title={t("partners.title")}
        actions={
          canAssign ? (
            <div className="flex items-center gap-2">
              {selected.size > 0 ? (
                <span className="text-sm text-muted-foreground">
                  {t("partners.owner.selected", { count: selected.size })}
                </span>
              ) : null}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelected(new Set([...selected, ...pageIds]))}
              >
                {t("partners.owner.selectPage")}
              </Button>
              <AssignOwnerDialog
                partnerIds={[...selected]}
                onAssigned={() => setSelected(new Set())}
              />
            </div>
          ) : null
        }
      />
      <PageBody>
        <PagedTable
          query={query}
          paging={paging}
          columns={canAssign ? [SELECT_COLUMN, ...COLUMNS] : COLUMNS}
          getRowId={(row) => row.id}
          hiddenColumns={["phone"]}
          onRowClick={(row) => router.push(`/partners/${row.id}`)}
          toolbar={
            <>
              <Input
                className="max-w-sm"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("partners.searchHint")}
                aria-label={t("list.search")}
              />
              <FilterTabs
                options={PARTNER_ROLE_FILTERS}
                value={role}
                onChange={setRole}
                label={(key) => t(`partners.roles.${key}`)}
              />
              {canAssign ? (
                <ChoiceSelect
                  label={t("partners.owner.filter")}
                  value={ownerKey(owner)}
                  onChange={(key) => setOwner(ownerFilter(key))}
                  options={[
                    { value: ANY_OWNER, label: t("partners.owner.any") },
                    { value: NO_OWNER, label: t("partners.owner.none") },
                    ...(accountants.data ?? []).map((user) => ({
                      value: user.id,
                      label: user.name,
                    })),
                  ]}
                  className="w-52"
                />
              ) : null}
            </>
          }
        />
      </PageBody>
    </SelectionContext>
  )
}

export function PartnerRoleBadges({ partner }: { partner: PartnerRead }) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap gap-1">
      {partner.isCustomer ? (
        <Badge variant="secondary">{t("partners.roles.customer")}</Badge>
      ) : null}
      {partner.isSupplier ? <Badge variant="outline">{t("partners.roles.supplier")}</Badge> : null}
      {partner.isActive ? null : <Badge variant="destructive">{t("partners.inactive")}</Badge>}
    </div>
  )
}
