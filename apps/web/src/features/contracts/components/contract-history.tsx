"use client"

import type { ContractEventRead, FactChange, FieldSpecRead } from "@workspace/api-client"
import { formatDate } from "@workspace/core/lib/date"
import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"

import { FieldValueText } from "./field-value-text"

interface ContractHistoryProps {
  events: ContractEventRead[]
  specs: FieldSpecRead[]
  onShowFile: (fileId: string) => void
}

/** Every change to the contract, newest first: who did what, to which document, and the values
 * before and after. It is the record to trust when a value is questioned. */
export function ContractHistory({ events, specs, onShowFile }: ContractHistoryProps) {
  const { t } = useTranslation()
  if (events.length === 0) {
    return (
      <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
        {t("contracts.history.empty")}
      </p>
    )
  }
  // Newest first; `toReversed` is not in this TS lib and `reverse` would mutate the cache.
  const newestFirst = events.map(
    (_, index) => events[events.length - 1 - index] as ContractEventRead
  )
  return (
    <ol className="flex flex-col gap-4 border-l pl-5">
      {newestFirst.map((event) => (
        <li key={event.id} className="relative flex flex-col gap-1.5">
          <span className="absolute top-1.5 -left-[1.6rem] size-2.5 rounded-full border-2 border-background bg-primary" />
          <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
            <span className="font-medium">{t(`contracts.history.kind.${event.kind}`)}</span>
            {event.instrumentCode ? (
              <span className="font-mono text-xs">{event.instrumentCode}</span>
            ) : null}
            <span className="text-muted-foreground">
              {event.actorName ?? "—"} · {formatDate(event.createdAt, "Pp")}
            </span>
          </div>
          {event.changes.length > 0 ? <ChangeList changes={event.changes} specs={specs} /> : null}
          {event.comment ? <p className="text-sm whitespace-pre-line">{event.comment}</p> : null}
          {event.fileId && event.kind !== "deleted" ? (
            <Button
              variant="link"
              size="sm"
              className="h-auto self-start p-0"
              onClick={() => onShowFile(event.fileId ?? "")}
            >
              {t("contracts.history.showDraft")}
            </Button>
          ) : null}
        </li>
      ))}
    </ol>
  )
}

function ChangeList({ changes, specs }: { changes: FactChange[]; specs: FieldSpecRead[] }) {
  const { t } = useTranslation()
  return (
    <dl className="grid grid-cols-[minmax(0,10rem)_minmax(0,1fr)] gap-x-3 gap-y-1 rounded-lg bg-muted/40 px-3 py-2 text-sm">
      {changes.map((change) => {
        const spec = specs.find((candidate) => candidate.key === change.key)
        return (
          <div key={change.key} className="contents">
            <dt className="text-muted-foreground">{t(`contracts.fields.${change.key}`)}</dt>
            <dd className="flex min-w-0 flex-wrap items-baseline gap-x-1.5">
              <span className="text-muted-foreground line-through">
                {change.before ? <FieldValueText spec={spec} value={change.before} /> : "—"}
              </span>
              <span aria-hidden>→</span>
              <span>
                {change.after ? <FieldValueText spec={spec} value={change.after} /> : "—"}
              </span>
            </dd>
          </div>
        )
      })}
    </dl>
  )
}
