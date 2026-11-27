# 0007. Contract facts are kept to manage the contract; the signed file is the proof

Status: Accepted · Date: 2026-11-25 (revised the same day)

## Context

The first design treated every typed fact as evidence: each value cited a page, recorded how it was
obtained, and a contract counted only once a person published it. In use, this made entry slow
while adding nothing: the signed scan stored next to the contract is already the proof, and the
business uses the typed facts only to manage, find and be reminded of contracts.

## Decision

- Facts of contracts and addenda (number, dates, renewal, value, payment, scope, adjustments) are
  plain values entered by a person; an empty value clears the field. Each change keeps the
  previous value (superseded, with who entered it and when) as history.
- The signed file is attached to every document; when in doubt, people read the file.
- There is no publish step. A contract gets its code when it is created and counts as soon as its
  main document is settled (approved if Spider drafted it, and signed by both parties) and has an
  effective date. An addendum counts once settled the same way.
- OCR/AI may later propose values; a person still saves them.

## Consequences

- Entering a fact is one inline edit, with no page, quote or correction reason.
- Status, end date and notice date are derived from the facts and stored on the contract for
  filtering; they are refreshed after each change and nightly.
