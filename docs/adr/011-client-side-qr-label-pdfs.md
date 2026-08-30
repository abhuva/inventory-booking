# ADR 011: Generate QR Label PDFs In The Browser

**Status**: Accepted | **Date**: 2026-08-30 |
**Participants**: Marc Bielert, implementation contributors

## Context

Users need to select assigned inventory QR codes, choose a copy count for each,
arrange the labels in a configurable grid, and download an A4 PDF for adhesive
paper. The QR destinations and asset names are already present in the
authenticated workspace response.

Alternatives considered were:

- browser print styles, which provide a preview but leave pagination, margins,
  and output consistency to each browser and print dialog;
- a backend PDF endpoint, which centralizes rendering but adds an API contract,
  server-side PDF dependencies, and temporary document processing for data the
  browser already has;
- deterministic client-side generation from the loaded QR assignments.

## Decision

We decided to generate the PDF in the browser with `pdf-lib` and the existing
`qrcode` dependency. The frontend validates the requested columns and rows,
uses fixed print-safe margins and gaps, and draws QR modules as vector
rectangles on portrait A4 pages. PDF generation is an explicit user action and
the document is downloaded without being uploaded or persisted.

The first version includes the asset name beneath each code and supports only
assigned QR codes. A monochrome NICA logo is centered over a white circle; the
circle radius and logo size are independently configurable. Branded codes use
the QR standard's high error-correction level. Reusable label templates remain
separate future work.

## Consequences

- (+) The downloaded document has deterministic A4 dimensions and pagination.
- (+) Vector QR modules remain sharp when labels are scaled or printed.
- (+) No new backend endpoint, stored document, or production service dependency
  is required.
- (+) Inventory and QR data remain within the authenticated browser session.
- (-) Large selections consume browser CPU and memory while the PDF is built.
- (-) Standard PDF fonts limit the initial label text character set.
- (-) Shared templates and centrally controlled branding will require a later
  extension.
