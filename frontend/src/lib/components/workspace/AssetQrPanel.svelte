<script lang="ts">
  import type { QrCode } from '$lib/api';

  let {
    assetName,
    qrCode,
    qrSvg,
    qrError,
    busy,
    onGenerateQr,
    onDownloadQr
  }: {
    assetName: string;
    qrCode: QrCode | undefined;
    qrSvg: string;
    qrError: string;
    busy: boolean;
    onGenerateQr: () => void;
    onDownloadQr: () => void;
  } = $props();
</script>

<div class="detail-tab-panel qr-panel">
  <div class="qr-preview">
    {#if qrCode && qrSvg}
      {@html qrSvg}
    {:else}
      <div class="asset-photo-placeholder qr-placeholder">
        <strong>No QR code</strong>
        <span>Generate a QR code for this asset.</span>
      </div>
    {/if}
  </div>

  <div class="qr-detail-copy">
    <h3>{assetName}</h3>
    {#if qrCode}
      <p class="field-note">Scanning this QR will open this asset once scan routing exists.</p>
    {:else}
      <p class="field-note">
        No QR code exists for this asset yet. Generate one and download the SVG for printing.
      </p>
    {/if}
    {#if qrError}
      <p class="notice error">{qrError}</p>
    {/if}
  </div>

  <div class="button-row compact-button-row">
    <button type="button" class="compact" disabled={busy || Boolean(qrCode)} onclick={onGenerateQr}>
      Generate QR code
    </button>
    <button
      type="button"
      class="secondary compact"
      disabled={!qrCode || !qrSvg}
      onclick={onDownloadQr}
    >
      Download SVG
    </button>
  </div>
</div>
