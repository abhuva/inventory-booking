<script lang="ts">
  let {
    assetName,
    imageUrl,
    busy,
    onUpload,
    onDelete
  }: {
    assetName: string;
    imageUrl: string | null;
    busy: boolean;
    onUpload: (file: File) => void;
    onDelete: () => void;
  } = $props();

  let photoInput = $state<HTMLInputElement>();

  function handlePhotoChange(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    onUpload(file);
    input.value = '';
  }
</script>

<div class="asset-photo-panel compact-photo-panel">
  {#if imageUrl}
    <img src={imageUrl} alt={`Photo of ${assetName}`} class="asset-photo" />
  {:else}
    <div class="asset-photo-placeholder">
      <strong>No photo</strong>
      <span>Add a square reference photo.</span>
    </div>
  {/if}
  <div class="asset-photo-actions">
    <input
      bind:this={photoInput}
      class="visually-hidden"
      type="file"
      accept="image/png,image/jpeg,image/webp"
      capture="environment"
      onchange={handlePhotoChange}
    />
    <button type="button" class="micro-button" disabled={busy} onclick={() => photoInput?.click()}>
      {imageUrl ? 'Replace' : 'Add photo'}
    </button>
    {#if imageUrl}
      <button type="button" class="secondary micro-button" disabled={busy} onclick={onDelete}>
        Delete
      </button>
    {/if}
  </div>
</div>
