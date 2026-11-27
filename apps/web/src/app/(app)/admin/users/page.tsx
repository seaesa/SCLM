import type { Metadata } from "next"

import { UserList } from "@/features/users/components/user-list"
import { getServerT } from "@/lib/i18n-server"

export async function generateMetadata(): Promise<Metadata> {
  const t = await getServerT()
  return { title: t("users.title") }
}

export default function UsersPage() {
  return <UserList />
}
