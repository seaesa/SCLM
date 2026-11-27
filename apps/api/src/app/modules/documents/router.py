import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path, UploadFile, status

from app.modules.auth.dependencies import require_permission
from app.modules.documents.schemas import (
    DocumentFileRead,
    DocumentSetDetail,
    DownloadUrl,
)
from app.modules.documents.service import DocumentService
from app.modules.users.models import User
from app.shared.permissions import Permission

SetId = Annotated[uuid.UUID, Path(alias="setId")]
FileId = Annotated[uuid.UUID, Path(alias="fileId")]
CanRead = Annotated[User, require_permission(Permission.CONTRACTS_READ)]
CanRegister = Annotated[User, require_permission(Permission.CONTRACTS_REGISTER)]
CanDownload = Annotated[User, require_permission(Permission.CONTRACT_FILES_DOWNLOAD)]

router = APIRouter(prefix="/document-sets", tags=["documents"], route_class=DishkaRoute)


@router.get("/{setId}")
async def get_document_set(
    set_id: SetId, _: CanRead, service: FromDishka[DocumentService]
) -> DocumentSetDetail:
    return await service.get(set_id)


@router.get("/{setId}/files/{fileId}/download-url")
async def get_document_file_url(
    set_id: SetId, file_id: FileId, _: CanDownload, service: FromDishka[DocumentService]
) -> DownloadUrl:
    return await service.download_url(set_id, file_id)


@router.post("/{setId}/files", status_code=status.HTTP_201_CREATED)
async def upload_document_file(
    set_id: SetId, file: UploadFile, _: CanRegister, service: FromDishka[DocumentService]
) -> DocumentFileRead:
    data = await file.read()
    return await service.add_file(set_id, file.filename or "upload.pdf", data)
