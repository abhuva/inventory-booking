<script lang="ts">
  import { renderQrSvg } from '$lib/qr';
  import type { QrPdfLabel } from '$lib/qr-pdf';

  let {
    label,
    logoRadiusPercent,
    logoSizePercent
  }: { label: QrPdfLabel; logoRadiusPercent: number; logoSizePercent: number } = $props();

  let qrSvg = $state('');

  $effect(() => {
    const url = label.url;
    let active = true;
    qrSvg = '';
    renderQrSvg(url, 'H', 4)
      .then((svg) => {
        if (active) {
          qrSvg = svg;
        }
      })
      .catch(() => {
        if (active) {
          qrSvg = '';
        }
      });
    return () => {
      active = false;
    };
  });
</script>

<div class="qr-label-preview-cell">
  <div class="qr-label-preview-code">
    <div class="qr-label-preview-graphic">
      {#if qrSvg}
        {@html qrSvg}
        <span
          class="qr-label-preview-logo"
          style:width={`${logoRadiusPercent * 2}%`}
          aria-hidden="true"
        >
          <img
            src="/branding/nica-logo-black.png"
            alt=""
            style:width={`${(logoSizePercent / (logoRadiusPercent * 2)) * 100}%`}
          />
        </span>
      {/if}
    </div>
  </div>
  <strong>{label.assetName}</strong>
</div>

<style>
  .qr-label-preview-cell {
    display: grid;
    grid-template-rows: minmax(0, 1fr) auto;
    gap: 0.15rem;
    min-width: 0;
    min-height: 0;
    border: 1px solid #c8ccc5;
    padding: 4%;
    overflow: hidden;
    background: #fff;
  }

  .qr-label-preview-code {
    display: grid;
    place-items: center;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }

  .qr-label-preview-graphic {
    position: relative;
    display: grid;
    place-items: center;
    max-width: 100%;
    max-height: 100%;
    aspect-ratio: 1;
  }

  .qr-label-preview-graphic :global(svg) {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
  }

  .qr-label-preview-logo {
    position: absolute;
    inset: 50% auto auto 50%;
    display: grid;
    place-items: center;
    aspect-ratio: 1;
    background: #fff;
    border-radius: 50%;
    transform: translate(-50%, -50%);
  }

  .qr-label-preview-logo img {
    display: block;
    max-width: none;
    height: auto;
  }

  strong {
    overflow: hidden;
    font-size: clamp(0.34rem, 1.15cqw, 0.72rem);
    line-height: 1.1;
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
