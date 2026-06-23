<script lang="ts">
  import type { Asset, Location, LocationCreate, StockLevel } from '$lib/api';

  let showAddLocation = $state(false);

  let {
    locationTypes,
    locations,
    selectedLocationId,
    busy,
    locationForm = $bindable(),
    createLocation,
    selectLocation,
    closeLocationDetail,
    selectedLocation,
    stockLevelsAtLocation,
    trackedAssetsAtLocation,
    totalStockAtLocation,
    responsibleLabel,
    stockAssetName,
    selectAssetDetail
  }: {
    locationTypes: string[];
    locations: Location[];
    selectedLocationId: string;
    busy: boolean;
    locationForm: LocationCreate;
    createLocation: () => void;
    selectLocation: (locationId: string) => void;
    closeLocationDetail: () => void;
    selectedLocation: () => Location | undefined;
    stockLevelsAtLocation: (locationId: string) => StockLevel[];
    trackedAssetsAtLocation: (locationId: string) => Asset[];
    totalStockAtLocation: (locationId: string) => number;
    responsibleLabel: (id: string | null) => string;
    stockAssetName: (id: string) => string;
    selectAssetDetail: (assetId: string) => void;
  } = $props();

  function submitNewLocation() {
    createLocation();
    showAddLocation = false;
  }

  function locationTypeLabel(location: Location | undefined): string {
    return location ? location.type.replaceAll('_', ' ') : 'unknown';
  }
</script>

<section class="inventory-workspace" aria-label="Locations workspace">
  <section class="panel inventory-table-panel">
    <div class="inventory-toolbar">
      <div>
        <h2>Locations</h2>
        <p>{locations.length} total</p>
      </div>
      <button type="button" class="compact" onclick={() => (showAddLocation = true)}>+ Add</button>
    </div>

    <div class="asset-table-wrap">
      <table class="asset-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Tracked</th>
            <th>Stock units</th>
          </tr>
        </thead>
        <tbody>
          {#each locations as location}
            <tr
              class:selected-row={location.id === selectedLocationId}
              onclick={() => selectLocation(location.id)}
            >
              <td>
                <strong>{location.name}</strong>
                <span>{location.is_active ? 'active' : 'inactive'}</span>
              </td>
              <td>{location.type.replaceAll('_', ' ')}</td>
              <td>{trackedAssetsAtLocation(location.id).length}</td>
              <td>{totalStockAtLocation(location.id)}</td>
            </tr>
          {:else}
            <tr>
              <td colspan="4" class="empty">No locations yet.</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <aside class="panel inventory-detail-panel" aria-label="Selected location details">
    {#if selectedLocation()}
      <div class="detail-header asset-detail-header">
        <div>
          <p class="eyebrow">Location detail</p>
          <h2>{selectedLocation()?.name}</h2>
        </div>
        <button type="button" class="secondary micro-button" onclick={closeLocationDetail}
          >Close</button
        >
      </div>

      <div class="physical-summary-grid">
        <article>
          <span>Type</span>
          <strong>{locationTypeLabel(selectedLocation())}</strong>
        </article>
        <article>
          <span>Tracked items</span>
          <strong>{trackedAssetsAtLocation(selectedLocationId).length}</strong>
        </article>
        <article>
          <span>Stock units</span>
          <strong>{totalStockAtLocation(selectedLocationId)}</strong>
        </article>
        <article>
          <span>Stock lines</span>
          <strong>{stockLevelsAtLocation(selectedLocationId).length}</strong>
        </article>
        <article>
          <span>Responsible</span>
          <strong>{responsibleLabel(selectedLocation()?.responsible_user_id ?? null)}</strong>
        </article>
        <article>
          <span>State</span>
          <strong>{selectedLocation()?.is_active ? 'active' : 'inactive'}</strong>
        </article>
      </div>

      <div class="split-detail location-detail-lists">
        <article class="mini-list">
          <h3>Stock here</h3>
          {#each stockLevelsAtLocation(selectedLocationId) as level}
            <div class="row-card">
              <strong>{stockAssetName(level.asset_id)}</strong>
              <span>
                {level.quantity_total} total / {level.quantity_checked_out} checked out
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
              <span
                >{asset.status.replaceAll('_', ' ')} / {asset.condition.replaceAll('_', ' ')}</span
              >
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
    {:else}
      <div class="empty-detail">
        <h2>Select a location</h2>
        <p>Click a row in the table to view location information.</p>
      </div>
    {/if}
  </aside>
</section>

{#if showAddLocation}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label="Add location"
      onsubmit={(event) => {
        event.preventDefault();
        submitNewLocation();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">New location</p>
          <h2>Add location</h2>
        </div>
        <button type="button" class="secondary compact" onclick={() => (showAddLocation = false)}
          >Cancel</button
        >
      </div>
      <label>Name <input bind:value={locationForm.name} required /></label>
      <label>
        Type
        <select bind:value={locationForm.type}>
          {#each locationTypes as type}
            <option value={type}>{type.replaceAll('_', ' ')}</option>
          {/each}
        </select>
      </label>
      <div class="button-row">
        <button type="button" class="secondary" onclick={() => (showAddLocation = false)}
          >Cancel</button
        >
        <button type="submit" disabled={busy}>Save location</button>
      </div>
    </form>
  </div>
{/if}
