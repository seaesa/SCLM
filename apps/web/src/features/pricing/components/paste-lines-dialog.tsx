"use client"

import { useId, useState } from "react"
import { toast } from "sonner"

import type { PriceTableRead } from "@workspace/api-client"
import { describeApiError } from "@workspace/core/lib/form"
import { parsePastedLines, PASTE_COLUMNS, useCreatePriceLines } from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

import { formatAmount } from "./pricing-format"

/** Paste rows copied from Excel; nothing is saved until every row reads without guessing. */
export function PasteLinesDialog({
  contractId,
  table,
}: {
  contractId: string
  table: PriceTableRead
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" variant="outline" />}>
        {t("pricing.pasteLines")}
      </DialogTrigger>
      <DialogContent className="sm:max-w-4xl">
        {open && (
          <PasteLinesForm contractId={contractId} table={table} onDone={() => setOpen(false)} />
        )}
      </DialogContent>
    </Dialog>
  )
}

function PasteLinesForm({
  contractId,
  table,
  onDone,
}: {
  contractId: string
  table: PriceTableRead
  onDone: () => void
}) {
  const { t } = useTranslation()
  const id = useId()
  const [text, setText] = useState("")
  const [hasHeader, setHasHeader] = useState(false)
  const create = useCreatePriceLines(contractId)
  const { lines, issues } = parsePastedLines(text, { defaultPage: table.page, hasHeader })
  const canSave = lines.length > 0 && issues.length === 0 && !create.isPending

  const save = () =>
    create.mutate(
      { path: { tableId: table.id }, body: { lines } },
      {
        onSuccess: () => {
          toast.success(t("pricing.linesAdded", { count: lines.length }))
          onDone()
        },
        onError: (error) => toast.error(describeApiError(error)),
      }
    )

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <DialogHeader>
        <DialogTitle>{t("pricing.pasteLines")}</DialogTitle>
        <DialogDescription>
          {t("pricing.pasteHint", {
            columns: PASTE_COLUMNS.map((column) => t(`pricing.columns.${column}`)).join(" | "),
            page: table.page,
          })}
        </DialogDescription>
      </DialogHeader>
      <Textarea
        aria-label={t("pricing.pasteLines")}
        className="min-h-40 font-mono text-xs"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={t("pricing.pastePlaceholder")}
      />
      <div className="flex items-center gap-2">
        <Checkbox id={id} checked={hasHeader} onCheckedChange={setHasHeader} />
        <Label htmlFor={id}>{t("pricing.hasHeader")}</Label>
      </div>
      {issues.length > 0 ? (
        <Alert variant="destructive">
          <AlertDescription>
            <ul className="list-disc pl-4">
              {issues.slice(0, 20).map((issue) => (
                <li key={`${issue.row}-${issue.column}`}>
                  {t(`pricing.issue.${issue.code}`, {
                    row: issue.row,
                    column: t(`pricing.columns.${issue.column}`),
                  })}
                </li>
              ))}
            </ul>
            {issues.length > 20 ? t("pricing.moreIssues", { count: issues.length - 20 }) : null}
          </AlertDescription>
        </Alert>
      ) : null}
      {lines.length > 0 ? (
        <div className="max-h-72 overflow-auto rounded-lg border">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-muted text-left">
              <tr>
                {PASTE_COLUMNS.map((column) => (
                  <th key={column} className="px-2 py-1.5 font-medium">
                    {t(`pricing.columns.${column}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => (
                // oxlint-disable-next-line react/no-array-index-key -- rows have no other identity
                <tr key={index} className="border-t">
                  <td className="px-2 py-1">{line.service}</td>
                  <td className="px-2 py-1">{line.origin ?? "—"}</td>
                  <td className="px-2 py-1">{line.destination ?? "—"}</td>
                  <td className="px-2 py-1">{line.vehicle ?? "—"}</td>
                  <td className="px-2 py-1">{line.unit}</td>
                  <td className="px-2 py-1 text-right tabular-nums">
                    {formatAmount(String(line.unitPrice))}
                  </td>
                  <td className="px-2 py-1 tabular-nums">{line.page}</td>
                  <td className="px-2 py-1">{line.note ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <DialogFooter>
        <Button disabled={!canSave} onClick={save}>
          {t("pricing.addLines", { count: lines.length })}
        </Button>
      </DialogFooter>
    </div>
  )
}
