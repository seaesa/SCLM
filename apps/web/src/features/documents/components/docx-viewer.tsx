"use client"

import { renderAsync } from "docx-preview"
import { useEffect, useRef, useState } from "react"

import { useTranslation } from "@workspace/i18n"

import { Skeleton } from "@/components/ui/skeleton"
import { FileFrame, FileMessage, useFileBytes } from "@/features/documents/components/file-frame"

interface DocxViewerProps {
  url: string
  fileName: string
  className?: string
}

/** A Word document laid out page by page, close to how Word prints it. */
export function DocxViewer({ url, fileName, className }: DocxViewerProps) {
  const { t } = useTranslation()
  const { data, isPending, isError } = useFileBytes(url)
  const body = useRef<HTMLDivElement>(null)
  const [hasFailed, setHasFailed] = useState(false)

  useEffect(() => {
    const element = body.current
    if (!data || !element) return
    let isCurrent = true
    renderAsync(data, element, undefined, {
      inWrapper: true,
      breakPages: true,
    }).catch(() => {
      if (isCurrent) setHasFailed(true)
    })
    return () => {
      isCurrent = false
      element.replaceChildren()
    }
  }, [data])

  return (
    <FileFrame url={url} fileName={fileName} className={className}>
      {isPending ? <Skeleton className="m-4 h-[60vh] flex-1" /> : null}
      {isError || hasFailed ? <FileMessage>{t("pdf.loadError")}</FileMessage> : null}
      <div
        ref={body}
        className="min-h-0 flex-1 overflow-auto [&_.docx-wrapper]:w-fit [&_.docx-wrapper]:min-w-full [&_.docx-wrapper]:bg-transparent [&_.docx-wrapper]:p-4"
        hidden={isPending || isError || hasFailed}
      />
    </FileFrame>
  )
}
