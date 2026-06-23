<script lang="ts">
  import type { Asset, Booking, BookingLine, User } from '$lib/api';

  let selectedBookingId = $state('');

  let {
    bookings,
    assets,
    users,
    assetName,
    locationName,
    userLabel,
    formatDateTime
  }: {
    bookings: Booking[];
    assets: Asset[];
    users: User[];
    assetName: (id: string) => string;
    locationName: (id: string | null) => string;
    userLabel: (id: string | null) => string;
    formatDateTime: (value: string) => string;
  } = $props();

  $effect(() => {
    if (selectedBookingId && bookings.some((booking) => booking.id === selectedBookingId)) {
      return;
    }
    selectedBookingId = bookings[0]?.id ?? '';
  });

  function selectedBooking(): Booking | undefined {
    return bookings.find((booking) => booking.id === selectedBookingId);
  }

  function selectBooking(bookingId: string): void {
    selectedBookingId = bookingId;
  }

  function bookingStatusClass(status: string): string {
    return `status-pill status-booking-${status}`;
  }

  function bookingLineQuantity(line: BookingLine): string {
    return line.quantity === null ? 'exact item' : `${line.quantity} requested`;
  }

  function bookingLineMode(line: BookingLine): string {
    const asset = assets.find((entry) => entry.id === line.asset_id);
    return asset?.asset_type === 'stock' ? 'stock' : 'tracked';
  }

  function requestedByName(booking: Booking | undefined): string {
    if (!booking) {
      return 'Unknown user';
    }
    return users.some((user) => user.id === booking.requested_by_user_id)
      ? userLabel(booking.requested_by_user_id)
      : 'Unknown user';
  }
</script>

<section class="inventory-workspace" aria-label="Bookings workspace">
  <section class="panel inventory-table-panel">
    <div class="inventory-toolbar">
      <div>
        <h2>Bookings</h2>
        <p>{bookings.length} total</p>
      </div>
    </div>

    <div class="asset-table-wrap">
      <table class="asset-table">
        <thead>
          <tr>
            <th>Booking</th>
            <th>Status</th>
            <th>Start</th>
            <th>Lines</th>
          </tr>
        </thead>
        <tbody>
          {#each bookings as booking}
            <tr
              class:selected-row={booking.id === selectedBookingId}
              onclick={() => selectBooking(booking.id)}
            >
              <td>
                <strong>{booking.title}</strong>
                <span>{requestedByName(booking)}</span>
              </td>
              <td>
                <span class={bookingStatusClass(booking.status)}>
                  {booking.status.replaceAll('_', ' ')}
                </span>
              </td>
              <td>{formatDateTime(booking.starts_at)}</td>
              <td>{booking.lines?.length ?? 0}</td>
            </tr>
          {:else}
            <tr>
              <td colspan="4" class="empty">No bookings yet.</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <aside class="panel inventory-detail-panel" aria-label="Selected booking details">
    {#if selectedBooking()}
      <div class="detail-header asset-detail-header">
        <div>
          <p class="eyebrow">Booking detail</p>
          <h2>{selectedBooking()?.title}</h2>
        </div>
      </div>

      <div class="detail-tab-panel">
        <div class="physical-summary-grid">
          <article>
            <span>Status</span>
            <strong>{selectedBooking()?.status.replaceAll('_', ' ')}</strong>
          </article>
          <article>
            <span>Requested by</span>
            <strong>{requestedByName(selectedBooking())}</strong>
          </article>
          <article>
            <span>Start</span>
            <strong>{formatDateTime(selectedBooking()?.starts_at ?? '')}</strong>
          </article>
          <article>
            <span>End</span>
            <strong>{formatDateTime(selectedBooking()?.ends_at ?? '')}</strong>
          </article>
        </div>

        <article class="mini-list">
          <h3>Booked items</h3>
          {#each selectedBooking()?.lines ?? [] as line}
            <div class="row-card">
              <strong>{assetName(line.asset_id)}</strong>
              <span>
                {bookingLineMode(line)} / {locationName(line.location_id)} /
                {bookingLineQuantity(line)}
              </span>
              {#if line.notes}
                <small>{line.notes}</small>
              {/if}
            </div>
          {:else}
            <p class="empty">No lines are attached to this booking.</p>
          {/each}
        </article>

        <article class="mini-list">
          <h3>Notes</h3>
          <p class="field-note">{selectedBooking()?.notes || 'No notes.'}</p>
        </article>
      </div>
    {:else}
      <div class="empty-detail">
        <h2>Select a booking</h2>
        <p>Click a row in the table to view booking details.</p>
      </div>
    {/if}
  </aside>
</section>
