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
  type AssetDetailTab = 'info' | 'unit' | 'stock' | 'extra' | 'history';

  let showAddAsset = $state(false);
  let activeDetailTab = $state<AssetDetailTab>('info');
  let inventoryLocationFilter = $state('');
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

  function selectedStockLevels(): StockLevel[] {
    return stockLevelsForAsset(selectedAssetId);
  }

  function selectedStockTotal(): number {
    return selectedStockLevels().reduce((sum, level) => sum + level.quantity_total, 0);
  }

  function selectedStockCheckedOut(): number {
    return selectedStockLevels().reduce((sum, level) => sum + level.quantity_checked_out, 0);
  }

  function displayedAssets(): Asset[] {
    return filteredAssets.filter((asset) => assetMatchesLocation(asset));
  }

  function assetMatchesLocation(asset: Asset): boolean {
    if (!inventoryLocationFilter) {
      return true;
    }
    if (asset.asset_type === 'tracked') {
      return asset.current_location_id === inventoryLocationFilter;
    }
    return stockLevelsForAsset(asset.id).some(
      (level) => level.location_id === inventoryLocationFilter && level.quantity_total > 0
    );
  }

  function stockLevelsForAsset(assetId: string): StockLevel[] {
    return stockLevels.filter((level) => level.asset_id === assetId);
  }

  function visibleStockLevelsForAsset(assetId: string): StockLevel[] {
    const levels = stockLevelsForAsset(assetId);
    if (!inventoryLocationFilter) {
      return levels;
    }
    return levels.filter((level) => level.location_id === inventoryLocationFilter);
  }

  function stockTotalForAsset(assetId: string): number {
    return visibleStockLevelsForAsset(assetId).reduce(
      (sum, level) => sum + level.quantity_total,
      0
    );
  }

  function stockCheckedOutForAsset(assetId: string): number {
    return visibleStockLevelsForAsset(assetId).reduce(
      (sum, level) => sum + level.quantity_checked_out,
      0
    );
  }

  function stockAvailableForAsset(assetId: string): number {
    return stockTotalForAsset(assetId) - stockCheckedOutForAsset(assetId);
  }

  function assetLocationSummary(asset: Asset): string {
    if (asset.asset_type === 'tracked') {
      return locationName(asset.current_location_id);
    }
    if (inventoryLocationFilter) {
      return locationName(inventoryLocationFilter);
    }
    const levels = stockLevelsForAsset(asset.id).filter((level) => level.quantity_total > 0);
    if (levels.length === 0) {
      return 'No stock location';
    }
    if (levels.length === 1) {
      return locationName(levels[0].location_id);
    }
    return `${levels.length} locations`;
  }

  function assetHolderSummary(asset: Asset): string {
    if (asset.asset_type === 'tracked') {
      return holderLabel(asset.current_holder_user_id);
    }
    const checkedOutQuantity = stockCheckedOutForAsset(asset.id);
    return checkedOutQuantity > 0 ? `${checkedOutQuantity} checked out` : 'Stock item';
  }

  function assetStatusSummary(asset: Asset): string {
    if (asset.asset_type === 'tracked') {
      return asset.status.replaceAll('_', ' ');
    }
    const checkedOutQuantity = stockCheckedOutForAsset(asset.id);
    const availableQuantity = stockAvailableForAsset(asset.id);
    return checkedOutQuantity > 0
      ? `${availableQuantity} available / ${checkedOutQuantity} out`
      : `${availableQuantity} available`;
  }

  $effect(() => {
    const asset = selectedAsset();
    if (!asset) {
      return;
    }
    if (activeDetailTab === 'unit' && asset.asset_type !== 'tracked') {
      activeDetailTab = 'stock';
    }
    if (activeDetailTab === 'stock' && asset.asset_type !== 'stock') {
      activeDetailTab = 'unit';
    }
  });
</script>

<section class="inventory-workspace" aria-label="Inventory workspace">
  <section class="panel inventory-table-panel">
    <div class="inventory-toolbar">
      <div>
        <h2>Assets</h2>
        <p>{displayedAssets().length} of {assets.length} shown</p>
      </div>
      <div class="inventory-actions">
        <input
          bind:value={assetSearch}
          aria-label="Search assets"
          placeholder="Search assets..."
          type="search"
        />
        <select bind:value={inventoryLocationFilter} aria-label="Filter assets by location">
          <option value="">All locations</option>
          {#each locations as location}
            <option value={location.id}>{location.name}</option>
          {/each}
        </select>
        <button
          type="button"
          class="secondary compact"
          disabled={!assetSearch && !inventoryLocationFilter}
          onclick={() => {
            assetSearch = '';
            inventoryLocationFilter = '';
          }}
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
          {#each displayedAssets() as asset}
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
                    <span>{asset.asset_type} / {categoryName(asset.category_id)}</span>
                  </div>
                </div>
              </td>
              <td>
                <span
                  class={asset.asset_type === 'tracked'
                    ? `status-pill status-${asset.status}`
                    : 'status-pill status-stock'}
                >
                  {assetStatusSummary(asset)}
                </span>
              </td>
              <td>{assetLocationSummary(asset)}</td>
              <td>{assetHolderSummary(asset)}</td>
            </tr>
          {:else}
            <tr>
              <td colspan="4" class="empty">
                {assets.length ? 'No assets match this filter.' : 'No assets yet.'}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <aside class="panel inventory-detail-panel" aria-label="Selected asset details">
    {#if selectedAsset()}
      <div class="detail-header asset-detail-header">
        <div>
          <p class="eyebrow">Asset detail</p>
          <h2>{selectedAsset()?.name}</h2>
        </div>
        <button type="button" class="secondary micro-button" onclick={closeAssetDetail}
          >Close</button
        >
      </div>

      <div class="detail-tab-bar" aria-label="Asset detail sections">
        <button
          type="button"
          class:active-detail-tab={activeDetailTab === 'info'}
          onclick={() => (activeDetailTab = 'info')}
        >
          Info
        </button>
        {#if selectedAsset()?.asset_type === 'tracked'}
          <button
            type="button"
            class:active-detail-tab={activeDetailTab === 'unit'}
            onclick={() => (activeDetailTab = 'unit')}
          >
            Unit
          </button>
        {/if}
        {#if selectedAsset()?.asset_type === 'stock'}
          <button
            type="button"
            class:active-detail-tab={activeDetailTab === 'stock'}
            onclick={() => (activeDetailTab = 'stock')}
          >
            Stock
          </button>
        {/if}
        <button
          type="button"
          class:active-detail-tab={activeDetailTab === 'extra'}
          onclick={() => (activeDetailTab = 'extra')}
        >
          Extra
        </button>
        <button
          type="button"
          class:active-detail-tab={activeDetailTab === 'history'}
          onclick={() => (activeDetailTab = 'history')}
        >
          History
        </button>
      </div>

      {#if activeDetailTab === 'info'}
        <form
          class="asset-edit-form detail-tab-panel"
          onsubmit={(event) => {
            event.preventDefault();
            updateSelectedAsset();
          }}
        >
          <div class="asset-info-layout">
            <div class="asset-photo-panel compact-photo-panel">
              {#if assetImageUrl(selectedAssetId)}
                <img
                  src={assetImageUrl(selectedAssetId) ?? ''}
                  alt={`Photo of ${selectedAsset()?.name}`}
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
                  bind:this={photoInput}
                  class="visually-hidden"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  capture="environment"
                  onchange={handlePhotoChange}
                />
                <button
                  type="button"
                  class="micro-button"
                  disabled={busy}
                  onclick={() => photoInput?.click()}
                >
                  {assetImageUrl(selectedAssetId) ? 'Replace photo' : 'Add photo'}
                </button>
                {#if assetImageUrl(selectedAssetId)}
                  <button
                    type="button"
                    class="secondary micro-button"
                    disabled={busy}
                    onclick={deleteSelectedAssetImage}
                  >
                    Delete
                  </button>
                {/if}
              </div>
            </div>

            <label class="description-field">
              Description
              <textarea
                bind:value={assetEditForm.description}
                placeholder="What is this item, what makes it recognizable, and what should people know first?"
              ></textarea>
            </label>
          </div>

          <label>Name <input bind:value={assetEditForm.name} required /></label>
          <div class="split-fields">
            <label>
              Mode
              <input value={selectedAsset()?.asset_type.replaceAll('_', ' ')} disabled />
            </label>
            <label>
              Unit
              <input value={selectedAsset()?.unit_name ?? 'single unit'} disabled />
            </label>
          </div>
          <label>
            Category
            <select bind:value={assetEditForm.category_id}>
              <option value={null}>No category</option>
              {#each categories as category}
                <option value={category.id}>{category.name}</option>
              {/each}
            </select>
          </label>
          <button type="submit" class="compact" disabled={busy}>Update info</button>
        </form>
      {/if}

      {#if activeDetailTab === 'unit' && selectedAsset()?.asset_type === 'tracked'}
        <form
          class="asset-edit-form detail-tab-panel"
          onsubmit={(event) => {
            event.preventDefault();
            updateSelectedAsset();
          }}
        >
          <div class="physical-summary-grid">
            <article>
              <span>Status</span>
              <strong>{selectedAsset()?.status.replaceAll('_', ' ')}</strong>
            </article>
            <article>
              <span>Condition</span>
              <strong>{selectedAsset()?.condition.replaceAll('_', ' ')}</strong>
            </article>
            <article>
              <span>Location</span>
              <strong>{locationName(selectedAsset()?.current_location_id ?? null)}</strong>
            </article>
            <article>
              <span>Holder</span>
              <strong>{holderLabel(selectedAsset()?.current_holder_user_id ?? null)}</strong>
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
              {#each availableHolderUsers() as user}
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
      {/if}

      {#if activeDetailTab === 'stock' && selectedAsset()?.asset_type === 'stock'}
        <div class="detail-tab-panel stock-panel">
          <div class="physical-summary-grid">
            <article>
              <span>Total</span>
              <strong>{selectedStockTotal()} {selectedAsset()?.unit_name ?? 'units'}</strong>
            </article>
            <article>
              <span>Available</span>
              <strong
                >{selectedStockTotal() - selectedStockCheckedOut()}
                {selectedAsset()?.unit_name ?? 'units'}</strong
              >
            </article>
            <article>
              <span>Checked out</span>
              <strong>{selectedStockCheckedOut()} {selectedAsset()?.unit_name ?? 'units'}</strong>
            </article>
          </div>

          <div class="stock-batch-list">
            <h3>Physical batches</h3>
            {#each selectedStockLevels() as level}
              <article class="stock-batch-card">
                <div>
                  <strong>{locationName(level.location_id)}</strong>
                  <span>
                    {level.quantity_total - level.quantity_checked_out} available
                    {#if level.quantity_checked_out}
                      / {level.quantity_checked_out} checked out
                    {/if}
                  </span>
                </div>
                <span class="stock-quantity"
                  >{level.quantity_total} {selectedAsset()?.unit_name ?? 'units'}</span
                >
              </article>
            {:else}
              <p class="empty">No stock batches exist for this item yet.</p>
            {/each}
          </div>

          <p class="field-note">
            Stock movement and new batches are handled in the Locations tab for now.
          </p>
        </div>
      {/if}

      {#if activeDetailTab === 'extra'}
        <form
          class="asset-edit-form detail-tab-panel"
          onsubmit={(event) => {
            event.preventDefault();
            updateSelectedAsset();
          }}
        >
          <div class="split-fields">
            <label>Manufacturer <input bind:value={assetEditForm.manufacturer} /></label>
            <label>Model <input bind:value={assetEditForm.model} /></label>
          </div>
          <div class="split-fields">
            <label>Replacement value <input bind:value={assetEditForm.replacement_value} /></label>
            <label>Definition type <input value={selectedAsset()?.asset_type} disabled /></label>
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
      {/if}

      {#if activeDetailTab === 'history'}
        <div class="detail-tab-panel history-panel">
          <div class="timeline">
            <h3>History</h3>
            {#each selectedAssetEvents as event}
              <article class="timeline-entry">
                <div>
                  <strong>{event.event_type.replaceAll('_', ' ')}</strong>
                  <span>{formatDateTime(event.created_at)} - {userLabel(event.actor_user_id)}</span>
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
        </div>
      {/if}
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
