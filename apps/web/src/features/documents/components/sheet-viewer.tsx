"use client"

import { ZoomInAreaIcon, ZoomOutAreaIcon } from "@hugeicons/core-free-icons"
import { useQuery } from "@tanstack/react-query"
import type { Cell, Workbook, Worksheet } from "exceljs"
import { useMemo, useState } from "react"

import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { fetchBytes, FileFrame, FileMessage } from "@/features/documents/components/file-frame"
import { ToolButton } from "@/features/documents/components/tool-button"
import { cn } from "@/lib/utils"

const ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 2] as const
// Far beyond any price table; a stray cell at row 1,048,576 must not draw a million rows.
const MAX_ROWS = 2000
const MAX_COLUMNS = 80
const HEADER_HEIGHT = 22
const ROW_HEADER_WIDTH = 40
const EMU_PER_PIXEL = 9525

interface SheetViewerProps {
  url: string
  fileName: string
  className?: string
}

/** A workbook read in the browser and shown as it is laid out: one tab per sheet, merged cells,
 * column widths, fonts, fills, borders and pictures. Nothing in it can be edited. */
export function SheetViewer({ url, fileName, className }: SheetViewerProps) {
  const { t } = useTranslation()
  const workbook = useQuery({
    queryKey: ["workbook", url],
    queryFn: async ({ signal }) => readWorkbook(await fetchBytes(url, signal)),
    staleTime: Infinity,
    gcTime: 60_000,
    retry: false,
  })
  const [sheetIndex, setSheetIndex] = useState(0)
  const [zoom, setZoom] = useState(1)
  const sheets = workbook.data ?? []
  const sheet = sheets[Math.min(sheetIndex, sheets.length - 1)]
  const zoomBy = (direction: 1 | -1) => {
    const index = ZOOM_STEPS.findIndex((step) => step >= zoom)
    setZoom(ZOOM_STEPS[Math.min(Math.max(0, index + direction), ZOOM_STEPS.length - 1)] ?? 1)
  }

  return (
    <FileFrame
      url={url}
      fileName={fileName}
      className={className}
      tools={
        <>
          <ToolButton icon={ZoomOutAreaIcon} label={t("pdf.zoomOut")} onClick={() => zoomBy(-1)} />
          <Button
            variant="ghost"
            size="sm"
            className="h-7 min-w-14 px-2 tabular-nums"
            onClick={() => setZoom(1)}
          >
            {Math.round(zoom * 100)}%
          </Button>
          <ToolButton icon={ZoomInAreaIcon} label={t("pdf.zoomIn")} onClick={() => zoomBy(1)} />
        </>
      }
    >
      {workbook.isPending ? <Skeleton className="m-4 h-[60vh] flex-1" /> : null}
      {workbook.isError ? <FileMessage>{t("pdf.loadError")}</FileMessage> : null}
      {workbook.isSuccess && !sheet ? <FileMessage>{t("sheet.empty")}</FileMessage> : null}
      {sheet ? (
        <>
          <div className="min-h-0 flex-1 overflow-auto bg-background">
            <SheetGrid key={sheet.name} sheet={sheet} zoom={zoom} />
          </div>
          {sheets.length > 1 ? (
            <div
              className="flex shrink-0 gap-1 overflow-x-auto border-t bg-muted/50 px-2 py-1"
              role="tablist"
              aria-label={t("sheet.sheets")}
            >
              {sheets.map((item, index) => (
                <Button
                  key={item.name}
                  role="tab"
                  aria-selected={item === sheet}
                  variant={item === sheet ? "secondary" : "ghost"}
                  size="sm"
                  className={cn("h-7 shrink-0", item === sheet && "bg-background shadow-sm")}
                  onClick={() => setSheetIndex(index)}
                >
                  {item.name}
                </Button>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </FileFrame>
  )
}

function SheetGrid({ sheet, zoom }: { sheet: SheetModel; zoom: number }) {
  const left = useMemo(() => offsets(sheet.columns.map((column) => column.width)), [sheet])
  const top = useMemo(() => offsets(sheet.rows.map((row) => row.height)), [sheet])
  const width = left.at(-1) ?? 0
  const height = top.at(-1) ?? 0

  return (
    <div className="relative w-fit text-[11px]" style={{ zoom }}>
      <table
        className="table-fixed border-separate border-spacing-0 bg-white text-black"
        style={{ width: width + ROW_HEADER_WIDTH }}
      >
        <colgroup>
          <col style={{ width: ROW_HEADER_WIDTH }} />
          {sheet.columns.map((column) => (
            <col key={column.name} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead>
          <tr style={{ height: HEADER_HEIGHT }}>
            <td
              aria-hidden
              className="sticky top-0 left-0 z-20 border-r border-b border-neutral-300 bg-neutral-100"
            >
              {" "}
            </td>
            {sheet.columns.map((column) => (
              <th
                key={column.name}
                className="sticky top-0 z-10 overflow-hidden border-r border-b border-neutral-300 bg-neutral-100 font-normal text-neutral-500"
              >
                {column.width > 0 ? column.name : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sheet.rows.map((row) => (
            <tr key={row.number} style={{ height: row.height }}>
              <th className="sticky left-0 z-10 border-r border-b border-neutral-300 bg-neutral-100 font-normal text-neutral-500">
                {row.height > 0 ? row.number : null}
              </th>
              {row.cells.map((cell) =>
                cell ? (
                  <td
                    key={cell.column}
                    rowSpan={cell.rowSpan > 1 ? cell.rowSpan : undefined}
                    colSpan={cell.colSpan > 1 ? cell.colSpan : undefined}
                    className="overflow-hidden border-r border-b border-neutral-200 px-1 align-bottom"
                    style={cell.style}
                  >
                    {cell.text}
                  </td>
                ) : null
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {sheet.pictures.map((picture) => (
        <SheetPicture
          key={picture.id}
          picture={picture}
          left={ROW_HEADER_WIDTH + position(left, picture.from.column, picture.from.columnOffset)}
          top={HEADER_HEIGHT + position(top, picture.from.row, picture.from.rowOffset)}
          maxWidth={width}
          maxHeight={height}
        />
      ))}
    </div>
  )
}

function SheetPicture({
  picture,
  left,
  top,
  maxWidth,
  maxHeight,
}: {
  picture: PictureModel
  left: number
  top: number
  maxWidth: number
  maxHeight: number
}) {
  return (
    // A picture drawn from the workbook's own bytes, not a link next/image could optimise.
    // oxlint-disable-next-line nextjs/no-img-element
    <img
      src={picture.source}
      alt=""
      className="pointer-events-none absolute object-fill"
      style={{
        left,
        top,
        width: Math.min(picture.width, maxWidth),
        height: Math.min(picture.height, maxHeight),
      }}
    />
  )
}

interface CellModel {
  column: number
  text: string
  rowSpan: number
  colSpan: number
  style: React.CSSProperties
}

interface PictureModel {
  id: string
  /** A data URL: the picture is in the workbook, not behind a link. */
  source: string
  from: {
    column: number
    columnOffset: number
    row: number
    rowOffset: number
  }
  width: number
  height: number
}

interface SheetModel {
  name: string
  columns: { name: string; width: number }[]
  /** A cell is `null` where a merged cell covers its place. */
  rows: { number: number; height: number; cells: (CellModel | null)[] }[]
  pictures: PictureModel[]
}

async function readWorkbook(bytes: ArrayBuffer): Promise<SheetModel[]> {
  // About a megabyte of code, so it is only loaded once a workbook is opened.
  const { default: ExcelJS } = await import("exceljs")
  const workbook = new ExcelJS.Workbook()
  await workbook.xlsx.load(bytes)
  return workbook.worksheets
    .filter((worksheet) => worksheet.state === "visible" || worksheet.state === undefined)
    .map((worksheet) => readSheet(workbook, worksheet))
    .filter((sheet) => sheet.rows.length > 0 || sheet.pictures.length > 0)
}

function readSheet(workbook: Workbook, worksheet: Worksheet): SheetModel {
  const merges = (worksheet.model.merges ?? []).flatMap((range) => {
    const parsed = parseRange(range)
    return parsed ? [parsed] : []
  })
  const images = worksheet.getImages()

  let lastRow = 0
  let lastColumn = 0
  worksheet.eachRow({ includeEmpty: false }, (row, rowNumber) => {
    row.eachCell({ includeEmpty: false }, (cell, cellColumn) => {
      if (safeText(cell).trim() === "") return
      lastRow = Math.max(lastRow, rowNumber)
      lastColumn = Math.max(lastColumn, cellColumn)
    })
  })
  for (const merge of merges) {
    if (merge.top > lastRow || merge.left > lastColumn) continue
    lastRow = Math.max(lastRow, merge.bottom)
    lastColumn = Math.max(lastColumn, merge.right)
  }
  for (const image of images) {
    const end = image.range.br ?? image.range.tl
    lastRow = Math.max(lastRow, Math.ceil(end.nativeRow) + 1)
    lastColumn = Math.max(lastColumn, Math.ceil(end.nativeCol) + 1)
  }
  lastRow = Math.min(lastRow, MAX_ROWS)
  lastColumn = Math.min(lastColumn, MAX_COLUMNS)

  const defaultWidth = worksheet.properties.defaultColWidth ?? 8.43
  const defaultHeight = worksheet.properties.defaultRowHeight ?? 15
  const columnWidths = Array.from({ length: lastColumn }, (_, index) => {
    const column = worksheet.getColumn(index + 1)
    return column.hidden ? 0 : Math.round((column.width ?? defaultWidth) * 7 + 5)
  })
  const rowHeights = Array.from({ length: lastRow }, (_, index) => {
    const row = worksheet.getRow(index + 1)
    return row.hidden ? 0 : Math.round((row.height ?? defaultHeight) * (4 / 3))
  })

  const covered = new Set<string>()
  const spans = new Map<string, { rowSpan: number; colSpan: number }>()
  for (const merge of merges) {
    spans.set(`${merge.top}:${merge.left}`, {
      rowSpan: Math.min(merge.bottom, lastRow) - merge.top + 1,
      colSpan: Math.min(merge.right, lastColumn) - merge.left + 1,
    })
    for (let row = merge.top; row <= merge.bottom; row++) {
      for (let column = merge.left; column <= merge.right; column++) {
        if (row !== merge.top || column !== merge.left) covered.add(`${row}:${column}`)
      }
    }
  }

  const rows = Array.from({ length: lastRow }, (_, rowIndex) => {
    const row = worksheet.getRow(rowIndex + 1)
    const cells = Array.from({ length: lastColumn }, (_cell, columnIndex): CellModel | null => {
      const key = `${rowIndex + 1}:${columnIndex + 1}`
      if (covered.has(key)) return null
      const cell = row.getCell(columnIndex + 1)
      const span = spans.get(key)
      return {
        column: columnIndex + 1,
        text: cellText(cell),
        rowSpan: span?.rowSpan ?? 1,
        colSpan: span?.colSpan ?? 1,
        style: cellStyle(cell),
      }
    })
    return { number: rowIndex + 1, height: rowHeights[rowIndex] ?? 0, cells }
  })

  const pictures = images.flatMap((image, index): PictureModel[] => {
    const media = workbook.getImage(Number(image.imageId))
    if (!media?.buffer) return []
    const { tl: from, br: to } = image.range
    const ext = (image.range as { ext?: { width: number; height: number } }).ext
    const start = {
      column: Math.floor(from.nativeCol),
      columnOffset: from.nativeColOff / EMU_PER_PIXEL,
      row: Math.floor(from.nativeRow),
      rowOffset: from.nativeRowOff / EMU_PER_PIXEL,
    }
    const columnLeft = offsets(columnWidths)
    const rowTop = offsets(rowHeights)
    const width = ext
      ? ext.width
      : position(columnLeft, to.nativeCol, to.nativeColOff / EMU_PER_PIXEL) -
        position(columnLeft, start.column, start.columnOffset)
    const height = ext
      ? ext.height
      : position(rowTop, to.nativeRow, to.nativeRowOff / EMU_PER_PIXEL) -
        position(rowTop, start.row, start.rowOffset)
    if (width <= 0 || height <= 0) return []
    const source = `data:image/${media.extension};base64,${base64(media.buffer)}`
    return [{ id: `${index}`, source, from: start, width, height }]
  })

  const columns = columnWidths.map((width, index) => ({
    name: columnName(index + 1),
    width,
  }))
  return { name: worksheet.name, columns, rows, pictures }
}

/** The text Excel shows, with numbers and dates written the Vietnamese way. */
function cellText(cell: Cell): string {
  let value: unknown = cell.value
  if (value && typeof value === "object" && "result" in value) value = value.result
  if (value instanceof Date) {
    const day = String(value.getUTCDate()).padStart(2, "0")
    const month = String(value.getUTCMonth() + 1).padStart(2, "0")
    return `${day}/${month}/${value.getUTCFullYear()}`
  }
  if (typeof value === "number") {
    const format = (cell.numFmt ?? "").split(";")[0] ?? ""
    const decimals = /\.(0+)/.exec(format)?.[1]?.length
    if (format.includes("%")) {
      return `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: decimals ?? 2 }).format(value * 100)}%`
    }
    return new Intl.NumberFormat("vi-VN", {
      minimumFractionDigits: decimals ?? 0,
      maximumFractionDigits: decimals ?? 10,
      useGrouping: format.includes(",") || format === "" || format === "General",
    }).format(value)
  }
  return safeText(cell)
}

/** ExcelJS throws on the text of a merged cell whose top-left cell is empty. */
function safeText(cell: Cell): string {
  try {
    return cell.text ?? ""
  } catch {
    return ""
  }
}

const TEXT_ALIGN: Record<string, React.CSSProperties["textAlign"]> = {
  left: "left",
  center: "center",
  right: "right",
  fill: "left",
  justify: "justify",
  centerContinuous: "center",
  distributed: "center",
}
const VERTICAL_ALIGN: Record<string, React.CSSProperties["verticalAlign"]> = {
  top: "top",
  middle: "middle",
  bottom: "bottom",
  distributed: "middle",
  justify: "top",
}
const BORDER_LINE: Record<string, [number, string]> = {
  thin: [1, "solid"],
  hair: [1, "dotted"],
  dotted: [1, "dotted"],
  dashed: [1, "dashed"],
  dashDot: [1, "dashed"],
  dashDotDot: [1, "dashed"],
  double: [3, "double"],
  medium: [2, "solid"],
  mediumDashed: [2, "dashed"],
  mediumDashDot: [2, "dashed"],
  mediumDashDotDot: [2, "dashed"],
  slantDashDot: [2, "dashed"],
  thick: [3, "solid"],
}

function cellStyle(cell: Cell): React.CSSProperties {
  const style: React.CSSProperties = {}
  const { font, fill, alignment, border } = cell
  if (font?.bold) style.fontWeight = 700
  if (font?.italic) style.fontStyle = "italic"
  if (font?.underline || font?.strike) {
    style.textDecoration = [font.underline && "underline", font.strike && "line-through"]
      .filter(Boolean)
      .join(" ")
  }
  if (font?.size) style.fontSize = `${Math.round(font.size * (4 / 3))}px`
  const color = argb(font?.color?.argb)
  if (color) style.color = color
  if (fill?.type === "pattern" && fill.pattern === "solid") {
    const background = argb(fill.fgColor?.argb)
    if (background) style.backgroundColor = background
  }
  style.whiteSpace = alignment?.wrapText ? "pre-wrap" : "nowrap"
  if (alignment?.horizontal) {
    style.textAlign = TEXT_ALIGN[alignment.horizontal]
  } else if (typeof cell.value === "number" || cell.value instanceof Date) {
    style.textAlign = "right"
  }
  if (alignment?.vertical) style.verticalAlign = VERTICAL_ALIGN[alignment.vertical]
  for (const [side, property] of [
    ["top", "borderTop"],
    ["right", "borderRight"],
    ["bottom", "borderBottom"],
    ["left", "borderLeft"],
  ] as const) {
    const line = border?.[side]
    if (!line?.style) continue
    const [width, kind] = BORDER_LINE[line.style] ?? [1, "solid"]
    style[property] = `${width}px ${kind} ${argb(line.color?.argb) ?? "#000"}`
  }
  return style
}

/** Excel's AARRGGBB colour as CSS, or nothing for a theme colour it does not spell out. */
function argb(value: string | undefined): string | undefined {
  return value?.length === 8 ? `#${value.slice(2)}` : undefined
}

function parseRange(range: string) {
  const match = /^([A-Z]+)(\d+):([A-Z]+)(\d+)$/.exec(range)
  if (!match) return null
  const [, left = "", top = "", right = "", bottom = ""] = match
  return {
    left: columnNumber(left),
    top: Number(top),
    right: columnNumber(right),
    bottom: Number(bottom),
  }
}

function columnNumber(name: string): number {
  let number = 0
  for (let index = 0; index < name.length; index++)
    number = number * 26 + name.charCodeAt(index) - 64
  return number
}

function columnName(number: number): string {
  let name = ""
  for (let rest = number; rest > 0; rest = Math.floor((rest - 1) / 26)) {
    name = String.fromCharCode(65 + ((rest - 1) % 26)) + name
  }
  return name
}

function base64(bytes: ArrayBuffer | Uint8Array): string {
  const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes)
  let binary = ""
  for (let index = 0; index < view.length; index += 0x8000) {
    binary += String.fromCharCode(...view.subarray(index, index + 0x8000))
  }
  return btoa(binary)
}

/** Where each column (or row) starts, plus where the last one ends. */
function offsets(sizes: number[]): number[] {
  const starts = [0]
  for (const size of sizes) starts.push((starts.at(-1) ?? 0) + size)
  return starts
}

function position(starts: number[], index: number, offset: number): number {
  const whole = Math.floor(index)
  return (starts[Math.min(whole, starts.length - 1)] ?? 0) + offset
}
