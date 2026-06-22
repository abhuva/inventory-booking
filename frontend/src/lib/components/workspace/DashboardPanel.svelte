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

<section class="stats-grid" aria-label="Inventory summary">
  <article>
    <span>{trackedAssetCount}</span>
    <p>tracked assets</p>
  </article>
  <article>
    <span>{stockAssetCount}</span>
    <p>stock assets</p>
  </article>
  <article>
    <span>{locationCount}</span>
    <p>locations</p>
  </article>
  <article>
    <span>{stockUnitCount}</span>
    <p>stock units</p>
  </article>
  <article>
    <span>{bookingCount}</span>
    <p>bookings</p>
  </article>
  <article>
    <span>{checkoutCount}</span>
    <p>checkouts</p>
  </article>
  <article>
    <span>{returnCount}</span>
    <p>returns</p>
  </article>
  <article>
    <span>{qrCodeCount}</span>
    <p>QR labels</p>
  </article>
</section>
