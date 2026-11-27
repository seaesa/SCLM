"use client"

import { useState } from "react"
import { toast } from "sonner"

import type { FuelPriceRead } from "@workspace/api-client"
import { useHasPermission } from "@workspace/core/auth"
import { formatDate } from "@workspace/core/lib/date"
import { describeApiError } from "@workspace/core/lib/form"
import { usePaging } from "@workspace/core/lib/paging"
import {
  useDeleteFuelPrice,
  useFuelPriceForm,
  useFuelPrices,
  useSyncFuelPrices,
} from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { type DataColumn } from "@/components/design-system/data-table/data-table"
import { PagedTable } from "@/components/design-system/data-table/paged-table"
import { FormDate } from "@/components/design-system/form/form-date"
import { FormInput } from "@/components/design-system/form/form-input"
import { PageBody, PageHeader } from "@/components/design-system/page-header"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"

import { DialogFormFooter } from "./dialog-form-parts"
import { formatAmount } from "./pricing-format"

function DeleteFuelPrice({ price }: { price: FuelPriceRead }) {
  const { t } = useTranslation()
  const remove = useDeleteFuelPrice()
  return (
    <Button
      size="sm"
      variant="ghost"
      disabled={remove.isPending}
      onClick={() =>
        remove.mutate(
          { path: { fuelPriceId: price.id } },
          {
            onSuccess: () => toast.success(t("pricing.fuelPrices.deleted")),
            onError: (error) => toast.error(describeApiError(error)),
          }
        )
      }
    >
      {t("pricing.fuelPrices.delete")}
    </Button>
  )
}

const COLUMNS: DataColumn<FuelPriceRead>[] = [
  { id: "fuelType", label: "pricing.fuel.fuelType", accessorKey: "fuelType" },
  {
    id: "effectiveOn",
    label: "pricing.fuelPrices.effectiveOn",
    accessorKey: "effectiveOn",
    cell: ({ row }) => formatDate(row.original.effectiveOn),
  },
  {
    id: "price",
    label: "pricing.fuelPrices.price",
    accessorFn: (row) => Number(row.price),
    cell: ({ row }) => <span className="tabular-nums">{formatAmount(row.original.price)}</span>,
  },
  { id: "source", label: "pricing.fuelPrices.source", accessorKey: "source", enableSorting: false },
]

const MANAGE_COLUMN: DataColumn<FuelPriceRead> = {
  id: "actions",
  label: "pricing.actions",
  enableSorting: false,
  cell: ({ row }) => (row.original.isOfficial ? null : <DeleteFuelPrice price={row.original} />),
}

function SyncButton() {
  const { t } = useTranslation()
  const sync = useSyncFuelPrices()
  return (
    <Button
      variant="outline"
      disabled={sync.isPending}
      onClick={() =>
        sync.mutate(
          {},
          {
            onSuccess: (report) =>
              toast.success(
                t("pricing.fuelPrices.synced", { added: report.added + report.updated })
              ),
            onError: (error) => toast.error(describeApiError(error)),
          }
        )
      }
    >
      {t("pricing.fuelPrices.sync")}
    </Button>
  )
}

/** Official prices synced from Petrolimex, plus older prices entered by hand for past contracts. */
export function FuelPriceList() {
  const { t } = useTranslation()
  const canManage = useHasPermission("fuel-prices:manage")
  const [fuelType, setFuelType] = useState("")
  const paging = usePaging()
  const query = useFuelPrices({
    fuelType: fuelType.trim() || undefined,
    page: paging.page,
    pageSize: paging.pageSize,
  })
  return (
    <>
      <PageHeader
        title={t("pricing.fuelPrices.title")}
        actions={
          canManage ? (
            <>
              <SyncButton />
              <FuelPriceDialog fuelType={fuelType.trim()} />
            </>
          ) : null
        }
      />
      <PageBody>
        <PagedTable
          query={query}
          paging={paging}
          emptyText={t("pricing.fuelPrices.empty")}
          columns={canManage ? [...COLUMNS, MANAGE_COLUMN] : COLUMNS}
          getRowId={(row) => row.id}
          toolbar={
            <Input
              className="max-w-xs"
              value={fuelType}
              aria-label={t("pricing.fuel.fuelType")}
              placeholder={t("pricing.fuelPrices.filter")}
              onChange={(event) => {
                setFuelType(event.target.value)
                paging.resetPage()
              }}
            />
          }
        />
      </PageBody>
    </>
  )
}

function FuelPriceDialog({ fuelType }: { fuelType: string }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" />}>{t("pricing.fuelPrices.add")}</DialogTrigger>
      <DialogContent>
        {open && <FuelPriceForm fuelType={fuelType} onSaved={() => setOpen(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function FuelPriceForm({ fuelType, onSaved }: { fuelType: string; onSaved: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = useFuelPriceForm({
    fuelType: fuelType || undefined,
    onSaved: () => {
      toast.success(t("pricing.saved"))
      onSaved()
    },
  })
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t("pricing.fuelPrices.add")}</DialogTitle>
      </DialogHeader>
      <FormInput
        control={form.control}
        name="fuelType"
        label={t("pricing.fuel.fuelType")}
        placeholder={t("pricing.fuel.fuelTypePlaceholder")}
      />
      <div className="grid grid-cols-2 gap-3">
        <FormDate
          control={form.control}
          name="effectiveOn"
          label={t("pricing.fuelPrices.effectiveOn")}
        />
        <FormInput
          control={form.control}
          name="price"
          inputMode="numeric"
          label={t("pricing.fuelPrices.price")}
        />
      </div>
      <FormInput control={form.control} name="source" label={t("pricing.fuelPrices.source")} />
      <DialogFormFooter errors={form.formState.errors} isSubmitting={form.formState.isSubmitting} />
    </form>
  )
}
