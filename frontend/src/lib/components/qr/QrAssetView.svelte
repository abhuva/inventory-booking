<script lang="ts">
  import type { Asset, Category, ItemEvent, Location, StockLevel } from '$lib/api';

  let {
    asset,
    imageUrl,
    categories,
    locations,
    stockLevels,
    events
  }: {
    asset: Asset;
    imageUrl: string | null;
    categories: Category[];
    locations: Location[];
    stockLevels: StockLevel[];
    events: ItemEvent[];
  } = $props();

  const totalStock = $derived(
    stockLevels.reduce((total, level) => total + level.quantity_total, 0)
  );
  const checkedOutStock = $derived(
    stockLevels.reduce((total, level) => total + level.quantity_checked_out, 0)
  );
  const reservedStock = $derived(
    stockLevels.reduce((total, level) => total + level.quantity_reserved, 0)
  );

  function categoryName(): string {
    return categories.find((category) => category.id === asset.category_id)?.name ?? 'No category';
  }

  function locationName(locationId: string | null): string {
    if (!locationId) {
      return 'No location';
    }
    return locations.find((location) => location.id === locationId)?.name ?? 'Unknown location';
  }

  function displayLabel(value: string): string {
    return value.replaceAll('_', ' ');
  }

  function formatValue(value: string | number | null | undefined): string {
    return value === null || value === undefined || value === '' ? 'Not recorded' : String(value);
  }

  function formatMoney(value: string | null): string {
    if (!value) {
      return 'Not recorded';
    }
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'EUR'
    }).format(Number(value));
  }

  function formatDateTime(value: string): string {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(new Date(value));
  }
</script>

<article class="qr-asset-view">
  <div class="qr-asset-media">
    {#if imageUrl}
      <img src={imageUrl} alt={`Photo of ${asset.name}`} />
    {:else}
      <div class="qr-asset-placeholder">
        <strong>No photo</strong>
        <span>{asset.asset_type === 'tracked' ? 'Tracked item' : 'Stock item'}</span>
      </div>
    {/if}
  </div>

  <header class="qr-asset-heading">
    <div>
      <p class="eyebrow">{asset.asset_type === 'tracked' ? 'Tracked asset' : 'Stock asset'}</p>
      <h1>{asset.name}</h1>
      <p>{categoryName()}</p>
    </div>
    <div class="qr-state-row" aria-label="Asset state">
      <span class="qr-status qr-status-{asset.status}">{displayLabel(asset.status)}</span>
      <span class="qr-condition qr-condition-{asset.condition}"
        >{displayLabel(asset.condition)}</span
      >
    </div>
  </header>

  {#if asset.description}
    <p class="qr-asset-description">{asset.description}</p>
  {/if}

  <section class="qr-detail-section">
    <h2>Location</h2>
    <dl class="qr-detail-grid">
      <div>
        <dt>Current</dt>
        <dd>{locationName(asset.current_location_id)}</dd>
      </div>
      <div>
        <dt>Home</dt>
        <dd>{locationName(asset.home_location_id)}</dd>
      </div>
      {#if asset.current_holder_user_id}
        <div>
          <dt>Responsibility</dt>
          <dd>Assigned to a user</dd>
        </div>
      {/if}
    </dl>
  </section>

  {#if asset.asset_type === 'stock'}
    <section class="qr-detail-section">
      <h2>Stock</h2>
      <div class="qr-stock-summary">
        <div><span>Total</span><strong>{totalStock}</strong></div>
        <div>
          <span>Available now</span>
          <strong>{Math.max(0, totalStock - checkedOutStock - reservedStock)}</strong>
        </div>
        <div><span>Reserved</span><strong>{reservedStock}</strong></div>
        <div><span>Checked out</span><strong>{checkedOutStock}</strong></div>
      </div>
      <div class="qr-stock-list">
        {#each stockLevels as level}
          <div>
            <span>{locationName(level.location_id)}</span>
            <strong>{level.quantity_total} {asset.unit_name ?? 'units'}</strong>
          </div>
        {:else}
          <p>No stock has been recorded for this item.</p>
        {/each}
      </div>
    </section>
  {/if}

  <section class="qr-detail-section">
    <h2>Identification</h2>
    <dl class="qr-detail-grid">
      <div>
        <dt>Manufacturer</dt>
        <dd>{formatValue(asset.manufacturer)}</dd>
      </div>
      <div>
        <dt>Model</dt>
        <dd>{formatValue(asset.model)}</dd>
      </div>
      <div>
        <dt>Serial number</dt>
        <dd>{formatValue(asset.serial_number)}</dd>
      </div>
      <div>
        <dt>Asset tag</dt>
        <dd>{formatValue(asset.asset_tag)}</dd>
      </div>
      <div>
        <dt>Replacement value</dt>
        <dd>{formatMoney(asset.replacement_value)}</dd>
      </div>
      {#if asset.asset_type === 'stock'}
        <div>
          <dt>Unit</dt>
          <dd>{formatValue(asset.unit_name)}</dd>
        </div>
      {/if}
    </dl>
  </section>

  {#if asset.notes}
    <section class="qr-detail-section">
      <h2>Notes</h2>
      <p class="qr-notes">{asset.notes}</p>
    </section>
  {/if}

  <section class="qr-detail-section">
    <h2>Recent history</h2>
    <div class="qr-history-list">
      {#each events as event}
        <div>
          <strong>{displayLabel(event.event_type)}</strong>
          <span>{formatDateTime(event.created_at)}</span>
          {#if event.notes}<p>{event.notes}</p>{/if}
        </div>
      {:else}
        <p>No history has been recorded for this item.</p>
      {/each}
    </div>
  </section>
</article>
