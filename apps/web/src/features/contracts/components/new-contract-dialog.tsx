"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"

import type {
  ContractCategory,
  PartnerRead,
  PartnerRole,
  PartnerSummary,
} from "@workspace/api-client"
import { useHasPermission } from "@workspace/core/auth"
import { useCreateContract } from "@workspace/core/contracts"
import { describeApiError } from "@workspace/core/lib/form"
import { useTranslation } from "@workspace/i18n"

import { ChoiceSelect } from "@/components/design-system/choice-select"
import { FilterTabs } from "@/components/design-system/list-states"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { CAN_ADD_DOCUMENTS } from "@/config"
import { PartnerPicker } from "@/features/partners/components/partner-picker"

import { CONTRACT_CATEGORIES } from "../constants"

const SIDES = [{ key: "customer" }, { key: "supplier" }] as const satisfies readonly {
  key: PartnerRole
}[]

const ACCEPTED_FILES = ".pdf,.doc,.docx,.xls,.xlsx"

const ORIGINS = ["signed", "draft"] as const

const CATEGORY_OPTIONS = CONTRACT_CATEGORIES.map((key) => ({ key }))

/** Customer and contractor contracts imply the side; a warehouse lease can go either way. */
const SIDE_OF: Partial<Record<ContractCategory, PartnerRole>> = {
  customer: "customer",
  contractor: "supplier",
}

/** The contract a new one is signed to replace: partner and category carry over. */
export interface ReplacedContract {
  id: string
  category: ContractCategory
  side: PartnerRole
  partner: PartnerSummary
}

/** Create a contract from its scan; the facts are entered on the contract page beside it. */
export function NewContractDialog({ replaces }: { replaces?: ReplacedContract }) {
  const { t } = useTranslation()
  const canRegister = useHasPermission("contracts:register")
  const [open, setOpen] = useState(false)
  if (!canRegister || !CAN_ADD_DOCUMENTS) return null
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant={replaces ? "outline" : "default"} />}>
        {t(replaces ? "contracts.resign.action" : "contracts.new.title")}
      </DialogTrigger>
      <DialogContent>{open && <NewContractForm replaces={replaces} />}</DialogContent>
    </Dialog>
  )
}

function NewContractForm({ replaces }: { replaces?: ReplacedContract }) {
  const { t } = useTranslation()
  const router = useRouter()
  const create = useCreateContract()
  const [category, setCategory] = useState<ContractCategory>(replaces?.category ?? "customer")
  const [warehouseSide, setWarehouseSide] = useState<PartnerRole>(replaces?.side ?? "customer")
  const [partner, setPartner] = useState<PartnerRead>()
  const [file, setFile] = useState<File>()
  const [origin, setOrigin] = useState<(typeof ORIGINS)[number]>("signed")
  const side = SIDE_OF[category] ?? warehouseSide
  const partnerId = replaces?.partner.id ?? partner?.id

  const handleCreate = () => {
    if (!partnerId || !file) return
    create.mutate(
      {
        body: {
          category,
          partnerId,
          side,
          file,
          needsApproval: origin === "draft",
          replacesId: replaces?.id,
        },
      },
      {
        onSuccess: (contract) => {
          toast.success(t("contracts.created"))
          router.push(`/contracts/${contract.id}`)
        },
        onError: (error) => toast.error(describeApiError(error)),
      }
    )
  }

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <DialogHeader>
        <DialogTitle>{t(replaces ? "contracts.resign.title" : "contracts.new.title")}</DialogTitle>
      </DialogHeader>
      {replaces ? (
        <Field>
          <FieldLabel>{t("contracts.columns.partner")}</FieldLabel>
          <p className="text-sm">{replaces.partner.name}</p>
        </Field>
      ) : (
        <>
          <Field>
            <FieldLabel>{t("contracts.columns.category")}</FieldLabel>
            <FilterTabs
              options={CATEGORY_OPTIONS}
              value={category}
              onChange={(next) => {
                setCategory(next)
                setPartner(undefined)
              }}
              label={(key) => t(`contracts.category.${key}`)}
            />
          </Field>
          {category === "warehouse" ? (
            <Field>
              <FieldLabel>{t("contracts.new.side")}</FieldLabel>
              <FilterTabs
                options={SIDES}
                value={warehouseSide}
                onChange={(next) => {
                  setWarehouseSide(next)
                  setPartner(undefined)
                }}
                label={(key) => t(`contracts.new.sides.${key}`)}
              />
            </Field>
          ) : null}
          <Field>
            <FieldLabel>{t("contracts.columns.partner")}</FieldLabel>
            <PartnerPicker role={side} value={partner} onChange={setPartner} />
          </Field>
        </>
      )}
      <Field>
        <FieldLabel htmlFor="new-contract-file">{t("contracts.new.file")}</FieldLabel>
        <Input
          id="new-contract-file"
          type="file"
          accept={ACCEPTED_FILES}
          onChange={(event) => setFile(event.target.files?.[0])}
        />
      </Field>
      <Field>
        <FieldLabel>{t("contracts.instrumentDialog.origin")}</FieldLabel>
        <ChoiceSelect
          label={t("contracts.instrumentDialog.origin")}
          value={origin}
          onChange={(next) => setOrigin(next ?? "signed")}
          options={ORIGINS.map((value) => ({
            value,
            label: t(`contracts.instrumentDialog.${value}`),
          }))}
          className="w-full"
        />
      </Field>
      <DialogFooter>
        <Button onClick={handleCreate} disabled={!partnerId || !file || create.isPending}>
          {t("contracts.new.create")}
        </Button>
      </DialogFooter>
    </div>
  )
}
