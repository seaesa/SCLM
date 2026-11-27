"use client"

import { useState } from "react"

import type { Role, UserRead } from "@workspace/api-client"
import { formatDate } from "@workspace/core/lib/date"
import { ROLES, useUserList } from "@workspace/core/users"
import { useTranslation } from "@workspace/i18n"

import { ChoiceSelect } from "@/components/design-system/choice-select"
import { type DataColumn } from "@/components/design-system/data-table/data-table"
import { PagedTable } from "@/components/design-system/data-table/paged-table"
import { PageBody, PageHeader } from "@/components/design-system/page-header"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"

import { InviteUserDialog } from "./invite-user-dialog"
import { UserEditor } from "./user-editor"

function RoleBadges({ roles }: { roles: Role[] }) {
  const { t } = useTranslation()
  if (roles.length === 0) return <span className="text-muted-foreground">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {roles.map((role) => (
        <Badge key={role} variant="outline">
          {t(`roles.${role}`)}
        </Badge>
      ))}
    </div>
  )
}

function AccessBadge({ user }: { user: UserRead }) {
  const { t } = useTranslation()
  if (!user.isActive) return <Badge variant="destructive">{t("users.inactive")}</Badge>
  if (!user.emailVerified) return <Badge variant="outline">{t("users.invitedState")}</Badge>
  return <Badge variant="secondary">{t("users.active")}</Badge>
}

const COLUMNS: DataColumn<UserRead>[] = [
  {
    id: "name",
    label: "users.fullName",
    enableSorting: false,
    accessorKey: "fullName",
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span className="font-medium">{row.original.fullName}</span>
        <span className="text-xs text-muted-foreground">{row.original.email}</span>
      </div>
    ),
  },
  {
    id: "roles",
    label: "users.roles",
    enableSorting: false,
    accessorFn: (row) => row.roles.join(","),
    cell: ({ row }) => <RoleBadges roles={row.original.roles} />,
  },
  {
    id: "access",
    label: "users.access",
    enableSorting: false,
    accessorKey: "isActive",
    cell: ({ row }) => <AccessBadge user={row.original} />,
  },
  {
    id: "createdAt",
    label: "users.createdAt",
    enableSorting: false,
    accessorKey: "createdAt",
    cell: ({ row }) => formatDate(row.original.createdAt),
  },
]

/** Accounts and what each may do: the only place access is granted or withdrawn. */
export function UserList() {
  const { t } = useTranslation()
  const list = useUserList()
  const { query } = list
  const [editing, setEditing] = useState<UserRead>()
  return (
    <>
      <PageHeader title={t("users.title")} actions={<InviteUserDialog />} />
      <PageBody>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            type="search"
            value={list.search}
            onChange={(event) => list.setSearch(event.target.value)}
            placeholder={t("users.searchPlaceholder")}
            aria-label={t("users.searchPlaceholder")}
            className="w-full sm:w-72"
          />
          <ChoiceSelect
            label={t("users.roles")}
            value={list.role}
            onChange={list.setRole}
            options={ROLES.map((role) => ({ value: role, label: t(`roles.${role}`) }))}
            anyLabel={t("users.allRoles")}
            className="w-48"
          />
        </div>
        <PagedTable
          query={query}
          paging={list.paging}
          columns={COLUMNS}
          getRowId={(row) => row.id}
          onRowClick={setEditing}
        />
        <Sheet open={editing !== undefined} onOpenChange={(open) => !open && setEditing(undefined)}>
          <SheetContent className="w-full overflow-y-auto sm:max-w-md">
            <SheetHeader>
              <SheetTitle>{editing?.fullName}</SheetTitle>
            </SheetHeader>
            <div className="px-4 pb-6">
              {editing ? <UserEditor key={editing.id} user={editing} /> : null}
            </div>
          </SheetContent>
        </Sheet>
      </PageBody>
    </>
  )
}
