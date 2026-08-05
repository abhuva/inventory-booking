<script lang="ts">
  import type { StockLevel } from '$lib/api';

  let {
    busy,
    canRemoveStock,
    locationFilter,
    scopeLabel,
    stockLevels,
    total,
    checkedOut,
    unitName,
    locationName,
    onAddStock,
    onRemoveStock
  }: {
    busy: boolean;
    canRemoveStock: boolean;
    locationFilter: string;
    scopeLabel: string;
    stockLevels: StockLevel[];
    total: number;
    checkedOut: number;
    unitName: string;
    locationName: (id: string | null) => string;
    onAddStock: () => void;
    onRemoveStock: () => void;
  } = $props();
</script>

<div class="detail-tab-panel stock-panel">
  <div class="stock-scope-row">
    <p class="field-note">Scope: {scopeLabel}</p>
    <div class="button-row compact-button-row">
      <button type="button" class="compact" disabled={busy} onclick={onAddStock}>Add</button>
      <button
        type="button"
        class="secondary compact"
        disabled={busy || !canRemoveStock}
        onclick={onRemoveStock}
      >
        Remove
      </button>
    </div>
  </div>

  <div class="physical-summary-grid">
    <article>
      <span>Total</span>
      <strong>{total} {unitName}</strong>
    </article>
    <article>
      <span>Available</span>
      <strong>{total - checkedOut} {unitName}</strong>
    </article>
    <article>
      <span>Checked out</span>
      <strong>{checkedOut} {unitName}</strong>
    </article>
  </div>

  <div class="stock-batch-list">
    <h3>{locationFilter ? 'Physical stock here' : 'Physical batches'}</h3>
    {#each stockLevels as level}
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
        <span class="stock-quantity">{level.quantity_total} {unitName}</span>
      </article>
    {:else}
      <p class="empty">
        {locationFilter
          ? 'No stock exists for this item at the selected location.'
          : 'No stock batches exist for this item yet.'}
      </p>
    {/each}
  </div>

  <p class="field-note">
    {locationFilter
      ? 'Add, remove, or move stock for the selected location here.'
      : 'Add stock here by choosing a location in the popup.'}
  </p>
</div>
