<script lang="ts">
  import type { Asset, Availability, Booking, Location } from '$lib/api';

  let {
    assets,
    locations,
    bookings,
    availability,
    busy,
    bookingForm = $bindable(),
    selectedBookingAsset,
    assetName,
    createBooking,
    previewBooking,
    formatDateTime
  }: {
    assets: Asset[];
    locations: Location[];
    bookings: Booking[];
    availability: Availability | null;
    busy: boolean;
    bookingForm: {
      title: string;
      starts_at: string;
      ends_at: string;
      asset_id: string;
      location_id: string;
      quantity: number;
    };
    selectedBookingAsset: () => Asset | undefined;
    assetName: (id: string) => string;
    createBooking: () => void;
    previewBooking: () => void;
    formatDateTime: (value: string) => string;
  } = $props();
</script>

<section class="forms-grid" aria-label="Booking controls">
  <form
    class="panel form-panel wide"
    onsubmit={(event) => {
      event.preventDefault();
      createBooking();
    }}
  >
    <h2>Booking</h2>
    <label>Title <input bind:value={bookingForm.title} required /></label>
    <div class="split-fields">
      <label>
        Start
        <input bind:value={bookingForm.starts_at} type="datetime-local" required />
      </label>
      <label>
        End
        <input bind:value={bookingForm.ends_at} type="datetime-local" required />
      </label>
    </div>
    <div class="split-fields">
      <label>
        Asset
        <select bind:value={bookingForm.asset_id} required>
          <option value="">Choose asset</option>
          {#each assets as asset}
            <option value={asset.id}>{asset.name} · {asset.asset_type}</option>
          {/each}
        </select>
      </label>
      {#if selectedBookingAsset()?.asset_type === 'stock'}
        <label>
          Location
          <select bind:value={bookingForm.location_id} required>
            <option value="">Choose location</option>
            {#each locations as location}
              <option value={location.id}>{location.name}</option>
            {/each}
          </select>
        </label>
      {:else}
        <label>
          Location
          <input value="Tracked assets reserve the exact item" disabled />
        </label>
      {/if}
    </div>
    {#if selectedBookingAsset()?.asset_type === 'stock'}
      <label>
        Quantity
        <input bind:value={bookingForm.quantity} type="number" min="1" required />
      </label>
    {/if}
    {#if availability}
      <div class:availability-ok={availability.available} class="availability-result">
        <strong>{availability.available ? 'Available' : 'Conflict'}</strong>
        {#each availability.lines as line}
          <span>
            {assetName(line.asset_id)}:
            {line.available
              ? `available${line.available_quantity === null ? '' : ` (${line.available_quantity})`}`
              : line.reason}
          </span>
        {/each}
      </div>
    {/if}
    <div class="button-row">
      <button type="button" class="secondary" onclick={previewBooking} disabled={busy}>
        Preview availability
      </button>
      <button type="submit" disabled={busy}>Create booking</button>
    </div>
  </form>
</section>

<section class="data-grid" aria-label="Booking lists">
  <article class="panel list-panel">
    <h2>Bookings</h2>
    {#each bookings as booking}
      <div class="row-card">
        <strong>{booking.title}</strong>
        <span
          >{booking.status} · {formatDateTime(booking.starts_at)} to {formatDateTime(
            booking.ends_at
          )}</span
        >
      </div>
    {:else}
      <p class="empty">No bookings yet.</p>
    {/each}
  </article>
</section>
