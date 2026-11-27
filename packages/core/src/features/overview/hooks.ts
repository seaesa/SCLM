import { useQuery } from "@tanstack/react-query"

import { getOverviewOptions } from "@workspace/api-client/query"

/** Dashboard figures the server computes for today; loaded again when the window regains focus. */
export function useOverview() {
  return useQuery(getOverviewOptions())
}
