<script lang="ts">
  import type { QrScanEvent } from '$lib/api';

  interface Props {
    event: QrScanEvent;
    pendingCount?: number;
    onDismiss: () => void;
    onOpen: () => void;
  }

  let { event, pendingCount = 0, onDismiss, onOpen }: Props = $props();

  const scannedAt = $derived(
    new Intl.DateTimeFormat(undefined, { timeStyle: 'short' }).format(new Date(event.created_at))
  );
</script>

<aside class="scan-notification" aria-live="polite" aria-label="QR scan notification">
  <button
    type="button"
    class="scan-notification-close"
    aria-label="Dismiss QR scan notification"
    title="Dismiss"
    onclick={onDismiss}
  >
    x
  </button>
  <p class="scan-notification-label">Scanned on another device</p>
  <strong>{event.asset_name}</strong>
  <p class="scan-notification-meta">
    {scannedAt}{pendingCount ? ` | ${pendingCount} more waiting` : ''}
  </p>
  <button type="button" class="scan-notification-action" onclick={onOpen}>Open item</button>
</aside>

<style>
  .scan-notification {
    position: fixed;
    top: 0.75rem;
    right: 0.75rem;
    z-index: 25;
    display: grid;
    gap: 0.35rem;
    width: min(23rem, calc(100vw - 1.5rem));
    border: 1px solid #b7c8ba;
    border-left: 4px solid #347350;
    border-radius: 8px;
    padding: 0.8rem 2.5rem 0.8rem 0.9rem;
    color: #1f3328;
    background: #f7fbf5;
    box-shadow: 0 10px 32px rgba(20, 33, 28, 0.2);
  }

  .scan-notification p,
  .scan-notification strong {
    margin: 0;
  }

  .scan-notification-label {
    color: #526358;
    font-size: 0.78rem;
    font-weight: 750;
  }

  .scan-notification-meta {
    color: #607066;
    font-size: 0.78rem;
  }

  .scan-notification-close {
    position: absolute;
    top: 0.45rem;
    right: 0.45rem;
    display: grid;
    place-items: center;
    width: 1.65rem;
    min-width: 1.65rem;
    height: 1.65rem;
    min-height: 1.65rem;
    border-radius: 999px;
    padding: 0;
    color: #254c37;
    background: transparent;
    font-size: 0.9rem;
    line-height: 1;
  }

  .scan-notification-action {
    justify-self: start;
    margin-top: 0.15rem;
    width: auto;
    min-height: auto;
    border: 0;
    border-radius: 0;
    padding: 0;
    color: #245f3b;
    background: transparent;
    font-weight: 800;
    text-decoration: underline;
    cursor: pointer;
  }

  @media (max-width: 34rem) {
    .scan-notification {
      top: 0.5rem;
      right: 0.5rem;
      width: calc(100vw - 1rem);
    }
  }
</style>
