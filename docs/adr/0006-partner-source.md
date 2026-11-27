# 0006. Partners are synchronized from an external source of record

Status: Accepted · Date: 2026-11-25

## Context

Customers and suppliers are mastered in MISA (accounting). The MISA connection is not available
yet; today the catalogue is a set of JSON exports. Contracts must not break when the source
changes, and the same company can be both customer and supplier.

## Decision

- The `partners` module reads the catalogue through a `PartnerSource` protocol. The first
  implementation reads the JSON exports; a MISA implementation will replace it without touching
  contracts.
- A partner has one internal id and one or more roles (customer, supplier). A code present in both
  customer and supplier exports is one partner with both roles.
- Source identifiers are kept in `partner_external_refs` (source, external code). Contracts
  reference the internal id only.
- Synchronization never merges two partners on its own: each source code stays its own partner,
  and a tax code shared by several partners is recorded as a conflict for an administrator to
  resolve (or acknowledge, e.g. two branches). The CLM does not create
  partners outside synchronization.

## Consequences

- Moving to MISA is a new `PartnerSource` plus a one-off mapping of external codes.
- Data quality issues in the source (missing tax codes, mixed roles) surface as conflicts instead
  of silent merges, and must be fixed in the source.
