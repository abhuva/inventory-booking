<script lang="ts">
  import type { Asset, AssetUpdate } from '$lib/api';
  import { calculateDailyRate, formatEuro } from '$lib/rental-pricing';

  let {
    asset,
    assetEditForm = $bindable(),
    busy,
    onUpdate
  }: {
    asset: Asset;
    assetEditForm: AssetUpdate;
    busy: boolean;
    onUpdate: () => void;
  } = $props();

  const dailyRate = $derived(
    calculateDailyRate(
      assetEditForm.replacement_value,
      assetEditForm.rental_recoup_days,
      assetEditForm.rental_maintenance_cost_per_day,
      assetEditForm.rental_profit_margin_percent
    )
  );

  function submitPricing(): void {
    assetEditForm.replacement_value ??= null;
    assetEditForm.rental_recoup_days ??= null;
    assetEditForm.rental_maintenance_cost_per_day ??= null;
    assetEditForm.rental_profit_margin_percent ??= null;
    onUpdate();
  }
</script>

<form
  class="asset-edit-form detail-tab-panel"
  onsubmit={(event) => {
    event.preventDefault();
    submitPricing();
  }}
>
  <div class="split-fields">
    <label>
      {asset.asset_type === 'stock' ? 'Base value per unit' : 'Base value'}
      <input
        bind:value={assetEditForm.replacement_value}
        inputmode="decimal"
        min="0"
        step="0.01"
        type="number"
      />
    </label>
    <label>
      Recoup after rental days
      <input
        bind:value={assetEditForm.rental_recoup_days}
        inputmode="numeric"
        min="1"
        step="1"
        type="number"
      />
    </label>
  </div>
  <div class="split-fields">
    <label>
      Maintenance per unit/day
      <input
        bind:value={assetEditForm.rental_maintenance_cost_per_day}
        inputmode="decimal"
        min="0"
        step="0.01"
        type="number"
      />
    </label>
    <label>
      Profit margin (%)
      <input
        bind:value={assetEditForm.rental_profit_margin_percent}
        inputmode="decimal"
        min="0"
        step="0.01"
        type="number"
      />
    </label>
  </div>
  <div class="readonly-field pricing-rate-output">
    <span>Price per unit/day</span>
    <strong>{formatEuro(dailyRate, 6)}</strong>
  </div>
  <button type="submit" class="compact" disabled={busy}>Update pricing</button>
</form>
