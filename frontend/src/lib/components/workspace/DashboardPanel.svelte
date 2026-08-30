<script lang="ts">
  let {
    totalInventoryValue,
    trackedAssetCount,
    stockAssetCount,
    locationCount,
    stockUnitCount,
    bookingCount,
    checkoutCount,
    returnCount,
    qrCodeCount
  }: {
    totalInventoryValue: string;
    trackedAssetCount: number;
    stockAssetCount: number;
    locationCount: number;
    stockUnitCount: number;
    bookingCount: number;
    checkoutCount: number;
    returnCount: number;
    qrCodeCount: number;
  } = $props();

  function formatMoney(value: string): string {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'EUR'
    }).format(value as Intl.StringNumericLiteral);
  }
</script>

<section class="panel dashboard-panel" aria-label="Inventory summary">
  <div class="detail-header asset-detail-header">
    <div>
      <h2>Workspace summary</h2>
      <p>Current inventory, booking, and field label counts.</p>
    </div>
  </div>

  <div class="dashboard-summary-grid">
    <div class="dashboard-value-stat">
      <span>{formatMoney(totalInventoryValue)}</span>
      <strong>Total inventory value</strong>
    </div>
    <div>
      <span>{trackedAssetCount}</span>
      <strong>Tracked assets</strong>
    </div>
    <div>
      <span>{stockAssetCount}</span>
      <strong>Stock assets</strong>
    </div>
    <div>
      <span>{locationCount}</span>
      <strong>Locations</strong>
    </div>
    <div>
      <span>{stockUnitCount}</span>
      <strong>Stock units</strong>
    </div>
    <div>
      <span>{bookingCount}</span>
      <strong>Bookings</strong>
    </div>
    <div>
      <span>{checkoutCount}</span>
      <strong>Checkouts</strong>
    </div>
    <div>
      <span>{returnCount}</span>
      <strong>Returns</strong>
    </div>
    <div>
      <span>{qrCodeCount}</span>
      <strong>QR labels</strong>
    </div>
  </div>
</section>
