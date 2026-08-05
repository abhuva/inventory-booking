<script lang="ts">
  import type { Asset, AssetCondition, AssetStatus, AssetUpdate, Location, User } from '$lib/api';

  let {
    asset,
    assetEditForm = $bindable(),
    assetStatuses,
    assetConditions,
    locations,
    availableHolderUsers,
    busy,
    locationName,
    holderLabel,
    onUpdate
  }: {
    asset: Asset;
    assetEditForm: AssetUpdate;
    assetStatuses: AssetStatus[];
    assetConditions: AssetCondition[];
    locations: Location[];
    availableHolderUsers: User[];
    busy: boolean;
    locationName: (id: string | null) => string;
    holderLabel: (id: string | null) => string;
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
  <div class="physical-summary-grid">
    <article>
      <span>Status</span>
      <strong>{asset.status.replaceAll('_', ' ')}</strong>
    </article>
    <article>
      <span>Condition</span>
      <strong>{asset.condition.replaceAll('_', ' ')}</strong>
    </article>
    <article>
      <span>Location</span>
      <strong>{locationName(asset.current_location_id)}</strong>
    </article>
    <article>
      <span>Holder</span>
      <strong>{holderLabel(asset.current_holder_user_id)}</strong>
    </article>
  </div>

  <div class="split-fields">
    <label>
      Status
      <select bind:value={assetEditForm.status}>
        {#each assetStatuses as status}
          <option value={status}>{status.replaceAll('_', ' ')}</option>
        {/each}
      </select>
    </label>
    <label>
      Condition
      <select bind:value={assetEditForm.condition}>
        {#each assetConditions as condition}
          <option value={condition}>{condition.replaceAll('_', ' ')}</option>
        {/each}
      </select>
    </label>
  </div>
  <label>
    Current location
    <select bind:value={assetEditForm.current_location_id}>
      <option value={null}>No location</option>
      {#each locations as location}
        <option value={location.id}>{location.name}</option>
      {/each}
    </select>
  </label>
  <label>
    Holder
    <select bind:value={assetEditForm.current_holder_user_id}>
      <option value={null}>No holder</option>
      {#each availableHolderUsers as user}
        <option value={user.id}>{user.display_name}</option>
      {/each}
    </select>
  </label>
  <div class="split-fields">
    <label>Serial <input bind:value={assetEditForm.serial_number} /></label>
    <label>Asset tag <input bind:value={assetEditForm.asset_tag} /></label>
  </div>
  <button type="submit" class="compact" disabled={busy}>Update unit</button>
</form>
