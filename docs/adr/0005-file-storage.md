# 0005. Contract files live in S3-compatible object storage

Status: Accepted · Date: 2026-11-25

## Context

Signed contracts and addenda (about 2,000 PDFs at start, mostly scans) are the legal record. They
must never change after upload, must not live in Postgres, and the company self-hosts its
infrastructure (RustFS today).

## Decision

- Files are stored in an S3-compatible bucket behind the `ObjectStorage` protocol
  (`apps/api/src/app/core/storage.py`). Development and tests run RustFS from `docker-compose.yml`,
  so every environment speaks the same protocol.
- A file is addressed by the SHA-256 of its bytes (`sha256/<hex>`). The same bytes are stored once;
  re-importing a folder is a no-op for files already stored.
- Stored objects are never overwritten or deleted by the application. A wrong upload is
  detached from its record, not removed from the bucket.
- Clients never get bucket credentials: they download through short-lived presigned URLs issued by
  the API after a permission check.

## Consequences

- Switching provider (AWS S3, MinIO, another RustFS) is configuration only.
- The bucket needs its own backup policy; the database only holds metadata and hashes.
