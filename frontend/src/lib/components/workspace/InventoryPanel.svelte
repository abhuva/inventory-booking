<script lang="ts">
  import type { Asset, AssetCreate, Category, ItemEvent, Location, StockLevel } from '$lib/api';

  let {
    assets,
    categories,
    locations,
    trackedAssets,
    stockLevels,
    filteredAssets,
    selectedAssetEvents,
    selectedAssetId,
    busy,
    assetForm = $bindable(),
    assetStateForm = $bindable(),
    assetSearch = $bindable(),
    createAsset,
    changeAssetOperationalState,
    selectAssetDetail,
    closeAssetDetail,
    selectedAsset,
    categoryName,
    locationName,
    holderLabel,
    userLabel,
    formatDateTime
  }: {
    assets: Asset[];
    categories: Category[];
    locations: Location[];
    trackedAssets: Asset[];
    stockLevels: StockLevel[];
    filteredAssets: Asset[];
    selectedAssetEvents: ItemEvent[];
    selectedAssetId: string;
    busy: boolean;
    assetForm: AssetCreate;
    assetStateForm: {
      asset_id: string;
      action: string;
      status: string;
      condition: string;
      notes: string;
    };
    assetSearch: string;
    createAsset: () => void;
    changeAssetOperationalState: () => void;
    selectAssetDetail: (assetId: string) => void;
    closeAssetDetail: () => void;
    selectedAsset: () => Asset | undefined;
    categoryName: (id: string | null) => string;
    locationName: (id: string | null) => string;
    holderLabel: (id: string | null) => string;
    userLabel: (id: string | null) => string;
    formatDateTime: (value: string) => string;
  } = $props();
</script>

<section class="forms-grid" aria-label="Inventory controls">
  <form
    class="panel form-panel wide"
    onsubmit={(event) => {
      event.preventDefault();
      createAsset();
    }}
  >
    <h2>Asset</h2>
    <div class="split-fields">
      <label>Name <input bind:value={assetForm.name} required /></label>
      <label>
        Mode
        <select bind:value={assetForm.asset_type}>
          <option value="tracked">tracked exact item</option>
          <option value="stock">stock quantity</option>
        </select>
      </label>
    </div>
    <div class="split-fields">
      <label>
        Category
        <select bind:value={assetForm.category_id}>
          <option value={null}>No category</option>
          {#each categories as category}
            <option value={category.id}>{category.name}</option>
          {/each}
        </select>
      </label>
      <label>
        Current location
        <select bind:value={assetForm.current_location_id}>
          <option value={null}>No location</option>
          {#each locations as location}
            <option value={location.id}>{location.name}</option>
          {/each}
        </select>
      </label>
    </div>
    {#if assetForm.asset_type === 'stock'}
      <label
        >Unit name <input
          bind:value={assetForm.unit_name}
          placeholder="piece, set, box"
          required
        /></label
      >
    {/if}
    <button type="submit" disabled={busy}>Create asset</button>
  </form>

  <form
    class="panel form-panel wide"
    onsubmit={(event) => {
      event.preventDefault();
      changeAssetOperationalState();
    }}
  >
    <h2>Asset state</h2>
    <div class="split-fields">
      <label>
        Asset
        <select bind:value={assetStateForm.asset_id} required>
          <option value="">Choose tracked asset</option>
          {#each trackedAssets as asset}
            <option value={asset.id}>{asset.name} · {asset.status}</option>
          {/each}
        </select>
      </label>
      <label>
        Action
        <select bind:value={assetStateForm.action}>
          <option value="maintenance_start">start maintenance</option>
          <option value="maintenance_complete">complete maintenance</option>
          <option value="state_change">mark state</option>
        </select>
      </label>
    </div>
    {#if assetStateForm.action === 'state_change'}
      <label>
        State
        <select bind:value={assetStateForm.status}>
          <option value="damaged">damaged</option>
          <option value="lost">lost</option>
          <option value="retired">retired</option>
          <option value="available">available / found</option>
        </select>
      </label>
    {/if}
    {#if assetStateForm.action !== 'maintenance_start'}
      <label>
        Condition
        <select bind:value={assetStateForm.condition}>
          <option value="unknown">unknown</option>
          <option value="good">good</option>
          <option value="worn">worn</option>
          <option value="damaged">damaged</option>
          <option value="needs_repair">needs repair</option>
        </select>
      </label>
    {/if}
    <label>Notes <textarea bind:value={assetStateForm.notes}></textarea></label>
    <button type="submit" disabled={busy}>Update asset state</button>
  </form>
</section>

{#if selectedAsset()}
  <section class="panel detail-panel" aria-label="Selected asset detail">
    <div class="detail-header">
      <div>
        <p class="eyebrow">Asset detail</p>
        <h2>{selectedAsset()?.name}</h2>
      </div>
      <button type="button" class="secondary" onclick={closeAssetDetail}>Close detail</button>
    </div>

    <div class="detail-grid">
      <div>
        <span>Mode</span>
        <strong>{selectedAsset()?.asset_type}</strong>
      </div>
      <div>
        <span>Status</span>
        <strong>{selectedAsset()?.status}</strong>
      </div>
      <div>
        <span>Condition</span>
        <strong>{selectedAsset()?.condition}</strong>
      </div>
      <div>
        <span>Category</span>
        <strong>{categoryName(selectedAsset()?.category_id ?? null)}</strong>
      </div>
      <div>
        <span>Current location</span>
        <strong>{locationName(selectedAsset()?.current_location_id ?? null)}</strong>
      </div>
      <div>
        <span>Holder</span>
        <strong>{holderLabel(selectedAsset()?.current_holder_user_id ?? null)}</strong>
      </div>
      {#if selectedAsset()?.asset_type === 'stock'}
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
      {/if}
    </div>

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
              {locationName(event.from_location_id)} → {locationName(event.to_location_id)}
            {:else}
              {event.notes ?? 'No notes'}
            {/if}
          </p>
        </article>
      {:else}
        <p class="empty">No history recorded for this asset yet.</p>
      {/each}
    </div>
  </section>
{/if}

<section class="data-grid" aria-label="Inventory lists">
  <article class="panel list-panel">
    <div class="list-header">
      <div>
        <h2>Assets</h2>
        <p>{filteredAssets.length} of {assets.length} shown</p>
      </div>
      <button
        type="button"
        class="secondary compact"
        onclick={() => {
          assetSearch = '';
        }}
        disabled={!assetSearch}
      >
        Clear
      </button>
    </div>
    <label class="search-field">
      Search assets
      <input
        bind:value={assetSearch}
        placeholder="name, category, location, status, tag..."
        type="search"
      />
    </label>
    {#each filteredAssets as asset}
      <div class="row-card">
        <strong>{asset.name}</strong>
        <span
          >{asset.asset_type} · {categoryName(asset.category_id)} · {locationName(
            asset.current_location_id
          )}</span
        >
        <button
          type="button"
          class="secondary compact"
          onclick={() => selectAssetDetail(asset.id)}
          disabled={busy}
        >
          View detail
        </button>
      </div>
    {:else}
      <p class="empty">{assets.length ? 'No assets match this search.' : 'No assets yet.'}</p>
    {/each}
  </article>
</section>
