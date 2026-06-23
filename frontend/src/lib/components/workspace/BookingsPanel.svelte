<script lang="ts">
  import { onMount } from 'svelte';
  import type { Asset, Availability, Booking, BookingLine, Location } from '$lib/api';
  import type { Calendar as FullCalendarInstance, EventInput } from '@fullcalendar/core';

  let calendarElement = $state<HTMLElement>();
  let calendar = $state<FullCalendarInstance | null>(null);
  let selectedBookingId = $state('');
  let showNewBooking = $state(false);
  let statusFilter = $state('active');
  let assetFilter = $state('');
  let locationFilter = $state('');

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
    clearBookingAvailability,
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
    createBooking: () => Promise<boolean>;
    previewBooking: () => Promise<boolean>;
    clearBookingAvailability: () => void;
    formatDateTime: (value: string) => string;
  } = $props();

  onMount(() => {
    let instance: FullCalendarInstance | null = null;
    if (!calendarElement) {
      return;
    }
    void (async () => {
      if (!calendarElement) {
        return;
      }
      const [{ Calendar }, dayGrid, timeGrid, list, interaction] = await Promise.all([
        import('@fullcalendar/core'),
        import('@fullcalendar/daygrid'),
        import('@fullcalendar/timegrid'),
        import('@fullcalendar/list'),
        import('@fullcalendar/interaction')
      ]);
      instance = new Calendar(calendarElement, {
        plugins: [dayGrid.default, timeGrid.default, list.default, interaction.default],
        initialView: 'timeGridWeek',
        nowIndicator: true,
        height: 'auto',
        firstDay: 1,
        headerToolbar: {
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
        },
        events: calendarEvents(),
        eventClick(info) {
          selectedBookingId = String(info.event.extendedProps.bookingId ?? '');
        }
      });
      instance.render();
      calendar = instance;
    })();
    return () => instance?.destroy();
  });

  $effect(() => {
    if (!calendar) {
      return;
    }
    calendar.removeAllEvents();
    calendar.addEventSource(calendarEvents());
  });

  function calendarEvents(): EventInput[] {
    return bookings.flatMap((booking) => {
      const lines = booking.lines?.length ? booking.lines : [null];
      return lines
        .map((line) => bookingLineEvent(booking, line))
        .filter((event): event is EventInput => event !== null);
    });
  }

  function bookingLineEvent(booking: Booking, line: BookingLine | null): EventInput | null {
    if (!bookingMatchesFilters(booking, line)) {
      return null;
    }
    const asset = line ? assets.find((entry) => entry.id === line.asset_id) : undefined;
    const location = line?.location_id
      ? locations.find((entry) => entry.id === line.location_id)
      : undefined;
    const titleParts = [asset?.name ?? booking.title];
    if (line?.quantity) {
      titleParts.push(`${line.quantity}x`);
    }
    if (location) {
      titleParts.push(location.name);
    }
    return {
      id: line ? `${booking.id}:${line.id}` : booking.id,
      title: titleParts.join(' / '),
      start: booking.starts_at,
      end: booking.ends_at,
      backgroundColor: bookingColor(booking.status),
      borderColor: bookingColor(booking.status),
      extendedProps: {
        bookingId: booking.id,
        lineId: line?.id ?? null
      }
    };
  }

  function bookingMatchesFilters(booking: Booking, line: BookingLine | null): boolean {
    if (statusFilter === 'active' && !['reserved', 'checked_out'].includes(booking.status)) {
      return false;
    }
    if (statusFilter !== 'all' && statusFilter !== 'active' && booking.status !== statusFilter) {
      return false;
    }
    if (assetFilter && line?.asset_id !== assetFilter) {
      return false;
    }
    if (locationFilter && line?.location_id !== locationFilter) {
      return false;
    }
    return true;
  }

  function bookingColor(status: Booking['status']): string {
    if (status === 'cancelled') {
      return '#8b6f65';
    }
    if (status === 'checked_out') {
      return '#b26d2e';
    }
    if (status === 'completed') {
      return '#60735c';
    }
    return '#254c37';
  }

  function selectedBooking(): Booking | undefined {
    return bookings.find((booking) => booking.id === selectedBookingId);
  }

  function selectedBookingLines(): BookingLine[] {
    return selectedBooking()?.lines ?? [];
  }

  function locationName(id: string | null): string {
    return id === null
      ? 'No location'
      : (locations.find((location) => location.id === id)?.name ?? 'Unknown location');
  }

  async function submitNewBooking() {
    const created = await createBooking();
    showNewBooking = !created;
  }

  function openNewBooking() {
    clearBookingAvailability();
    showNewBooking = true;
  }
</script>

<section class="booking-workspace" aria-label="Bookings calendar workspace">
  <section class="panel booking-calendar-panel">
    <div class="booking-toolbar">
      <div>
        <h2>Booking calendar</h2>
        <p>{bookings.length} bookings</p>
      </div>
      <div class="booking-actions">
        <select bind:value={statusFilter} aria-label="Filter bookings by status">
          <option value="active">Active</option>
          <option value="all">All statuses</option>
          <option value="reserved">Reserved</option>
          <option value="checked_out">Checked out</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select bind:value={assetFilter} aria-label="Filter bookings by asset">
          <option value="">All assets</option>
          {#each assets as asset}
            <option value={asset.id}>{asset.name}</option>
          {/each}
        </select>
        <select bind:value={locationFilter} aria-label="Filter bookings by location">
          <option value="">All locations</option>
          {#each locations as location}
            <option value={location.id}>{location.name}</option>
          {/each}
        </select>
        <button type="button" class="compact" onclick={openNewBooking}>+ New booking</button>
      </div>
    </div>

    <div class="calendar-shell" bind:this={calendarElement}></div>
  </section>

  <aside class="panel booking-detail-panel" aria-label="Selected booking detail">
    {#if selectedBooking()}
      <div class="detail-header asset-detail-header">
        <div>
          <p class="eyebrow">Booking detail</p>
          <h2>{selectedBooking()?.title}</h2>
        </div>
        <span class={`status-pill status-${selectedBooking()?.status}`}
          >{selectedBooking()?.status.replaceAll('_', ' ')}</span
        >
      </div>

      <div class="physical-summary-grid">
        <article>
          <span>Start</span>
          <strong>{formatDateTime(selectedBooking()?.starts_at ?? '')}</strong>
        </article>
        <article>
          <span>End</span>
          <strong>{formatDateTime(selectedBooking()?.ends_at ?? '')}</strong>
        </article>
        <article>
          <span>Lines</span>
          <strong>{selectedBookingLines().length}</strong>
        </article>
      </div>

      <article class="mini-list">
        <h3>Reserved items</h3>
        {#each selectedBookingLines() as line}
          <div class="row-card">
            <strong>{assetName(line.asset_id)}</strong>
            <span>
              {locationName(line.location_id)}
              {#if line.quantity}
                / {line.quantity} requested
              {:else}
                / exact item
              {/if}
            </span>
          </div>
        {:else}
          <p class="empty">No booking lines loaded.</p>
        {/each}
      </article>
    {:else}
      <div class="empty-detail">
        <h2>Select booking</h2>
        <p>Click a calendar event to inspect the reservation.</p>
      </div>
    {/if}
  </aside>
</section>

{#if showNewBooking}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label="Create booking"
      onsubmit={(event) => {
        event.preventDefault();
        void submitNewBooking();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">Reservation</p>
          <h2>New booking</h2>
        </div>
        <button type="button" class="secondary compact" onclick={() => (showNewBooking = false)}
          >Cancel</button
        >
      </div>
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
              <option value={asset.id}>{asset.name} / {asset.asset_type}</option>
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
        <button type="button" class="secondary" onclick={() => (showNewBooking = false)}
          >Cancel</button
        >
        <button
          type="button"
          class="secondary"
          onclick={() => void previewBooking()}
          disabled={busy}
        >
          Check availability
        </button>
        <button type="submit" disabled={busy}>Create booking</button>
      </div>
    </form>
  </div>
{/if}
