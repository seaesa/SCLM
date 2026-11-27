"use client"

import type { Route } from "next"
import Link from "next/link"
import { Fragment } from "react"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { cn } from "@/lib/utils"

interface PageHeaderProps {
  title: React.ReactNode
  description?: React.ReactNode
  /** Pages above this one, outermost first. */
  parents?: readonly { href: Route; label: string }[]
  actions?: React.ReactNode
  /** Badges or facts shown under the title. */
  meta?: React.ReactNode
}

const NO_PARENTS: NonNullable<PageHeaderProps["parents"]> = []

/** The top of every signed-in page: sidebar toggle, breadcrumb, title and page actions. */
export function PageHeader({
  title,
  description,
  parents = NO_PARENTS,
  actions,
  meta,
}: PageHeaderProps) {
  return (
    <>
      <header className="sticky top-0 z-10 flex h-12 shrink-0 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mr-2 data-vertical:h-4 data-vertical:self-auto"
        />
        <Breadcrumb>
          <BreadcrumbList>
            {parents.map((parent) => (
              <Fragment key={parent.href}>
                <BreadcrumbItem className="hidden md:inline-flex">
                  <BreadcrumbLink render={<Link href={parent.href} />}>
                    {parent.label}
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
              </Fragment>
            ))}
            <BreadcrumbItem>
              <BreadcrumbPage className="max-w-[40ch] truncate">{title}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </header>
      <div className="flex flex-wrap items-start justify-between gap-4 px-4 pt-6 pb-4 md:px-6">
        <div className="flex min-w-0 flex-col gap-1.5">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
          {meta ? <div className="flex flex-wrap items-center gap-2 pt-1">{meta}</div> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </>
  )
}

/** Page body with the standard padding. */
export function PageBody({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex min-w-0 flex-col gap-4 px-4 pb-10 md:px-6", className)}>
      {children}
    </div>
  )
}
