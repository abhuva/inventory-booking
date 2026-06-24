<script lang="ts">
  import type {
    Asset,
    AssetCondition,
    Booking,
    BookingLine,
    BookingStatus,
    BookingUpdate,
    Checkout,
    Person,
    ReturnCreate,
    User
  } from '$lib/api';
  import { readStoredBoolean, readStoredString, writeStoredValue } from '$lib/persisted';

  const bookingStatuses: BookingStatus[] = ['reserved', 'cancelled', 'checked_out', 'completed'];
  const noLocationFilterValue = '__none';

  type SortKey = 'title' | 'status' | 'created_at' | 'starts_at' | 'lines';
  type SortDirection = 'asc' | 'desc';

  let selectedBookingId = $state('');
  let statusFilter = $state<BookingStatus | ''>(
    readStoredString('bookings.statusFilter') as BookingStatus | ''
  );
  let locationFilter = $state(readStoredString('bookings.locationFilter'));
  let sortKey = $state<SortKey | ''>(readStoredString('bookings.sortKey') as SortKey | '');
  let sortDirection = $state<SortDirection>(
    readStoredString('bookings.sortDirection', 'asc') as SortDirection
  );
  let compactBookedItems = $state(readStoredBoolean('bookings.compactBookedItems'));
  let bookingEditForm = $state<{
    status: BookingStatus;
    person_id: string;
    starts_at: string;
    ends_at: string;
  }>({
    status: 'reserved',
    person_id: '',
    starts_at: '',
    ends_at: ''
  });
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
    persons,
    users,
    busy,
    assetName,
    locationName,
    personName,
    userLabel,
    formatDateTime,
    updateBooking,
    createCheckoutForBooking,
    loadCheckoutDetails,
    createReturnForCheckout,
    deleteBooking
  }: {
    bookings: Booking[];
    checkouts: Checkout[];
    assets: Asset[];
    persons: Person[];
    users: User[];
    busy: boolean;
    assetName: (id: string) => string;
    locationName: (id: string | null) => string;
    personName: (id: string | null) => string;
    userLabel: (id: string | null) => string;
    formatDateTime: (value: string) => string;
    updateBooking: (bookingId: string, payload: BookingUpdate) => Promise<boolean>;
    createCheckoutForBooking: (
      bookingId: string,
      conditionOut: AssetCondition,
      notes: string
    ) => Promise<boolean>;
    loadCheckoutDetails: (checkoutId: string) => Promise<Checkout | null>;
    createReturnForCheckout: (payload: ReturnCreate) => Promise<boolean>;
    deleteBooking: (bookingId: string) => Promise<boolean>;
  } = $props();

  $effect(() => {
    writeStoredValue('bookings.statusFilter', statusFilter);
    writeStoredValue('bookings.locationFilter', locationFilter);
    writeStoredValue('bookings.sortKey', sortKey);
    writeStoredValue('bookings.sortDirection', sortDirection);
    writeStoredValue('bookings.compactBookedItems', compactBookedItems);
  });

  $effect(() => {
    const visibleBookings = displayedBookings();
    if (selectedBookingId && visibleBookings.some((booking) => booking.id === selectedBookingId)) {
      return;
    }
    selectedBookingId = visibleBookings[0]?.id ?? '';
  });

  $effect(() => {
    const booking = selectedBooking();
    if (!booking) {
      return;
    }
    bookingEditForm = {
      status: booking.status,
      person_id: booking.person_id ?? '',
      starts_at: toDateTimeLocalValue(booking.starts_at),
      ends_at: toDateTimeLocalValue(booking.ends_at)
    };
  });

  function selectedBooking(): Booking | undefined {
    return bookings.find((booking) => booking.id === selectedBookingId);
  }

  async function confirmDeleteBooking(): Promise<void> {
    const booking = selectedBooking();
    if (!booking) {
      return;
    }
    const checkoutCount = checkouts.filter((checkout) => checkout.booking_id === booking.id).length;
    const lineCount = booking.lines?.length ?? 0;
    const confirmed = window.confirm(
      [
        `Delete booking "${booking.title}"?`,
        '',
        `${lineCount} booked item rows and ${checkoutCount} related checkouts will be removed.`,
        'Related return records for those checkouts will also be removed.',
        '',
        'This cannot be undone.'
      ].join('\n')
    );
    if (confirmed) {
      await deleteBooking(booking.id);
    }
  }

  function selectBooking(bookingId: string): void {
    selectedBookingId = bookingId;
  }

  function bookingStatusClass(status: string): string {
    return `status-pill status-booking-${status}`;
  }

  function filteredBookings(): Booking[] {
    return bookings.filter((booking) => {
      if (statusFilter && booking.status !== statusFilter) {
        return false;
      }
      if (!locationFilter) {
        return true;
      }
      const lines = booking.lines ?? [];
      if (locationFilter === noLocationFilterValue) {
        return lines.some((line) => line.location_id === null);
      }
      return lines.some((line) => line.location_id === locationFilter);
    });
  }

  function displayedBookings(): Booking[] {
    const visibleBookings = filteredBookings();
    if (!sortKey) {
      return visibleBookings;
    }
    return [...visibleBookings].sort((left, right) => compareBookings(left, right));
  }

  function compareBookings(left: Booking, right: Booking): number {
    const direction = sortDirection === 'asc' ? 1 : -1;
    let comparison = 0;
    if (sortKey === 'title') {
      comparison = left.title.localeCompare(right.title);
    } else if (sortKey === 'status') {
      comparison = left.status.localeCompare(right.status);
    } else if (sortKey === 'created_at') {
      comparison = Date.parse(left.created_at) - Date.parse(right.created_at);
    } else if (sortKey === 'starts_at') {
      comparison = Date.parse(left.starts_at) - Date.parse(right.starts_at);
    } else if (sortKey === 'lines') {
      comparison = (left.lines?.length ?? 0) - (right.lines?.length ?? 0);
    }
    return comparison * direction;
  }

  function toggleSort(key: SortKey): void {
    if (sortKey !== key) {
      sortKey = key;
      sortDirection = 'asc';
      return;
    }
    if (sortDirection === 'asc') {
      sortDirection = 'desc';
      return;
    }
    sortKey = '';
    sortDirection = 'asc';
  }

  function sortIndicator(key: SortKey): string {
    if (sortKey !== key) {
      return '';
    }
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  }

  function sortLabel(label: string, key: SortKey): string {
    if (sortKey !== key) {
      return `${label}: not sorted`;
    }
    return `${label}: sorted ${sortDirection === 'asc' ? 'ascending' : 'descending'}`;
  }

  function locationFilterOptions(): string[] {
    const locationIds = new Set<string>();
    for (const booking of bookings) {
      for (const line of booking.lines ?? []) {
        locationIds.add(line.location_id ?? noLocationFilterValue);
      }
    }
    return [...locationIds].sort((left, right) =>
      locationFilterLabel(left).localeCompare(locationFilterLabel(right))
    );
  }

  function locationFilterLabel(value: string): string {
    return value === noLocationFilterValue ? 'No location / exact item' : locationName(value);
  }

  function resetFilters(): void {
    statusFilter = '';
    locationFilter = '';
  }

  function toDateTimeLocalValue(value: string): string {
    if (!value) {
      return '';
    }
    const date = new Date(value);
    const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return offsetDate.toISOString().slice(0, 16);
  }

  async function submitBookingUpdate(): Promise<void> {
    const booking = selectedBooking();
    if (!booking) {
      return;
    }
    await updateBooking(booking.id, {
      status: bookingEditForm.status,
      person_id: bookingEditForm.person_id || null,
      starts_at: new Date(bookingEditForm.starts_at).toISOString(),
      ends_at: new Date(bookingEditForm.ends_at).toISOString()
    });
  }

  function bookingLineQuantity(line: BookingLine): string {
    return line.quantity === null ? 'exact item' : `${line.quantity} requested`;
  }

  function compactBookingLine(line: BookingLine): string {
    const quantity = line.quantity === null ? '1' : String(line.quantity);
    return `${quantity} x ${assetName(line.asset_id)} from ${locationName(line.location_id)} (${lineDateRange(line)})`;
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

  function lineDateRange(line: BookingLine): string {
    return `${formatDateTime(line.starts_at)} - ${formatDateTime(line.ends_at)}`;
  }

  function requestedByName(booking: Booking | undefined): string {
    if (!booking) {
      return 'Unknown user';
    }
    return users.some((user) => user.id === booking.requested_by_user_id)
      ? userLabel(booking.requested_by_user_id)
      : 'Unknown user';
  }

  function bookingPersonName(booking: Booking | undefined): string {
    if (!booking) {
      return 'No person';
    }
    return persons.some((person) => person.id === booking.person_id)
      ? personName(booking.person_id)
      : 'No person';
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
        <p>{filteredBookings().length} shown / {bookings.length} total</p>
      </div>
      <div class="booking-list-filters" aria-label="Filter bookings">
        <select bind:value={statusFilter} aria-label="Filter bookings by status">
          <option value="">All statuses</option>
          {#each bookingStatuses as status}
            <option value={status}>{status.replaceAll('_', ' ')}</option>
          {/each}
        </select>
        <select bind:value={locationFilter} aria-label="Filter bookings by location">
          <option value="">All locations</option>
          {#each locationFilterOptions() as locationId}
            <option value={locationId}>{locationFilterLabel(locationId)}</option>
          {/each}
        </select>
        <button
          type="button"
          class="secondary compact"
          disabled={!statusFilter && !locationFilter}
          onclick={resetFilters}
        >
          Reset
        </button>
      </div>
    </div>

    <div class="asset-table-wrap">
      <table class="asset-table">
        <thead>
          <tr>
            <th>
              <button
                type="button"
                class="sortable-header-button"
                aria-label={sortLabel('Booking', 'title')}
                onclick={() => toggleSort('title')}
              >
                Booking{sortIndicator('title')}
              </button>
            </th>
            <th>
              <button
                type="button"
                class="sortable-header-button"
                aria-label={sortLabel('Status', 'status')}
                onclick={() => toggleSort('status')}
              >
                Status{sortIndicator('status')}
              </button>
            </th>
            <th>
              <button
                type="button"
                class="sortable-header-button"
                aria-label={sortLabel('Created', 'created_at')}
                onclick={() => toggleSort('created_at')}
              >
                Created{sortIndicator('created_at')}
              </button>
            </th>
            <th>
              <button
                type="button"
                class="sortable-header-button"
                aria-label={sortLabel('Start', 'starts_at')}
                onclick={() => toggleSort('starts_at')}
              >
                Start{sortIndicator('starts_at')}
              </button>
            </th>
            <th>
              <button
                type="button"
                class="sortable-header-button"
                aria-label={sortLabel('Lines', 'lines')}
                onclick={() => toggleSort('lines')}
              >
                Lines{sortIndicator('lines')}
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {#each displayedBookings() as booking}
            <tr
              class:selected-row={booking.id === selectedBookingId}
              onclick={() => selectBooking(booking.id)}
            >
              <td>
                <strong>{booking.title}</strong>
                <span>{bookingPersonName(booking)}</span>
              </td>
              <td>
                <span class={bookingStatusClass(booking.status)}>
                  {booking.status.replaceAll('_', ' ')}
                </span>
              </td>
              <td>{formatDateTime(booking.created_at)}</td>
              <td>{formatDateTime(booking.starts_at)}</td>
              <td>{booking.lines?.length ?? 0}</td>
            </tr>
          {:else}
            <tr>
              <td colspan="5" class="empty">
                {bookings.length ? 'No bookings match these filters.' : 'No bookings yet.'}
              </td>
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
          <button
            type="button"
            class="danger compact"
            disabled={busy}
            onclick={() => void confirmDeleteBooking()}
          >
            Delete
          </button>
        </div>
      </div>

      <div class="detail-tab-panel">
        <form
          class="booking-field-grid"
          aria-label="Booking metadata"
          onsubmit={(event) => {
            event.preventDefault();
            void submitBookingUpdate();
          }}
        >
          <label class="compact-field-row">
            Status
            <select bind:value={bookingEditForm.status}>
              {#each bookingStatuses as status}
                <option value={status}>{status.replaceAll('_', ' ')}</option>
              {/each}
            </select>
          </label>
          <label class="compact-field-row">
            Person
            <select bind:value={bookingEditForm.person_id} required>
              <option value="">Choose person</option>
              {#each persons as person}
                <option value={person.id}>{person.display_name} / {person.person_type}</option>
              {/each}
            </select>
          </label>
          <label class="compact-field-row">
            Requested by
            <input value={requestedByName(selectedBooking())} readonly />
          </label>
          <label class="compact-field-row">
            Created
            <input value={formatDateTime(selectedBooking()?.created_at ?? '')} readonly />
          </label>
          <label class="compact-field-row">
            Start
            <input bind:value={bookingEditForm.starts_at} type="datetime-local" required />
          </label>
          <label class="compact-field-row">
            End
            <input bind:value={bookingEditForm.ends_at} type="datetime-local" required />
          </label>
          <div class="button-row compact-button-row booking-field-actions">
            <button type="submit" class="compact" disabled={busy || !bookingEditForm.person_id}>
              Update booking
            </button>
          </div>
        </form>

        <article class="mini-list">
          <div class="mini-list-heading">
            <h3>Booked items</h3>
            <button
              type="button"
              class="secondary micro-button icon-toggle"
              aria-label={compactBookedItems
                ? 'Show expanded booked items'
                : 'Show compact booked items'}
              title={compactBookedItems ? 'Expanded view' : 'Compact view'}
              onclick={() => (compactBookedItems = !compactBookedItems)}
            >
              {compactBookedItems ? '☰' : '≡'}
            </button>
          </div>
          {#each selectedBooking()?.lines ?? [] as line}
            {#if compactBookedItems}
              <div class="row-card compact-booked-item">
                <span>{compactBookingLine(line)}</span>
              </div>
            {:else}
              <div class="row-card">
                <strong>{assetName(line.asset_id)}</strong>
                <span>
                  {bookingLineMode(line)} / {locationName(line.location_id)} /
                  {bookingLineQuantity(line)}
                </span>
                <span>{lineDateRange(line)}</span>
                {#if line.notes}
                  <small>{line.notes}</small>
                {/if}
              </div>
            {/if}
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
