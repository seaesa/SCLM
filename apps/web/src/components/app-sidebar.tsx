"use client"

import {
  DashboardSquare01Icon,
  File01Icon,
  FuelStationIcon,
  UserGroupIcon,
  UserSettings01Icon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon, type IconSvgElement } from "@hugeicons/react"
import type { Route } from "next"
import Image from "next/image"
import Link from "next/link"
import { usePathname } from "next/navigation"

import type { Permission } from "@workspace/api-client"
import { useCurrentUser } from "@workspace/core/auth"
import { useTranslation } from "@workspace/i18n"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { IS_OVERVIEW_VISIBLE, IS_PRICING_VISIBLE } from "@/config"

interface NavItem {
  href: Route
  key: string
  icon: IconSvgElement
  permission: Permission
}

const NAV_GROUPS = [
  {
    key: "overview",
    items: [
      { href: "/", key: "overview", icon: DashboardSquare01Icon, permission: "contracts:read" },
    ],
  },
  {
    key: "contracts",
    items: [
      { href: "/contracts", key: "contracts", icon: File01Icon, permission: "contracts:read" },
      { href: "/partners", key: "partners", icon: UserGroupIcon, permission: "partners:read" },
      {
        href: "/fuel-prices",
        key: "fuelPrices",
        icon: FuelStationIcon,
        permission: "contracts:read",
      },
    ],
  },
  {
    key: "admin",
    items: [
      { href: "/admin/users", key: "users", icon: UserSettings01Icon, permission: "users:manage" },
    ],
  },
] as const satisfies readonly { key: string; items: readonly NavItem[] }[]

/** The home link is current only on the home page; others also on their sub-pages. */
const isCurrent = (pathname: string, href: string) =>
  href === "/" ? pathname === "/" : pathname.startsWith(href)

/** Sections the signed-in user may open (the API enforces the same permissions); `footer` holds
 * the signed-in user, which belongs to the auth feature. */
export function AppSidebar({ footer }: { footer: React.ReactNode }) {
  const { t } = useTranslation()
  const pathname = usePathname()
  const { data: user } = useCurrentUser()
  const allowed = (item: NavItem) => user?.permissions.includes(item.permission) ?? false

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" className="gap-3" render={<Link href="/" />}>
              <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-white shadow-sm ring-1 ring-black/5">
                <Image src="/brand/mark.png" alt="" width={28} height={28} className="size-7" />
              </span>
              <span className="flex min-w-0 flex-col gap-0.5 leading-none">
                <span className="text-base font-bold tracking-[0.12em]">{t("common.appName")}</span>
                <span className="truncate text-[11px] text-muted-foreground">
                  <span className="font-semibold tracking-wide text-primary">
                    {t("common.company")}
                  </span>{" "}
                  {t("nav.tagline")}
                </span>
              </span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {NAV_GROUPS.map((group) => {
          const items = group.items.filter(
            (item) =>
              allowed(item) &&
              (IS_PRICING_VISIBLE || item.key !== "fuelPrices") &&
              (IS_OVERVIEW_VISIBLE || item.key !== "overview")
          )
          if (items.length === 0) return null
          return (
            <SidebarGroup key={group.key}>
              <SidebarGroupLabel>{t(`nav.groups.${group.key}`)}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {items.map((item) => (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton
                        isActive={isCurrent(pathname, item.href)}
                        tooltip={t(`nav.${item.key}`)}
                        render={<Link href={item.href} />}
                      >
                        <HugeiconsIcon icon={item.icon} />
                        <span>{t(`nav.${item.key}`)}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )
        })}
      </SidebarContent>
      <SidebarFooter>{footer}</SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
