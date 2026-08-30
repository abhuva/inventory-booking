<script lang="ts">
  import type { Asset, QrCode } from '$lib/api';
  import QrLabelPreviewCell from './QrLabelPreviewCell.svelte';
  import {
    DEFAULT_QR_LOGO_RADIUS_PERCENT,
    DEFAULT_QR_LOGO_SIZE_PERCENT,
    MAX_QR_LOGO_RADIUS_PERCENT,
    MAX_QR_LOGO_SIZE_PERCENT,
    MIN_QR_LOGO_RADIUS_PERCENT,
    MIN_QR_LOGO_SIZE_PERCENT,
    VERIFIED_QR_LOGO_RADIUS_PERCENT,
    calculateQrPdfLayout,
    createQrLabelPdf,
    downloadQrLabelPdf,
    type QrPdfLabel
  } from '$lib/qr-pdf';

  interface LabelRow {
    asset: Asset;
    qrCode: QrCode;
  }

  let {
    assets,
    qrCodes,
    qrScanUrl
  }: {
    assets: Asset[];
    qrCodes: QrCode[];
    qrScanUrl: (token: string) => string;
  } = $props();

  let search = $state('');
  let copies = $state<Record<string, number>>({});
  let columns = $state(4);
  let rows = $state(6);
  let logoRadiusPercent = $state(DEFAULT_QR_LOGO_RADIUS_PERCENT);
  let logoSizePercent = $state(DEFAULT_QR_LOGO_SIZE_PERCENT);
  let generating = $state(false);
  let pdfError = $state('');

  const labelRows = $derived.by(() =>
    qrCodes
      .flatMap((qrCode): LabelRow[] => {
        const asset = assets.find((entry) => entry.id === qrCode.asset_id);
        return asset ? [{ asset, qrCode }] : [];
      })
      .sort((left, right) => left.asset.name.localeCompare(right.asset.name))
  );
  const filteredRows = $derived(
    labelRows.filter((row) => {
      const query = search.trim().toLocaleLowerCase();
      return (
        !query ||
        row.asset.name.toLocaleLowerCase().includes(query) ||
        row.asset.asset_type.toLocaleLowerCase().includes(query) ||
        (row.qrCode.label ?? '').toLocaleLowerCase().includes(query)
      );
    })
  );
  const selectedAssetCount = $derived(
    labelRows.filter((row) => (copies[row.qrCode.id] ?? 0) > 0).length
  );
  const selectedLabels = $derived.by(() =>
    labelRows.flatMap((row): QrPdfLabel[] => {
      const count = copies[row.qrCode.id] ?? 0;
      return Array.from({ length: count }, () => ({
        assetId: row.asset.id,
        assetName: row.asset.name,
        url: qrScanUrl(row.qrCode.token)
      }));
    })
  );
  const layoutResult = $derived.by(() => {
    try {
      return { layout: calculateQrPdfLayout({ columns, rows }), error: '' };
    } catch (caught) {
      return {
        layout: null,
        error: caught instanceof Error ? caught.message : 'Invalid label grid.'
      };
    }
  });
  const pageCount = $derived(
    layoutResult.layout ? Math.ceil(selectedLabels.length / layoutResult.layout.labelsPerPage) : 0
  );
  const firstPageLabels = $derived(
    layoutResult.layout
      ? selectedLabels.slice(0, layoutResult.layout.labelsPerPage)
      : ([] as QrPdfLabel[])
  );
  const previewColumns = $derived(Number.isInteger(columns) && columns > 0 ? columns : 1);
  const previewRows = $derived(Number.isInteger(rows) && rows > 0 ? rows : 1);

  function setCopyCount(qrCodeId: string, value: number): void {
    copies[qrCodeId] = Number.isFinite(value) ? Math.max(0, Math.min(99, Math.floor(value))) : 0;
    pdfError = '';
  }

  function selectVisible(): void {
    filteredRows.forEach((row) => {
      if ((copies[row.qrCode.id] ?? 0) === 0) {
        copies[row.qrCode.id] = 1;
      }
    });
  }

  function clearSelection(): void {
    copies = {};
    pdfError = '';
  }

  async function downloadPdf(): Promise<void> {
    generating = true;
    pdfError = '';
    try {
      const bytes = await createQrLabelPdf(
        selectedLabels,
        { columns, rows },
        { logoRadiusPercent, logoSizePercent }
      );
      downloadQrLabelPdf(bytes);
    } catch (caught) {
      pdfError = caught instanceof Error ? caught.message : 'Could not generate the PDF.';
    } finally {
      generating = false;
    }
  }
</script>

<section class="qr-labels-workspace" aria-label="QR label sheets">
  <section class="panel qr-label-selection-panel">
    <div class="inventory-toolbar qr-label-toolbar">
      <div>
        <h2>QR labels</h2>
        <p>{labelRows.length} assigned {labelRows.length === 1 ? 'code' : 'codes'}</p>
      </div>
      <div class="qr-label-toolbar-actions">
        <input bind:value={search} aria-label="Search QR labels" placeholder="Search assets" />
        <button type="button" class="secondary compact" onclick={selectVisible}>1 each</button>
        <button type="button" class="secondary compact" onclick={clearSelection}>Clear</button>
      </div>
    </div>

    <div class="asset-table-wrap qr-label-table-wrap">
      <table class="asset-table qr-label-table">
        <thead>
          <tr>
            <th scope="col">Print</th>
            <th scope="col">Asset</th>
            <th scope="col">Type</th>
            <th scope="col">Copies</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredRows as row (row.qrCode.id)}
            <tr class:selected-row={(copies[row.qrCode.id] ?? 0) > 0}>
              <td>
                <input
                  type="checkbox"
                  aria-label={`Print ${row.asset.name}`}
                  checked={(copies[row.qrCode.id] ?? 0) > 0}
                  onchange={(event) =>
                    setCopyCount(
                      row.qrCode.id,
                      event.currentTarget.checked ? Math.max(1, copies[row.qrCode.id] ?? 0) : 0
                    )}
                />
              </td>
              <td>
                <strong>{row.asset.name}</strong>
                {#if row.qrCode.label && row.qrCode.label !== row.asset.name}
                  <span>{row.qrCode.label}</span>
                {/if}
              </td>
              <td
                ><span class="status-pill status-{row.asset.asset_type}"
                  >{row.asset.asset_type}</span
                ></td
              >
              <td>
                <input
                  class="qr-copy-input"
                  type="number"
                  min="0"
                  max="99"
                  step="1"
                  aria-label={`Copies of ${row.asset.name}`}
                  value={copies[row.qrCode.id] ?? 0}
                  oninput={(event) =>
                    setCopyCount(row.qrCode.id, event.currentTarget.valueAsNumber)}
                />
              </td>
            </tr>
          {:else}
            <tr>
              <td colspan="4" class="empty">No assigned QR codes match.</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel qr-sheet-panel">
    <div class="list-header">
      <div>
        <h2>A4 sheet</h2>
        <p>
          {selectedLabels.length} labels across {pageCount}
          {pageCount === 1 ? 'page' : 'pages'}
        </p>
      </div>
    </div>

    <div class="qr-grid-controls">
      <label>
        <span>Columns</span>
        <input type="number" min="1" max="8" step="1" bind:value={columns} />
      </label>
      <label>
        <span>Rows</span>
        <input type="number" min="1" max="8" step="1" bind:value={rows} />
      </label>
      <div class="readonly-field">
        <span>QR size</span>
        <strong
          >{layoutResult.layout ? `${layoutResult.layout.qrSizeMm.toFixed(1)} mm` : '-'}</strong
        >
      </div>
      <label class="qr-logo-radius-control">
        <div class="qr-logo-radius-heading">
          <span>Logo radius</span>
          <output>{logoRadiusPercent}%</output>
        </div>
        <input
          type="range"
          min={MIN_QR_LOGO_RADIUS_PERCENT}
          max={MAX_QR_LOGO_RADIUS_PERCENT}
          step="0.5"
          bind:value={logoRadiusPercent}
        />
        {#if logoRadiusPercent > VERIFIED_QR_LOGO_RADIUS_PERCENT}
          <small>Experimental size; the resulting codes may not scan reliably.</small>
        {/if}
      </label>
      <label class="qr-logo-size-control">
        <div class="qr-logo-radius-heading">
          <span>Logo size</span>
          <output>{logoSizePercent}%</output>
        </div>
        <input
          type="range"
          min={MIN_QR_LOGO_SIZE_PERCENT}
          max={MAX_QR_LOGO_SIZE_PERCENT}
          step="0.5"
          bind:value={logoSizePercent}
        />
        {#if logoSizePercent > logoRadiusPercent * 2.4}
          <small>The logo extends beyond the white circle.</small>
        {/if}
      </label>
    </div>

    {#if layoutResult.error || pdfError}
      <p class="notice error">{layoutResult.error || pdfError}</p>
    {/if}

    <div class="qr-sheet-preview-shell">
      <div
        class="qr-sheet-preview"
        style:grid-template-columns={`repeat(${previewColumns}, minmax(0, 1fr))`}
        style:grid-template-rows={`repeat(${previewRows}, minmax(0, 1fr))`}
        aria-label="First PDF page preview"
      >
        {#each firstPageLabels as label, index (`${label.assetId}-${index}`)}
          <QrLabelPreviewCell {label} {logoRadiusPercent} {logoSizePercent} />
        {/each}
      </div>
    </div>

    <div class="qr-sheet-footer">
      <strong>{selectedAssetCount} assets selected</strong>
      <button
        type="button"
        disabled={generating || !selectedLabels.length || !layoutResult.layout}
        onclick={() => void downloadPdf()}
      >
        {generating ? 'Generating...' : 'Download PDF'}
      </button>
    </div>
  </section>
</section>

<style>
  .qr-labels-workspace {
    display: grid;
    grid-template-columns: minmax(28rem, 1.15fr) minmax(22rem, 0.85fr);
    gap: 0.55rem;
    height: 100%;
    min-height: 0;
  }

  .qr-label-selection-panel,
  .qr-sheet-panel {
    min-width: 0;
    min-height: 0;
    padding: 0.75rem;
  }

  .qr-label-selection-panel {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
  }

  .qr-label-toolbar-actions {
    display: grid;
    grid-template-columns: minmax(10rem, 1fr) auto auto;
    gap: 0.35rem;
    width: min(100%, 27rem);
  }

  .qr-label-toolbar-actions button {
    width: auto;
  }

  .qr-label-table-wrap {
    min-height: 0;
  }

  .qr-label-table th:first-child,
  .qr-label-table td:first-child {
    width: 3.5rem;
    text-align: center;
  }

  .qr-label-table th:last-child,
  .qr-label-table td:last-child {
    width: 5.5rem;
  }

  .qr-label-table tbody tr {
    cursor: default;
  }

  .qr-label-table input[type='checkbox'] {
    width: 1rem;
    height: 1rem;
  }

  .qr-copy-input {
    width: 4.5rem;
    min-width: 0;
  }

  .qr-sheet-panel {
    display: grid;
    grid-template-rows: auto auto auto minmax(0, 1fr) auto;
    gap: 0.65rem;
    overflow: hidden;
  }

  .qr-grid-controls {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.45rem;
  }

  .qr-grid-controls label {
    display: grid;
    gap: 0.25rem;
  }

  .qr-grid-controls label span {
    color: #526358;
    font-size: 0.74rem;
    font-weight: 700;
  }

  .qr-logo-radius-control,
  .qr-logo-size-control {
    grid-column: 1 / -1;
  }

  .qr-logo-radius-heading {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }

  .qr-logo-radius-heading output {
    color: #28372f;
    font-size: 0.76rem;
    font-weight: 700;
  }

  .qr-logo-radius-control input[type='range'],
  .qr-logo-size-control input[type='range'] {
    width: 100%;
    min-height: 1.5rem;
    padding: 0;
  }

  .qr-logo-radius-control small,
  .qr-logo-size-control small {
    color: #8b2e24;
    font-size: 0.72rem;
    font-weight: 700;
  }

  .qr-sheet-preview-shell {
    display: grid;
    place-items: center;
    min-height: 0;
    padding: 0.6rem;
    overflow: auto;
    background: #dde2da;
  }

  .qr-sheet-preview {
    container-type: inline-size;
    display: grid;
    gap: 0.35%;
    width: min(100%, 31rem);
    aspect-ratio: 210 / 297;
    padding: 2.7%;
    background: #fff;
    box-shadow: 0 4px 18px rgba(20, 33, 28, 0.18);
  }

  .qr-sheet-footer {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    justify-content: space-between;
  }

  .qr-sheet-footer strong {
    color: #526358;
    font-size: 0.78rem;
  }

  .qr-sheet-footer button {
    width: auto;
  }

  @media (max-width: 960px) {
    .qr-labels-workspace {
      grid-template-columns: 1fr;
      height: auto;
      overflow: auto;
    }

    .qr-label-selection-panel {
      min-height: 26rem;
    }

    .qr-sheet-preview-shell {
      min-height: 32rem;
    }
  }

  @media (max-width: 560px) {
    .qr-label-toolbar {
      display: grid;
    }

    .qr-label-toolbar-actions,
    .qr-grid-controls {
      grid-template-columns: 1fr;
      width: 100%;
    }

    .qr-label-table th:nth-child(3),
    .qr-label-table td:nth-child(3) {
      display: none;
    }
  }
</style>
