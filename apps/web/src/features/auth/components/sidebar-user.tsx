"use client"

import { MoreHorizontalIcon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"

import { useCurrentUser, useLogout } from "@workspace/core/auth"
import { useTranslation } from "@workspace/i18n"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar"
import { PreferencesMenuItems } from "@/features/preferences/components/preferences-menu"

const initials = (name = "") =>
  name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()

/** The signed-in user at the foot of the sidebar: roles, preferences and sign-out. */
export function SidebarUser() {
  const { t } = useTranslation()
  const { data: user } = useCurrentUser()
  const logout = useLogout()

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={<SidebarMenuButton size="lg" aria-label={t("profile.account")} />}
          >
            <Avatar className="size-8">
              <AvatarFallback>{initials(user?.fullName)}</AvatarFallback>
            </Avatar>
            <span className="flex min-w-0 flex-1 flex-col text-left leading-tight">
              <span className="truncate font-medium">{user?.fullName}</span>
              <span className="truncate text-xs text-muted-foreground">{user?.email}</span>
            </span>
            <HugeiconsIcon icon={MoreHorizontalIcon} className="ml-auto" />
          </DropdownMenuTrigger>
          <DropdownMenuContent side="right" align="end" className="min-w-60">
            <DropdownMenuGroup>
              <DropdownMenuLabel>
                <div className="font-medium text-foreground">{user?.fullName}</div>
                <div className="text-xs text-muted-foreground">
                  {user?.roles.map((role) => t(`roles.${role}`)).join(" · ")}
                </div>
              </DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <PreferencesMenuItems />
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => logout.mutate()}>
              {t("common.signOut")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
