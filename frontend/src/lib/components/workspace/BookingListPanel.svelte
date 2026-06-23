<script lang="ts">
  import type {
    Asset,
    AssetCondition,
    Booking,
    BookingLine,
    Checkout,
    ReturnCreate,
    User
  } from '$lib/api';

  let selectedBookingId = $state('');
  let showCheckoutPanel = $state(false);
  let showCheckinPanel = $state(false);
  let checkoutCondition = $state<AssetCondition>('unknown');
  let checkoutNotes = $state('');
  let checkinCheckoutId = $state('');
  let checkinLineId = $state('');
  let checkinQuantity = $state(1);
  let checkinCondition = $state<AssetCondition>('unknown');
  let checkinNotes = $state('');
  let loadedCheckinCheckout = $state<Checkout | null>(null);
  let checkinError = $state('');

  let {
    bookings,
    checkouts,
    assets,
    users,
    busy,
    assetName,
    locationName,
    userLabel,
    formatDateTime,
    createCheckoutForBooking,
    loadCheckoutDetails,
    createReturnForCheckout
  }: {
    bookings: Booking[];
    checkouts: Checkout[];
    assets: Asset[];
    users: User[];
    busy: boolean;
    assetName: (id: string) => string;
    locationName: (id: string | null) => string;
    userLabel: (id: string | null) => string;
    formatDateTime: (value: string) => string;
    createCheckoutForBooking: (
      bookingId: string,
      conditionOut: AssetCondition,
      notes: string
    ) => Promise<boolean>;
    loadCheckoutDetails: (checkoutId: string) => Promise<Checkout | null>;
    createReturnForCheckout: (payload: ReturnCreate) => Promise<boolean>;
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

  function checkoutLineQuantity(line: NonNullable<Checkout['lines']>[number]): string {
    if (line.quantity === null) {
      return 'exact item';
    }
    const remaining = line.quantity - line.quantity_returned;
    return `${remaining} of ${line.quantity} open`;
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

  function activeCheckoutsForBooking(bookingId: string): Checkout[] {
    return checkouts.filter(
      (checkout) => checkout.booking_id === bookingId && checkout.status !== 'returned'
    );
  }

  function checkoutButtonDisabled(booking: Booking | undefined): boolean {
    return busy || !booking || booking.status !== 'reserved';
  }

  function checkinButtonDisabled(booking: Booking | undefined): boolean {
    return busy || !booking || activeCheckoutsForBooking(booking.id).length === 0;
  }

  function resetCheckoutForm(): void {
    checkoutCondition = 'unknown';
    checkoutNotes = '';
  }

  async function submitCheckout(): Promise<void> {
    const booking = selectedBooking();
    if (!booking) {
      return;
    }
    const created = await createCheckoutForBooking(booking.id, checkoutCondition, checkoutNotes);
    showCheckoutPanel = !created;
    if (created) {
      resetCheckoutForm();
    }
  }

  async function openCheckinPanel(): Promise<void> {
    const booking = selectedBooking();
    if (!booking) {
      return;
    }
    checkinError = '';
    const activeCheckouts = activeCheckoutsForBooking(booking.id);
    checkinCheckoutId = activeCheckouts[0]?.id ?? '';
    await loadSelectedCheckinCheckout();
    showCheckinPanel = true;
  }

  async function loadSelectedCheckinCheckout(): Promise<void> {
    checkinError = '';
    loadedCheckinCheckout = null;
    checkinLineId = '';
    if (!checkinCheckoutId) {
      return;
    }
    const checkout = await loadCheckoutDetails(checkinCheckoutId);
    if (!checkout) {
      checkinError = 'Could not load checkout lines.';
      return;
    }
    loadedCheckinCheckout = checkout;
    const firstOpenLine = checkout.lines?.find((line) => {
      if (line.quantity === null) {
        return line.quantity_returned === 0;
      }
      return line.quantity_returned < line.quantity;
    });
    checkinLineId = firstOpenLine?.id ?? checkout.lines?.[0]?.id ?? '';
    checkinQuantity = 1;
  }

  function selectedCheckinLine(): NonNullable<Checkout['lines']>[number] | undefined {
    return loadedCheckinCheckout?.lines?.find((line) => line.id === checkinLineId);
  }

  function maxReturnQuantity(): number | undefined {
    const line = selectedCheckinLine();
    if (!line || line.quantity === null) {
      return undefined;
    }
    return Math.max(1, line.quantity - line.quantity_returned);
  }

  async function submitCheckin(): Promise<void> {
    const line = selectedCheckinLine();
    if (!loadedCheckinCheckout || !line) {
      checkinError = 'Choose a checkout line.';
      return;
    }
    const payload: ReturnCreate = {
      checkout_id: loadedCheckinCheckout.id,
      notes: checkinNotes || null,
      lines: [
        {
          checkout_line_id: line.id,
          quantity: line.quantity === null ? null : checkinQuantity,
          condition_in: checkinCondition,
          notes: checkinNotes || null
        }
      ]
    };
    const created = await createReturnForCheckout(payload);
    showCheckinPanel = !created;
    if (created) {
      loadedCheckinCheckout = null;
      checkinCheckoutId = '';
      checkinLineId = '';
      checkinQuantity = 1;
      checkinCondition = 'unknown';
      checkinNotes = '';
    }
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
        <div class="button-row compact-button-row">
          <button
            type="button"
            class="compact"
            disabled={checkoutButtonDisabled(selectedBooking())}
            onclick={() => (showCheckoutPanel = true)}
          >
            Check Out
          </button>
          <button
            type="button"
            class="secondary compact"
            disabled={checkinButtonDisabled(selectedBooking())}
            onclick={() => void openCheckinPanel()}
          >
            Check In
          </button>
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

        <article class="mini-list">
          <h3>Checkouts</h3>
          {#each checkouts.filter((checkout) => checkout.booking_id === selectedBookingId) as checkout}
            <div class="row-card">
              <strong>{checkout.status.replaceAll('_', ' ')}</strong>
              <span>{checkout.lines?.length ?? 0} lines</span>
            </div>
          {:else}
            <p class="empty">No checkout recorded for this booking.</p>
          {/each}
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

{#if showCheckoutPanel && selectedBooking()}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label="Check out booking"
      onsubmit={(event) => {
        event.preventDefault();
        void submitCheckout();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">{selectedBooking()?.title}</p>
          <h2>Check out</h2>
        </div>
        <button
          type="button"
          class="secondary compact"
          onclick={() => {
            showCheckoutPanel = false;
            resetCheckoutForm();
          }}
        >
          Cancel
        </button>
      </div>
      <label>
        Condition out
        <select bind:value={checkoutCondition}>
          <option value="unknown">unknown</option>
          <option value="good">good</option>
          <option value="worn">worn</option>
          <option value="damaged">damaged</option>
          <option value="needs_repair">needs repair</option>
        </select>
      </label>
      <label>Notes <textarea bind:value={checkoutNotes}></textarea></label>
      <div class="button-row">
        <button
          type="button"
          class="secondary"
          onclick={() => {
            showCheckoutPanel = false;
            resetCheckoutForm();
          }}
        >
          Cancel
        </button>
        <button type="submit" disabled={busy}>Create checkout</button>
      </div>
    </form>
  </div>
{/if}

{#if showCheckinPanel && selectedBooking()}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label="Check in booking"
      onsubmit={(event) => {
        event.preventDefault();
        void submitCheckin();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">{selectedBooking()?.title}</p>
          <h2>Check in</h2>
        </div>
        <button type="button" class="secondary compact" onclick={() => (showCheckinPanel = false)}>
          Cancel
        </button>
      </div>

      {#if checkinError}
        <p class="notice error">{checkinError}</p>
      {/if}

      <label>
        Checkout
        <select
          bind:value={checkinCheckoutId}
          required
          onchange={() => void loadSelectedCheckinCheckout()}
        >
          {#each activeCheckoutsForBooking(selectedBookingId) as checkout}
            <option value={checkout.id}>{checkout.status.replaceAll('_', ' ')}</option>
          {/each}
        </select>
      </label>

      {#if loadedCheckinCheckout?.lines?.length}
        <label>
          Line
          <select bind:value={checkinLineId} required>
            {#each loadedCheckinCheckout.lines as line}
              <option value={line.id}>
                {assetName(line.asset_id)} / {checkoutLineQuantity(line)}
              </option>
            {/each}
          </select>
        </label>

        {#if selectedCheckinLine()?.quantity !== null}
          <label>
            Quantity
            <input
              bind:value={checkinQuantity}
              type="number"
              min="1"
              max={maxReturnQuantity()}
              required
            />
          </label>
        {/if}

        <label>
          Condition in
          <select bind:value={checkinCondition}>
            <option value="unknown">unknown</option>
            <option value="good">good</option>
            <option value="worn">worn</option>
            <option value="damaged">damaged</option>
            <option value="needs_repair">needs repair</option>
          </select>
        </label>
        <label>Notes <textarea bind:value={checkinNotes}></textarea></label>
      {:else}
        <p class="empty">No checkout lines loaded.</p>
      {/if}

      <div class="button-row">
        <button type="button" class="secondary" onclick={() => (showCheckinPanel = false)}>
          Cancel
        </button>
        <button type="submit" disabled={busy || !selectedCheckinLine()}>Record check in</button>
      </div>
    </form>
  </div>
{/if}
