<script lang="ts">
  import type { Asset, AssetUpdate } from '$lib/api';

  let {
    asset,
    assetEditForm = $bindable(),
    busy,
    onUpdate
  }: {
    asset: Asset;
    assetEditForm: AssetUpdate;
    busy: boolean;
    onUpdate: () => void;
  } = $props();
</script>

<form
  class="asset-edit-form detail-tab-panel"
  onsubmit={(event) => {
    event.preventDefault();
    onUpdate();
  }}
>
  <div class="split-fields">
    <label>Manufacturer <input bind:value={assetEditForm.manufacturer} /></label>
    <label>Model <input bind:value={assetEditForm.model} /></label>
  </div>
  <div class="split-fields">
    <label>Replacement value <input bind:value={assetEditForm.replacement_value} /></label>
    <label>Definition type <input value={asset.asset_type} disabled /></label>
  </div>
  <label>
    Internal notes
    <textarea
      bind:value={assetEditForm.notes}
      placeholder="Operational notes, quirks, repair context, or admin-only reminders."
    ></textarea>
  </label>
  <button type="submit" class="compact" disabled={busy}>Update extra</button>
</form>
