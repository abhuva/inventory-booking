<script lang="ts">
  import type {
    Asset,
    Location,
    LocationCreate,
    StockLevel,
    StockLevelCreate,
    StockTransfer,
    TrackedAssetTransfer
  } from '$lib/api';

  let {
    locationTypes,
    locations,
    stockAssets,
    trackedAssets,
    stockLevels,
    selectedLocationId,
    busy,
    locationForm = $bindable(),
    stockForm = $bindable(),
    trackedTransferForm = $bindable(),
    stockTransferForm = $bindable(),
    createLocation,
    createStockLevel,
    transferTrackedAssetAction,
    transferStockAction,
    selectLocation,
    closeLocationDetail,
    selectedLocation,
    stockLevelsAtLocation,
    trackedAssetsAtLocation,
    totalStockAtLocation,
    responsibleLabel,
    stockAssetName,
    stockLocationName,
    selectAssetDetail
  }: {
    locationTypes: string[];
    locations: Location[];
    stockAssets: Asset[];
    trackedAssets: Asset[];
    stockLevels: StockLevel[];
    selectedLocationId: string;
    busy: boolean;
    locationForm: LocationCreate;
    stockForm: StockLevelCreate;
    trackedTransferForm: TrackedAssetTransfer & { asset_id: string };
    stockTransferForm: StockTransfer;
    createLocation: () => void;
    createStockLevel: () => void;
    transferTrackedAssetAction: () => void;
    transferStockAction: () => void;
    selectLocation: (locationId: string) => void;
    closeLocationDetail: () => void;
    selectedLocation: () => Location | undefined;
    stockLevelsAtLocation: (locationId: string) => StockLevel[];
    trackedAssetsAtLocation: (locationId: string) => Asset[];
    totalStockAtLocation: (locationId: string) => number;
    responsibleLabel: (id: string | null) => string;
    stockAssetName: (id: string) => string;
    stockLocationName: (id: string) => string;
    selectAssetDetail: (assetId: string) => void;
  } = $props();
</script>

<section class="forms-grid" aria-label="Location and stock controls">
  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      createLocation();
    }}
  >
    <h2>Location</h2>
    <label>Name <input bind:value={locationForm.name} required /></label>
    <label>
      Type
      <select bind:value={locationForm.type}>
        {#each locationTypes as type}
          <option value={type}>{type.replaceAll('_', ' ')}</option>
        {/each}
      </select>
    </label>
    <button type="submit" disabled={busy}>Create location</button>
  </form>

  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      createStockLevel();
    }}
  >
    <h2>Stock level</h2>
    <label>
      Stock asset
      <select bind:value={stockForm.asset_id} required>
        <option value="">Choose stock</option>
        {#each stockAssets as asset}
          <option value={asset.id}>{asset.name}</option>
        {/each}
      </select>
    </label>
    <label>
      Location
      <select bind:value={stockForm.location_id} required>
        <option value="">Choose location</option>
        {#each locations as location}
          <option value={location.id}>{location.name}</option>
        {/each}
      </select>
    </label>
    <label
      >Total quantity <input bind:value={stockForm.quantity_total} type="number" min="0" /></label
    >
    <button type="submit" disabled={busy}>Set stock level</button>
  </form>

  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      transferTrackedAssetAction();
    }}
  >
    <h2>Move tracked item</h2>
    <label>
      Asset
      <select bind:value={trackedTransferForm.asset_id} required>
        <option value="">Choose tracked asset</option>
        {#each trackedAssets as asset}
          <option value={asset.id}>{asset.name}</option>
        {/each}
      </select>
    </label>
    <label>
      Destination
      <select bind:value={trackedTransferForm.to_location_id}>
        <option value="">No location</option>
        {#each locations as location}
          <option value={location.id}>{location.name}</option>
        {/each}
      </select>
    </label>
    <label>Notes <textarea bind:value={trackedTransferForm.notes}></textarea></label>
    <button type="submit" disabled={busy}>Move tracked item</button>
  </form>

  <form
    class="panel form-panel wide"
    onsubmit={(event) => {
      event.preventDefault();
      transferStockAction();
    }}
  >
    <h2>Move stock</h2>
    <div class="split-fields">
      <label>
        Stock asset
        <select bind:value={stockTransferForm.asset_id} required>
          <option value="">Choose stock</option>
          {#each stockAssets as asset}
            <option value={asset.id}>{asset.name}</option>
          {/each}
        </select>
      </label>
      <label>
        Quantity
        <input bind:value={stockTransferForm.quantity} type="number" min="1" required />
      </label>
    </div>
    <div class="split-fields">
      <label>
        From
        <select bind:value={stockTransferForm.from_location_id} required>
          <option value="">Source location</option>
          {#each locations as location}
            <option value={location.id}>{location.name}</option>
          {/each}
        </select>
      </label>
      <label>
        To
        <select bind:value={stockTransferForm.to_location_id} required>
          <option value="">Destination location</option>
          {#each locations as location}
            <option value={location.id}>{location.name}</option>
          {/each}
        </select>
      </label>
    </div>
    <label>Notes <textarea bind:value={stockTransferForm.notes}></textarea></label>
    <button type="submit" disabled={busy}>Move stock</button>
  </form>
</section>

{#if selectedLocation()}
  <section class="panel detail-panel" aria-label="Selected location detail">
    <div class="detail-header">
      <div>
        <p class="eyebrow">Location detail</p>
        <h2>{selectedLocation()?.name}</h2>
      </div>
      <button type="button" class="secondary" onclick={closeLocationDetail}>Close detail</button>
    </div>

    <div class="detail-grid">
      <div>
        <span>Type</span>
        <strong>{selectedLocation()?.type.replaceAll('_', ' ')}</strong>
      </div>
      <div>
        <span>Tracked items</span>
        <strong>{trackedAssetsAtLocation(selectedLocationId).length}</strong>
      </div>
      <div>
        <span>Stock lines</span>
        <strong>{stockLevelsAtLocation(selectedLocationId).length}</strong>
      </div>
      <div>
        <span>Total stock units</span>
        <strong>{totalStockAtLocation(selectedLocationId)}</strong>
      </div>
      <div>
        <span>Responsible</span>
        <strong>{responsibleLabel(selectedLocation()?.responsible_user_id ?? null)}</strong>
      </div>
      <div>
        <span>State</span>
        <strong>{selectedLocation()?.is_active ? 'active' : 'inactive'}</strong>
      </div>
    </div>

    <div class="split-detail">
      <article class="mini-list">
        <h3>Stock at this location</h3>
        {#each stockLevelsAtLocation(selectedLocationId) as level}
          <div class="row-card">
            <strong>{stockAssetName(level.asset_id)}</strong>
            <span>
              {level.quantity_total} total · {level.quantity_reserved} reserved · {level.quantity_checked_out}
              checked out
            </span>
          </div>
        {:else}
          <p class="empty">No stock is stored here.</p>
        {/each}
      </article>

      <article class="mini-list">
        <h3>Tracked items here</h3>
        {#each trackedAssetsAtLocation(selectedLocationId) as asset}
          <div class="row-card">
            <strong>{asset.name}</strong>
            <span>{asset.status} · {asset.condition}</span>
            <button
              type="button"
              class="secondary compact"
              onclick={() => selectAssetDetail(asset.id)}
              disabled={busy}
            >
              View asset
            </button>
          </div>
        {:else}
          <p class="empty">No tracked items are currently here.</p>
        {/each}
      </article>
    </div>
  </section>
{/if}

<section class="data-grid" aria-label="Location and stock lists">
  <article class="panel list-panel">
    <h2>Stock levels</h2>
    {#each stockLevels as level}
      <div class="row-card">
        <strong>{stockAssetName(level.asset_id)}</strong>
        <span>{stockLocationName(level.location_id)} · {level.quantity_total} total</span>
      </div>
    {:else}
      <p class="empty">No stock levels yet.</p>
    {/each}
  </article>

  <article class="panel list-panel">
    <h2>Locations</h2>
    {#each locations as location}
      <div class="row-card">
        <strong>{location.name}</strong>
        <span>
          {location.type.replaceAll('_', ' ')} · {trackedAssetsAtLocation(location.id).length}
          tracked · {totalStockAtLocation(location.id)} stock units
        </span>
        <button type="button" class="secondary compact" onclick={() => selectLocation(location.id)}>
          View detail
        </button>
      </div>
    {:else}
      <p class="empty">No locations yet.</p>
    {/each}
  </article>
</section>
