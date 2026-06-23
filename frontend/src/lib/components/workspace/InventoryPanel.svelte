<script lang="ts">
  import type {
    Asset,
    AssetCondition,
    AssetCreate,
    AssetStatus,
    AssetUpdate,
    Category,
    ItemEvent,
    Location,
    StockLevel,
    User
  } from '$lib/api';

  const assetStatuses: AssetStatus[] = [
    'available',
    'reserved',
    'checked_out',
    'in_transfer',
    'maintenance',
    'damaged',
    'lost',
    'retired'
  ];
  const assetConditions: AssetCondition[] = ['unknown', 'good', 'worn', 'damaged', 'needs_repair'];

  let showAddAsset = $state(false);
  let photoInput = $state<HTMLInputElement>();

  let {
    assets,
    categories,
    locations,
    users,
    currentUser,
    stockLevels,
    filteredAssets,
    selectedAssetEvents,
    selectedAssetId,
    busy,
    assetForm = $bindable(),
    assetEditForm = $bindable(),
    assetSearch = $bindable(),
    createAsset,
    updateSelectedAsset,
    uploadSelectedAssetImage,
    deleteSelectedAssetImage,
    selectAssetDetail,
    closeAssetDetail,
    selectedAsset,
    categoryName,
    locationName,
    holderLabel,
    userLabel,
    assetImageUrl,
    formatDateTime
  }: {
    assets: Asset[];
    categories: Category[];
    locations: Location[];
    users: User[];
    currentUser: User | null;
    stockLevels: StockLevel[];
    filteredAssets: Asset[];
    selectedAssetEvents: ItemEvent[];
    selectedAssetId: string;
    busy: boolean;
    assetForm: AssetCreate;
    assetEditForm: AssetUpdate;
    assetSearch: string;
    createAsset: () => void;
    updateSelectedAsset: () => void;
    uploadSelectedAssetImage: (file: File) => void;
    deleteSelectedAssetImage: () => void;
    selectAssetDetail: (assetId: string) => void;
    closeAssetDetail: () => void;
    selectedAsset: () => Asset | undefined;
    categoryName: (id: string | null) => string;
    locationName: (id: string | null) => string;
    holderLabel: (id: string | null) => string;
    userLabel: (id: string | null) => string;
    assetImageUrl: (assetId: string) => string | null;
    formatDateTime: (value: string) => string;
  } = $props();

  function submitNewAsset() {
    createAsset();
    showAddAsset = false;
  }

  function availableHolderUsers(): User[] {
    if (!currentUser) {
      return users;
    }
    return users.some((user) => user.id === currentUser.id) ? users : [currentUser, ...users];
  }

  function handlePhotoChange(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    uploadSelectedAssetImage(file);
    input.value = '';
  }
</script>

<section class="inventory-workspace" aria-label="Inventory workspace">
  <section class="panel inventory-table-panel">
    <div class="inventory-toolbar">
      <div>
        <h2>Assets</h2>
        <p>{filteredAssets.length} of {assets.length} shown</p>
      </div>
      <div class="inventory-actions">
        <input
          bind:value={assetSearch}
          aria-label="Search assets"
          placeholder="Search assets..."
          type="search"
        />
        <button
          type="button"
          class="secondary compact"
          disabled={!assetSearch}
          onclick={() => (assetSearch = '')}
        >
          Clear
        </button>
        <button type="button" class="compact" onclick={() => (showAddAsset = true)}
          >+ Add asset</button
        >
      </div>
    </div>

    <div class="asset-table-wrap">
      <table class="asset-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Location</th>
            <th>Holder</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredAssets as asset}
            <tr
              class:selected-row={asset.id === selectedAssetId}
              onclick={() => selectAssetDetail(asset.id)}
            >
              <td>
                <div class="asset-name-cell">
                  {#if assetImageUrl(asset.id)}
                    <img src={assetImageUrl(asset.id) ?? ''} alt="" class="asset-thumb" />
                  {:else}
                    <span class="asset-thumb asset-thumb-empty">No photo</span>
                  {/if}
                  <div>
                    <strong>{asset.name}</strong>
                    <span>{asset.asset_type} · {categoryName(asset.category_id)}</span>
                  </div>
                </div>
              </td>
              <td
                ><span class={`status-pill status-${asset.status}`}
                  >{asset.status.replaceAll('_', ' ')}</span
                ></td
              >
              <td>{locationName(asset.current_location_id)}</td>
              <td>{holderLabel(asset.current_holder_user_id)}</td>
            </tr>
          {:else}
            <tr>
              <td colspan="4" class="empty">
                {assets.length ? 'No assets match this search.' : 'No assets yet.'}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <aside class="panel inventory-detail-panel" aria-label="Selected asset details">
    {#if selectedAsset()}
      <div class="detail-header">
        <div>
          <p class="eyebrow">Asset detail</p>
          <h2>{selectedAsset()?.name}</h2>
        </div>
        <button type="button" class="secondary compact" onclick={closeAssetDetail}>Close</button>
      </div>

      <div class="asset-photo-panel">
        {#if assetImageUrl(selectedAssetId)}
          <img
            src={assetImageUrl(selectedAssetId) ?? ''}
            alt={`Photo of ${selectedAsset()?.name}`}
            class="asset-photo"
          />
        {:else}
          <div class="asset-photo-placeholder">
            <strong>No photo</strong>
            <span>Add a square reference photo for quick recognition.</span>
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
          <button type="button" class="compact" disabled={busy} onclick={() => photoInput?.click()}>
            {assetImageUrl(selectedAssetId) ? 'Replace photo' : 'Add photo'}
          </button>
          {#if assetImageUrl(selectedAssetId)}
            <button
              type="button"
              class="secondary compact"
              disabled={busy}
              onclick={deleteSelectedAssetImage}
            >
              Delete photo
            </button>
          {/if}
        </div>
      </div>

      <form
        class="asset-edit-form"
        onsubmit={(event) => {
          event.preventDefault();
          updateSelectedAsset();
        }}
      >
        <label>Name <input bind:value={assetEditForm.name} required /></label>
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
        <div class="split-fields">
          <label>
            Category
            <select bind:value={assetEditForm.category_id}>
              <option value={null}>No category</option>
              {#each categories as category}
                <option value={category.id}>{category.name}</option>
              {/each}
            </select>
          </label>
          <label>
            Current location
            <select bind:value={assetEditForm.current_location_id}>
              <option value={null}>No location</option>
              {#each locations as location}
                <option value={location.id}>{location.name}</option>
              {/each}
            </select>
          </label>
        </div>
        <label>
          Holder
          <select bind:value={assetEditForm.current_holder_user_id}>
            <option value={null}>No holder</option>
            {#each availableHolderUsers() as user}
              <option value={user.id}>{user.display_name}</option>
            {/each}
          </select>
        </label>
        <div class="split-fields">
          <label>Manufacturer <input bind:value={assetEditForm.manufacturer} /></label>
          <label>Model <input bind:value={assetEditForm.model} /></label>
        </div>
        <div class="split-fields">
          <label>Serial <input bind:value={assetEditForm.serial_number} /></label>
          <label>Asset tag <input bind:value={assetEditForm.asset_tag} /></label>
        </div>
        <label>Replacement value <input bind:value={assetEditForm.replacement_value} /></label>
        <label>Notes <textarea bind:value={assetEditForm.notes}></textarea></label>
        <button type="submit" disabled={busy}>Update asset</button>
      </form>

      {#if selectedAsset()?.asset_type === 'stock'}
        <div class="detail-grid">
          <div>
            <span>Unit</span>
            <strong>{selectedAsset()?.unit_name ?? 'unit'}</strong>
          </div>
          <div>
            <span>Total stock</span>
            <strong
              >{stockLevels
                .filter((level) => level.asset_id === selectedAssetId)
                .reduce((sum, level) => sum + level.quantity_total, 0)}</strong
            >
          </div>
        </div>
      {/if}

      <div class="timeline">
        <h3>History</h3>
        {#each selectedAssetEvents as event}
          <article class="timeline-entry">
            <div>
              <strong>{event.event_type.replaceAll('_', ' ')}</strong>
              <span>{formatDateTime(event.created_at)} · {userLabel(event.actor_user_id)}</span>
            </div>
            <p>
              {#if event.from_location_id || event.to_location_id}
                {locationName(event.from_location_id)} -> {locationName(event.to_location_id)}
              {:else}
                {event.notes ?? 'No notes'}
              {/if}
            </p>
          </article>
        {:else}
          <p class="empty">No history recorded for this asset yet.</p>
        {/each}
      </div>
    {:else}
      <div class="empty-detail">
        <h2>Select an asset</h2>
        <p>Click a row in the table to view and edit details.</p>
      </div>
    {/if}
  </aside>
</section>

{#if showAddAsset}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label="Add asset"
      onsubmit={(event) => {
        event.preventDefault();
        submitNewAsset();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">New asset</p>
          <h2>Add asset</h2>
        </div>
        <button type="button" class="secondary compact" onclick={() => (showAddAsset = false)}
          >Cancel</button
        >
      </div>
      <label>Name <input bind:value={assetForm.name} required /></label>
      <div class="split-fields">
        <label>
          Mode
          <select bind:value={assetForm.asset_type}>
            <option value="tracked">tracked exact item</option>
            <option value="stock">stock quantity</option>
          </select>
        </label>
        <label>
          Category
          <select bind:value={assetForm.category_id}>
            <option value={null}>No category</option>
            {#each categories as category}
              <option value={category.id}>{category.name}</option>
            {/each}
          </select>
        </label>
      </div>
      <label>
        Current location
        <select bind:value={assetForm.current_location_id}>
          <option value={null}>No location</option>
          {#each locations as location}
            <option value={location.id}>{location.name}</option>
          {/each}
        </select>
      </label>
      {#if assetForm.asset_type === 'stock'}
        <label
          >Unit name <input
            bind:value={assetForm.unit_name}
            placeholder="piece, set, box"
            required
          /></label
        >
      {/if}
      <div class="button-row">
        <button type="button" class="secondary" onclick={() => (showAddAsset = false)}
          >Cancel</button
        >
        <button type="submit" disabled={busy}>Save asset</button>
      </div>
    </form>
  </div>
{/if}
