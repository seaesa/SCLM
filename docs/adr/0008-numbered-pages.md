# 0008. Lists are paginated by page number

Status: Accepted · Date: 2026-11-25

## Context

The template paginated every list with an opaque cursor and a "Load more" button. Contract staff
work through bounded registers (about 2,000 partners, 1,000 dossiers, a few thousand contracts):
they want to see how many rows match a filter, jump to page 7, and choose 20, 50 or 100 rows. A
cursor cannot say how many rows there are or open a page in the middle.

## Decision

- Business lists take `page` (from 1) and `pageSize` (1–100) through `PageParams` and answer
  `Page[T]` = `{ items, total, page, pageSize }`. The repository runs one count and one
  `OFFSET … LIMIT` query with a total order (a unique column last), through
  `BaseRepository.page`.
- Every column a list filters or sorts by is indexed, as before.
- Cursor pagination stays for append-only feeds that can grow without bound and are read from the
  newest end (partner sync conflicts). A new list uses numbered pages unless it is such a feed.

## Consequences

- Screens show the total and page links; a filter that matches nothing says so at once.
- A row inserted while someone reads can shift the next page by one row. Acceptable for registers
  that change a few times a day.
- Offset grows linearly; at these sizes it stays well under a millisecond. Revisit if a list
  passes ~100,000 rows.
