"use client"

import dynamic from "next/dynamic"
import { useState } from "react"
import { ErrorBoundary } from "react-error-boundary"

import { useDocumentFileUrl } from "@workspace/core/documents"
import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { FileFrame, FileMessage } from "@/features/documents/components/file-frame"
import { ImageViewer } from "@/features/documents/components/image-viewer"

const loading = () => <Skeleton className="h-[75vh] w-full" />
// pdf.js, ExcelJS and docx-preview need the browser and are large, so each is loaded only when
// a file of its kind is opened, and never rendered on the server.
const PdfViewer = dynamic(
  () => import("@/features/documents/components/pdf-viewer").then((module) => module.PdfViewer),
  { ssr: false, loading }
)
const SheetViewer = dynamic(
  () => import("@/features/documents/components/sheet-viewer").then((module) => module.SheetViewer),
  { ssr: false, loading }
)
const DocxViewer = dynamic(
  () => import("@/features/documents/components/docx-viewer").then((module) => module.DocxViewer),
  { ssr: false, loading }
)

type FileKind = "pdf" | "image" | "sheet" | "docx" | "other"

/** Which viewer reads the file, from its type and, failing that, its name. */
function fileKind(contentType: string | undefined, fileName: string): FileKind {
  const type = contentType ?? ""
  const extension = fileName.split(".").at(-1)?.toLowerCase() ?? ""
  if (type === "application/pdf" || extension === "pdf") return "pdf"
  if (type.startsWith("image/") || ["jpg", "jpeg", "png", "gif", "webp"].includes(extension)) {
    return "image"
  }
  if (type.includes("spreadsheetml") || extension === "xlsx") return "sheet"
  if (type.includes("wordprocessingml") || extension === "docx") return "docx"
  return "other"
}

interface DocumentFileViewerProps {
  setId: string
  fileId: string
  fileName: string
  contentType?: string
  /** Page to open, e.g. the page a fact cites (PDF only). */
  page?: number
  onPageChange?: (page: number) => void
  className?: string
}

/** The signed file itself, so every fact is entered and checked against the page it cites. */
export function DocumentFileViewer({
  setId,
  fileId,
  contentType,
  ...props
}: DocumentFileViewerProps) {
  const { t } = useTranslation()
  const { data, isPending, isError, refetch } = useDocumentFileUrl(setId, fileId)
  // A refreshed link would make the reader download the file again: keep the first one per file.
  const [opened, setOpened] = useState<{ fileId: string; url: string }>()
  if (data && opened?.fileId !== fileId) setOpened({ fileId, url: data.url })

  if (isPending && !opened) return <Skeleton className="h-[75vh] w-full" />
  if ((isError || !data) && !opened) {
    return (
      <Button variant="outline" onClick={() => void refetch()}>
        {t("common.retry")}
      </Button>
    )
  }
  if (!opened) return null
  const { url } = opened
  const { fileName, className } = props
  const kind = fileKind(contentType, fileName)
  // A file the viewer cannot read only loses the preview; the contract page stays usable.
  return (
    <ErrorBoundary
      resetKeys={[opened.fileId]}
      fallback={
        <FileFrame url={url} fileName={fileName} className={className}>
          <FileMessage>{t("pdf.loadError")}</FileMessage>
        </FileFrame>
      }
    >
      {kind === "pdf" ? <PdfViewer key={opened.fileId} url={url} {...props} /> : null}
      {kind === "image" ? (
        <ImageViewer key={opened.fileId} url={url} fileName={fileName} className={className} />
      ) : null}
      {kind === "sheet" ? (
        <SheetViewer key={opened.fileId} url={url} fileName={fileName} className={className} />
      ) : null}
      {kind === "docx" ? (
        <DocxViewer key={opened.fileId} url={url} fileName={fileName} className={className} />
      ) : null}
      {kind === "other" ? (
        <FileFrame url={url} fileName={fileName} className={className}>
          <FileMessage>{t("file.noPreview")}</FileMessage>
        </FileFrame>
      ) : null}
    </ErrorBoundary>
  )
}
