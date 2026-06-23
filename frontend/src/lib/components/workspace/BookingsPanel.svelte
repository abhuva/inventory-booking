<script lang="ts">
  import { apiGet, type AvailabilityHeatmap } from '$lib/api';
  import type { Asset, Availability, Booking, BookingLineCreate, Location } from '$lib/api';
  import type { ECharts } from 'echarts';

  let heatmapElement = $state<HTMLElement>();
  let heatmapChart = $state<ECharts | null>(null);
  let heatmap = $state<AvailabilityHeatmap | null>(null);
  let showNewBooking = $state(false);
  let assetFilter = $state('');
  let locationFilter = $state('');
  let heatmapRange = $state<'month' | 'year'>('month');
  let heatmapMonth = $state(currentMonthValue());
  let heatmapYear = $state(String(new Date().getFullYear()));
  let showHeatmapNumbers = $state(false);

  let {
    assets,
    locations,
    bookings,
    availability,
    busy,
    bookingDraft = $bindable(),
    bookingDraftLineForm = $bindable(),
    selectedBookingDraftAsset,
    assetName,
    createBookingDraft,
    previewBookingDraft,
    addBookingDraftLineFromForm,
    removeBookingDraftLine,
    resetBookingDraft,
    clearBookingAvailability
  }: {
    assets: Asset[];
    locations: Location[];
    bookings: Booking[];
    availability: Availability | null;
    busy: boolean;
    bookingDraft: {
      title: string;
      starts_at: string;
      ends_at: string;
      notes: string;
      lines: Array<BookingLineCreate & { client_id: string }>;
    };
    bookingDraftLineForm: {
      asset_id: string;
      location_id: string;
      quantity: number;
      notes: string;
    };
    selectedBookingDraftAsset: () => Asset | undefined;
    assetName: (id: string) => string;
    createBookingDraft: () => Promise<boolean>;
    previewBookingDraft: () => Promise<boolean>;
    addBookingDraftLineFromForm: () => void;
    removeBookingDraftLine: (clientId: string) => void;
    resetBookingDraft: () => void;
    clearBookingAvailability: () => void;
  } = $props();

  $effect(() => {
    const dependencyKey = `${heatmapRange}:${heatmapMonth}:${heatmapYear}:${locationFilter}`;
    void dependencyKey;
    void loadHeatmap();
  });

  $effect(() => {
    const renderKey = `${assetFilter}:${showHeatmapNumbers}:${heatmap?.starts_at ?? ''}`;
    void renderKey;
    if (!heatmapElement) {
      return;
    }
    void renderHeatmap();
  });

  async function loadHeatmap() {
    const { start, end, bucket } = heatmapRangeBounds();
    const params = new URLSearchParams({
      starts_at: start.toISOString(),
      ends_at: end.toISOString(),
      bucket
    });
    if (locationFilter) {
      params.set('location_id', locationFilter);
    }
    heatmap = await apiGet<AvailabilityHeatmap>(`/bookings/availability/heatmap?${params}`);
    await renderHeatmap();
  }

  async function renderHeatmap() {
    if (!heatmapElement || !heatmap) {
      return;
    }
    if (!heatmapChart) {
      const echarts = await import('echarts');
      heatmapChart = echarts.init(heatmapElement, undefined, { renderer: 'canvas' });
      window.addEventListener('resize', () => heatmapChart?.resize());
    }

    const visibleItems = heatmap.items.filter((item) =>
      item.name.toLocaleLowerCase().includes(assetFilter.trim().toLocaleLowerCase())
    );
    const xLabels =
      visibleItems[0]?.cells.map((cell) =>
        heatmapBucketLabel(cell.bucket_start, heatmap?.bucket)
      ) ?? [];
    const yLabels = visibleItems.map((item) => item.name);
    const values = visibleItems.flatMap((item, yIndex) =>
      item.cells.map((cell, xIndex) => [xIndex, yIndex, cell.available_quantity])
    );
    const maxQuantity = Math.max(1, ...visibleItems.map((item) => item.total_quantity));

    heatmapChart.setOption({
      animation: false,
      tooltip: {
        position: 'top',
        formatter(params: { data: [number, number, number] }) {
          const [xIndex, yIndex] = params.data;
          const item = visibleItems[yIndex];
          const cell = item?.cells[xIndex];
          if (!item || !cell) {
            return '';
          }
          return [
            `<strong>${item.name}</strong>`,
            heatmapBucketLabel(cell.bucket_start, heatmap?.bucket),
            `Available: ${cell.available_quantity} ${item.unit_name ?? 'units'}`,
            `Reserved: ${cell.reserved_quantity}`,
            `Basket holds: ${cell.held_quantity}`
          ].join('<br />');
        }
      },
      grid: { top: 10, right: 18, bottom: 48, left: 132, containLabel: false },
      xAxis: {
        type: 'category',
        data: xLabels,
        splitArea: { show: true },
        axisLabel: { rotate: heatmapRange === 'month' ? 45 : 0 }
      },
      yAxis: {
        type: 'category',
        data: yLabels,
        splitArea: { show: true }
      },
      visualMap: {
        min: 0,
        max: maxQuantity,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        itemHeight: 72,
        inRange: { color: ['#a63d2f', '#e6c75e', '#5d8a4f'] }
      },
      series: [
        {
          type: 'heatmap',
          data: values,
          label: { show: showHeatmapNumbers },
          emphasis: {
            itemStyle: {
              shadowBlur: 8,
              shadowColor: 'rgba(20, 33, 28, 0.22)'
            }
          }
        }
      ]
    });
    requestAnimationFrame(() => heatmapChart?.resize());
  }

  function heatmapRangeBounds(): { start: Date; end: Date; bucket: 'day' | 'week' } {
    if (heatmapRange === 'year') {
      const year = Number.parseInt(heatmapYear, 10) || new Date().getFullYear();
      return {
        start: new Date(year, 0, 1),
        end: new Date(year + 1, 0, 1),
        bucket: 'week'
      };
    }
    const [yearText, monthText] = heatmapMonth.split('-');
    const year = Number.parseInt(yearText, 10) || new Date().getFullYear();
    const month = (Number.parseInt(monthText, 10) || 1) - 1;
    return {
      start: new Date(year, month, 1),
      end: new Date(year, month + 1, 1),
      bucket: 'day'
    };
  }

  function heatmapBucketLabel(value: string, bucket: 'day' | 'week' | undefined): string {
    const date = new Date(value);
    if (bucket === 'week') {
      return `W${weekNumber(date)}`;
    }
    return new Intl.DateTimeFormat(undefined, { day: '2-digit', month: '2-digit' }).format(date);
  }

  function weekNumber(date: Date): number {
    const copiedDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    copiedDate.setUTCDate(copiedDate.getUTCDate() + 4 - (copiedDate.getUTCDay() || 7));
    const yearStart = new Date(Date.UTC(copiedDate.getUTCFullYear(), 0, 1));
    return Math.ceil(((copiedDate.getTime() - yearStart.getTime()) / 86_400_000 + 1) / 7);
  }

  function currentMonthValue(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }

  function locationName(id: string | null): string {
    return id === null
      ? 'No location'
      : (locations.find((location) => location.id === id)?.name ?? 'Unknown location');
  }

  async function submitNewBooking() {
    const created = await createBookingDraft();
    showNewBooking = !created;
  }

  function openNewBooking() {
    clearBookingAvailability();
    if (!bookingDraft.starts_at || !bookingDraft.ends_at) {
      const start = new Date();
      start.setHours(start.getHours() + 1, 0, 0, 0);
      const end = new Date(start);
      end.setHours(end.getHours() + 2);
      bookingDraft.starts_at = toDateTimeLocalValue(start);
      bookingDraft.ends_at = toDateTimeLocalValue(end);
    }
    showNewBooking = true;
  }

  function toDateTimeLocalValue(date: Date): string {
    const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return offsetDate.toISOString().slice(0, 16);
  }
</script>

<section class="booking-workspace heatmap-only-workspace" aria-label="Stock availability workspace">
  <section class="panel booking-calendar-panel heatmap-panel">
    <div class="booking-toolbar">
      <div>
        <h2>Stock availability</h2>
        <p>{heatmap?.items.length ?? 0} stock items / {bookings.length} bookings</p>
      </div>
      <div class="booking-actions">
        <select bind:value={heatmapRange} aria-label="Heatmap range">
          <option value="month">Month</option>
          <option value="year">Year</option>
        </select>
        {#if heatmapRange === 'month'}
          <input bind:value={heatmapMonth} type="month" aria-label="Heatmap month" />
        {:else}
          <input
            bind:value={heatmapYear}
            type="number"
            min="2020"
            max="2100"
            aria-label="Heatmap year"
          />
        {/if}
        <input
          bind:value={assetFilter}
          type="search"
          placeholder="Filter stock item..."
          aria-label="Filter stock item"
        />
        <select bind:value={locationFilter} aria-label="Filter bookings by location">
          <option value="">All locations</option>
          {#each locations as location}
            <option value={location.id}>{location.name}</option>
          {/each}
        </select>
        <label class="inline-check">
          <input bind:checked={showHeatmapNumbers} type="checkbox" />
          Numbers
        </label>
        <button type="button" class="compact" onclick={openNewBooking}>+ New booking</button>
      </div>
    </div>

    <div class="heatmap-shell" bind:this={heatmapElement}>
      {#if heatmap && heatmap.items.length === 0}
        <div class="empty-detail">
          <h2>No stock data</h2>
          <p>No stock items exist for the selected location/range.</p>
        </div>
      {/if}
    </div>
  </section>
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
      <label>Title <input bind:value={bookingDraft.title} required /></label>
      <div class="split-fields">
        <label>
          Start
          <input bind:value={bookingDraft.starts_at} type="datetime-local" required />
        </label>
        <label>
          End
          <input bind:value={bookingDraft.ends_at} type="datetime-local" required />
        </label>
      </div>
      <label>Notes <textarea bind:value={bookingDraft.notes}></textarea></label>

      <div class="booking-builder">
        <article class="mini-list">
          <h3>Add item</h3>
          <div class="split-fields">
            <label>
              Asset
              <select bind:value={bookingDraftLineForm.asset_id} required>
                <option value="">Choose asset</option>
                {#each assets as asset}
                  <option value={asset.id}>{asset.name} / {asset.asset_type}</option>
                {/each}
              </select>
            </label>
            {#if selectedBookingDraftAsset()?.asset_type === 'stock'}
              <label>
                Location
                <select bind:value={bookingDraftLineForm.location_id} required>
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
          {#if selectedBookingDraftAsset()?.asset_type === 'stock'}
            <label>
              Quantity
              <input bind:value={bookingDraftLineForm.quantity} type="number" min="1" required />
            </label>
          {/if}
          <label>Line notes <textarea bind:value={bookingDraftLineForm.notes}></textarea></label>
          <button
            type="button"
            class="compact"
            disabled={busy}
            onclick={addBookingDraftLineFromForm}
          >
            Add line
          </button>
        </article>

        <article class="mini-list">
          <h3>Bundle lines</h3>
          {#each bookingDraft.lines as line}
            <div class="row-card">
              <strong>{assetName(line.asset_id)}</strong>
              <span>
                {locationName(line.location_id ?? null)}
                {#if line.quantity}
                  / {line.quantity} requested
                {:else}
                  / exact item
                {/if}
              </span>
              <button
                type="button"
                class="secondary compact"
                disabled={busy}
                onclick={() => removeBookingDraftLine(line.client_id)}
              >
                Remove
              </button>
            </div>
          {:else}
            <p class="empty">No items added yet.</p>
          {/each}
        </article>
      </div>

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
          onclick={() => void previewBookingDraft()}
          disabled={busy}
        >
          Check availability
        </button>
        <button type="button" class="secondary" onclick={resetBookingDraft} disabled={busy}>
          Clear bundle
        </button>
        <button type="submit" disabled={busy || bookingDraft.lines.length === 0}>
          Create booking
        </button>
      </div>
    </form>
  </div>
{/if}
