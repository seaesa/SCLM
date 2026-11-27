import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  getDocumentFileUrlOptions,
  getDocumentSetOptions,
  getDocumentSetQueryKey,
  uploadDocumentFileMutation,
} from "@workspace/api-client/query"

/** Presigned download links live 5 minutes on the API; refetch a little before. */
const FILE_URL_STALE_MS = 4 * 60 * 1000

/** The files kept for one contract (its dossier). */
export function useDocumentSet(setId: string) {
  return useQuery(getDocumentSetOptions({ path: { setId } }))
}

export function useDocumentFileUrl(setId: string, fileId: string | undefined) {
  return useQuery({
    ...getDocumentFileUrlOptions({ path: { setId, fileId: fileId ?? "" } }),
    enabled: fileId !== undefined,
    staleTime: FILE_URL_STALE_MS,
  })
}

export function useUploadDocumentFile(setId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    ...uploadDocumentFileMutation(),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: getDocumentSetQueryKey({ path: { setId } }) }),
  })
}
