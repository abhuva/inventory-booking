<script lang="ts">
  import type { Asset, AssetUpdate, Category } from '$lib/api';
  import AssetPhotoPanel from './AssetPhotoPanel.svelte';

  let {
    asset,
    assetEditForm = $bindable(),
    categories,
    imageUrl,
    busy,
    onUpdate,
    onMove,
    onReserve,
    onUploadImage,
    onDeleteImage
  }: {
    asset: Asset;
    assetEditForm: AssetUpdate;
    categories: Category[];
    imageUrl: string | null;
    busy: boolean;
    onUpdate: () => void;
    onMove: () => void;
    onReserve: () => void;
    onUploadImage: (file: File) => void;
    onDeleteImage: () => void;
  } = $props();
</script>

<form
  class="asset-edit-form detail-tab-panel"
  onsubmit={(event) => {
    event.preventDefault();
    onUpdate();
  }}
>
  <div class="asset-info-layout">
    <AssetPhotoPanel
      assetName={asset.name}
      {imageUrl}
      {busy}
      onUpload={onUploadImage}
      onDelete={onDeleteImage}
    />

    <label class="description-field" aria-label="Description">
      <textarea
        bind:value={assetEditForm.description}
        placeholder="What is this item, what makes it recognizable, and what should people know first?"
      ></textarea>
    </label>
  </div>

  <label class="compact-field-row">Name <input bind:value={assetEditForm.name} required /></label>
  <label class="compact-field-row">
    Mode
    <input value={asset.asset_type.replaceAll('_', ' ')} disabled />
  </label>
  <label class="compact-field-row">
    Unit
    <input value={asset.unit_name ?? 'single unit'} disabled />
  </label>
  <label class="compact-field-row">
    Category
    <select bind:value={assetEditForm.category_id}>
      <option value={null}>No category</option>
      {#each categories as category}
        <option value={category.id}>{category.name}</option>
      {/each}
    </select>
  </label>
  <div class="button-row compact-button-row">
    <button type="submit" class="compact" disabled={busy}>Update info</button>
    <button type="button" class="secondary compact" disabled={busy} onclick={onMove}>
      {asset.asset_type === 'stock' ? 'Move' : 'Move tracked item'}
    </button>
    <button type="button" class="secondary compact" disabled={busy} onclick={onReserve}>
      Add to basket
    </button>
  </div>
</form>
