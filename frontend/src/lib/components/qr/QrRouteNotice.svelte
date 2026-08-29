<script lang="ts">
  let {
    eyebrow = 'Asset lookup',
    title,
    message,
    tone = 'neutral',
    actionLabel,
    onAction
  }: {
    eyebrow?: string;
    title: string;
    message: string;
    tone?: 'neutral' | 'warning' | 'error';
    actionLabel?: string;
    onAction?: () => void;
  } = $props();
</script>

<section class="qr-route-notice qr-route-notice-{tone}" aria-live="polite">
  <p class="eyebrow">{eyebrow}</p>
  <h1>{title}</h1>
  <p>{message}</p>
  {#if actionLabel && onAction}
    <button type="button" onclick={onAction}>{actionLabel}</button>
  {/if}
</section>
