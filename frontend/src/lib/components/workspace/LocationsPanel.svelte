<script lang="ts">
  import type {
    Asset,
    Location,
    LocationCreate,
    LocationUpdate,
    Person,
    StockLevel
  } from '$lib/api';

  let showAddLocation = $state(false);
  let activeLocationDetailTab = $state<'info' | 'extra'>('info');
  let locationPhotoInput = $state<HTMLInputElement>();

  let {
    locationTypes,
    persons,
    locations,
    selectedLocationId,
    busy,
    locationForm = $bindable(),
    locationEditForm = $bindable(),
    createLocation,
    selectLocationDetail,
    updateSelectedLocation,
    closeLocationDetail,
    selectedLocation,
    stockLevelsAtLocation,
    trackedAssetsAtLocation,
    totalStockAtLocation,
    responsibleLabel,
    stockAssetName,
    locationImageUrl,
    uploadSelectedLocationImage,
    deleteSelectedLocationImage,
    selectAssetDetail
  }: {
    locationTypes: string[];
    persons: Person[];
    locations: Location[];
    selectedLocationId: string;
    busy: boolean;
    locationForm: LocationCreate;
    locationEditForm: LocationUpdate;
    createLocation: () => void;
    selectLocationDetail: (locationId: string) => void;
    updateSelectedLocation: () => void;
    closeLocationDetail: () => void;
    selectedLocation: () => Location | undefined;
    stockLevelsAtLocation: (locationId: string) => StockLevel[];
    trackedAssetsAtLocation: (locationId: string) => Asset[];
    totalStockAtLocation: (locationId: string) => number;
    responsibleLabel: (id: string | null) => string;
    stockAssetName: (id: string) => string;
    locationImageUrl: (locationId: string) => string | null;
    uploadSelectedLocationImage: (file: File) => void;
    deleteSelectedLocationImage: () => void;
    selectAssetDetail: (assetId: string) => void;
  } = $props();

  function submitNewLocation() {
    createLocation();
    showAddLocation = false;
  }

  function locationTypeLabel(location: Location | undefined): string {
    return location ? location.type.replaceAll('_', ' ') : 'unknown';
  }

  function handleLocationPhotoChange(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    uploadSelectedLocationImage(file);
    input.value = '';
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
              onclick={() => selectLocationDetail(location.id)}
            >
              <td>
                <div class="asset-name-cell">
                  {#if locationImageUrl(location.id)}
                    <img src={locationImageUrl(location.id) ?? ''} alt="" class="asset-thumb" />
                  {:else}
                    <span class="asset-thumb asset-thumb-empty">No photo</span>
                  {/if}
                  <div>
                    <strong>{location.name}</strong>
                    <span>{location.is_active ? 'active' : 'inactive'}</span>
                  </div>
                </div>
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

      <div class="detail-tab-bar" aria-label="Location detail sections">
        <button
          type="button"
          class:active-detail-tab={activeLocationDetailTab === 'info'}
          onclick={() => (activeLocationDetailTab = 'info')}
        >
          Info
        </button>
        <button
          type="button"
          class:active-detail-tab={activeLocationDetailTab === 'extra'}
          onclick={() => (activeLocationDetailTab = 'extra')}
        >
          Extra
        </button>
      </div>

      {#if activeLocationDetailTab === 'info'}
        <form
          class="asset-edit-form detail-tab-panel"
          onsubmit={(event) => {
            event.preventDefault();
            updateSelectedLocation();
          }}
        >
          <div class="asset-info-layout">
            <div class="asset-photo-panel compact-photo-panel">
              {#if locationImageUrl(selectedLocationId)}
                <img
                  src={locationImageUrl(selectedLocationId) ?? ''}
                  alt={`Photo of ${selectedLocation()?.name}`}
                  class="asset-photo"
                />
              {:else}
                <div class="asset-photo-placeholder">
                  <strong>No photo</strong>
                  <span>Add a square reference photo.</span>
                </div>
              {/if}
              <div class="asset-photo-actions">
                <input
                  bind:this={locationPhotoInput}
                  class="visually-hidden"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  capture="environment"
                  onchange={handleLocationPhotoChange}
                />
                <button
                  type="button"
                  class="micro-button"
                  disabled={busy}
                  onclick={() => locationPhotoInput?.click()}
                >
                  {locationImageUrl(selectedLocationId) ? 'Replace' : 'Add photo'}
                </button>
                {#if locationImageUrl(selectedLocationId)}
                  <button
                    type="button"
                    class="secondary micro-button"
                    disabled={busy}
                    onclick={deleteSelectedLocationImage}
                  >
                    Delete
                  </button>
                {/if}
              </div>
            </div>

            <label class="description-field" aria-label="Location description">
              <textarea
                bind:value={locationEditForm.notes}
                placeholder="What is this place, how do people find it, and what should they know first?"
              ></textarea>
            </label>
          </div>

          <label class="compact-field-row"
            >Name <input bind:value={locationEditForm.name} required /></label
          >
          <label class="compact-field-row"
            >Address <input bind:value={locationEditForm.address} /></label
          >

          <div class="button-row compact-button-row">
            <button type="submit" class="compact" disabled={busy}>Update info</button>
            <button type="button" class="secondary compact" onclick={closeLocationDetail}>
              Close
            </button>
          </div>
        </form>
      {/if}

      {#if activeLocationDetailTab === 'extra'}
        <div class="detail-tab-panel">
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
              <strong>{responsibleLabel(selectedLocation()?.responsible_person_id ?? null)}</strong>
            </article>
            <article>
              <span>State</span>
              <strong>{selectedLocation()?.is_active ? 'active' : 'inactive'}</strong>
            </article>
          </div>

          <form
            class="asset-edit-form detail-tab-panel"
            onsubmit={(event) => {
              event.preventDefault();
              updateSelectedLocation();
            }}
          >
            <label class="compact-field-row">
              Responsible person
              <select bind:value={locationEditForm.responsible_person_id}>
                <option value={null}>No responsible person</option>
                {#each persons as person}
                  <option value={person.id}>
                    {person.display_name} · {person.person_type.replaceAll('_', ' ')}
                  </option>
                {/each}
              </select>
            </label>
            <label class="compact-field-row">
              Type
              <select bind:value={locationEditForm.type}>
                {#each locationTypes as type}
                  <option value={type}>{type.replaceAll('_', ' ')}</option>
                {/each}
              </select>
            </label>
            <label class="checkbox-label">
              <input bind:checked={locationEditForm.is_active} type="checkbox" />
              Active
            </label>
            <button type="submit" class="compact" disabled={busy}>Update extra</button>
          </form>

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
                    >{asset.status.replaceAll('_', ' ')} / {asset.condition.replaceAll(
                      '_',
                      ' '
                    )}</span
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
        </div>
      {/if}
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
