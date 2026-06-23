<script lang="ts">
  let {
    trackedAssetCount,
    stockAssetCount,
    locationCount,
    stockUnitCount,
    bookingCount,
    checkoutCount,
    returnCount,
    qrCodeCount
  }: {
    trackedAssetCount: number;
    stockAssetCount: number;
    locationCount: number;
    stockUnitCount: number;
    bookingCount: number;
    checkoutCount: number;
    returnCount: number;
    qrCodeCount: number;
  } = $props();
</script>

<section class="panel dashboard-panel" aria-label="Inventory summary">
  <div class="detail-header asset-detail-header">
    <div>
      <h2>Workspace summary</h2>
      <p>Current inventory, booking, and field label counts.</p>
    </div>
  </div>

  <div class="dashboard-summary-grid">
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
