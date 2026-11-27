"use client"

import { useContracts } from "@workspace/core/contracts"
import { usePaging } from "@workspace/core/lib/paging"
import { usePartner } from "@workspace/core/partners"
import { useTranslation } from "@workspace/i18n"

import { ListStates } from "@/components/design-system/list-states"
import { PageBody, PageHeader } from "@/components/design-system/page-header"
import { ListPagination } from "@/components/design-system/pagination"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ContractTable } from "@/features/contracts/components/contract-table"

import { PartnerInfo } from "./partner-info"
import { PartnerRoleBadges } from "./partner-list"

export function PartnerDetail({ partnerId }: { partnerId: string }) {
  const { t } = useTranslation()
  const { data: partner, isPending } = usePartner(partnerId)
  const contractPaging = usePaging()
  const contracts = useContracts({
    partnerId,
    page: contractPaging.page,
    pageSize: contractPaging.pageSize,
  })

  if (isPending || !partner) {
    return (
      <PageBody>
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-40 w-full" />
      </PageBody>
    )
  }
  return (
    <>
      <PageHeader
        parents={[{ href: "/partners", label: t("nav.partners") }]}
        title={partner.name}
        description={partner.code}
        meta={<PartnerRoleBadges partner={partner} />}
      />
      <PageBody>
        <Card>
          <CardContent>
            <PartnerInfo partner={partner} />
          </CardContent>
        </Card>
        <Tabs defaultValue="contracts">
          <TabsList>
            <TabsTrigger value="contracts">
              {t("partners.contracts")} ({contracts.data?.total ?? "…"})
            </TabsTrigger>
          </TabsList>
          <TabsContent value="contracts" className="pt-2">
            <ListStates
              isPending={contracts.isPending}
              isError={contracts.isError}
              isEmpty={false}
              onRetry={() => void contracts.refetch()}
            >
              <ContractTable
                contracts={contracts.data?.items ?? []}
                footer={
                  <ListPagination total={contracts.data?.total ?? 0} paging={contractPaging} />
                }
              />
            </ListStates>
          </TabsContent>
        </Tabs>
      </PageBody>
    </>
  )
}
