<script lang="ts">
  import type { Asset, Location } from '$lib/api';

  let {
    assets,
    locations,
    displayedAssets,
    selectedAssetId,
    assetSearch = $bindable(),
    locationFilter = $bindable(),
    assetImageUrl,
    categoryName,
    assetStatusSummary,
    assetLocationSummary,
    assetHolderSummary,
    onAddAsset,
    onSelectAsset
  }: {
    assets: Asset[];
    locations: Location[];
    displayedAssets: Asset[];
    selectedAssetId: string;
    assetSearch: string;
    locationFilter: string;
    assetImageUrl: (assetId: string) => string | null;
    categoryName: (id: string | null) => string;
    assetStatusSummary: (asset: Asset) => string;
    assetLocationSummary: (asset: Asset) => string;
    assetHolderSummary: (asset: Asset) => string;
    onAddAsset: () => void;
    onSelectAsset: (assetId: string) => void;
  } = $props();
</script>

<section class="panel inventory-table-panel">
  <div class="inventory-toolbar">
    <div>
      <h2>Assets</h2>
      <p>{displayedAssets.length} of {assets.length} shown</p>
    </div>
    <div class="inventory-actions">
      <input
        bind:value={assetSearch}
        aria-label="Search assets"
        placeholder="Search assets..."
        type="search"
      />
      <select bind:value={locationFilter} aria-label="Filter assets by location">
        <option value="">All locations</option>
        {#each locations as location}
          <option value={location.id}>{location.name}</option>
        {/each}
      </select>
      <button
        type="button"
        class="secondary compact"
        disabled={!assetSearch && !locationFilter}
        onclick={() => {
          assetSearch = '';
          locationFilter = '';
        }}
      >
        Clear
      </button>
      <button type="button" class="compact" onclick={onAddAsset}>+ Add asset</button>
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
        {#each displayedAssets as asset}
          <tr
            class:selected-row={asset.id === selectedAssetId}
            onclick={() => onSelectAsset(asset.id)}
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
