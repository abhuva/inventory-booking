<script lang="ts">
  import { onDestroy } from 'svelte';
  import { apiGet, type AvailabilityHeatmap } from '$lib/api';
  import { readCachedHeatmap, writeCachedHeatmap } from '$lib/heatmap-cache';
  import { readStoredBoolean, readStoredString, writeStoredValue } from '$lib/persisted';
  import type { Asset, Availability, Booking, BookingLineCreate, Location, Person } from '$lib/api';
  import type { ECharts } from 'echarts';

  let heatmapElement = $state<HTMLElement>();
  let heatmapChart = $state<ECharts | null>(null);
  let heatmap = $state<AvailabilityHeatmap | null>(null);
  let heatmapLoading = $state(false);
  let heatmapProgress = $state(0);
  let heatmapError = $state('');
  let activeHeatmapKey = '';
  let heatmapLoadToken = 0;
  let heatmapAbortController: AbortController | null = null;
  let progressTimer: ReturnType<typeof setInterval> | null = null;
  let showNewBooking = $state(false);
  let assetFilter = $state(readStoredString('stock.assetFilter'));
  let locationFilter = $state(readStoredString('stock.locationFilter'));
  let heatmapRange = $state<'month' | 'year'>(
    readStoredString('stock.heatmapRange', 'month') as 'month' | 'year'
  );
  let heatmapBucket = $state<'day' | 'week'>(
    readStoredString('stock.heatmapBucket', 'week') as 'day' | 'week'
  );
  let heatmapMonth = $state(readStoredString('stock.heatmapMonth', currentMonthValue()));
  let heatmapYear = $state(readStoredString('stock.heatmapYear', String(new Date().getFullYear())));
  let showHeatmapNumbers = $state(readStoredBoolean('stock.showHeatmapNumbers'));
  let availabilityColorMin = $state(readStoredNumber('stock.availabilityColorMin', 0));
  let availabilityColorMax = $state(readStoredNumber('stock.availabilityColorMax', 100));

  let {
    assets,
    persons,
    locations,
    bookings,
    stockAvailabilityVersion,
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
    persons: Person[];
    locations: Location[];
    bookings: Booking[];
    stockAvailabilityVersion: number;
    availability: Availability | null;
    busy: boolean;
    bookingDraft: {
      title: string;
      person_id: string;
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
    writeStoredValue('stock.assetFilter', assetFilter);
    writeStoredValue('stock.locationFilter', locationFilter);
    writeStoredValue('stock.heatmapRange', heatmapRange);
    writeStoredValue('stock.heatmapBucket', heatmapBucket);
    writeStoredValue('stock.heatmapMonth', heatmapMonth);
    writeStoredValue('stock.heatmapYear', heatmapYear);
    writeStoredValue('stock.showHeatmapNumbers', showHeatmapNumbers);
    writeStoredValue('stock.availabilityColorMin', String(availabilityColorMin));
    writeStoredValue('stock.availabilityColorMax', String(availabilityColorMax));
  });

  $effect(() => {
    const cacheKey = heatmapCacheKey();
    void loadHeatmap(cacheKey);
  });

  $effect(() => {
    const renderKey = `${assetFilter}:${showHeatmapNumbers}:${heatmap?.starts_at ?? ''}`;
    void renderKey;
    if (!heatmapElement) {
      return;
    }
    void renderHeatmap();
  });

  $effect(() => {
    const visualRangeKey = `${availabilityColorMin}:${availabilityColorMax}`;
    void visualRangeKey;
    updateHeatmapVisualRange();
  });

  onDestroy(() => {
    heatmapLoadToken += 1;
    heatmapAbortController?.abort();
    stopHeatmapProgress();
    window.removeEventListener('resize', resizeHeatmap);
    heatmapChart?.dispose();
  });

  async function loadHeatmap(cacheKey: string) {
    if (activeHeatmapKey === cacheKey) {
      return;
    }

    const cached = readCachedHeatmap(cacheKey);
    if (cached) {
      activeHeatmapKey = cacheKey;
      heatmap = cached;
      heatmapError = '';
      void renderHeatmap();
      return;
    }

    const loadToken = ++heatmapLoadToken;
    heatmapAbortController?.abort();
    heatmapAbortController = new AbortController();
    activeHeatmapKey = cacheKey;
    heatmapError = '';
    startHeatmapProgress();
    const { start, end, bucket } = heatmapRangeBounds();
    const params = new URLSearchParams({
      starts_at: start.toISOString(),
      ends_at: end.toISOString(),
      bucket
    });
    if (locationFilter) {
      params.set('location_id', locationFilter);
    }
    try {
      const loadedHeatmap = await apiGet<AvailabilityHeatmap>(
        `/bookings/availability/heatmap?${params}`,
        { signal: heatmapAbortController.signal }
      );
      if (loadToken !== heatmapLoadToken) {
        return;
      }
      heatmap = loadedHeatmap;
      writeCachedHeatmap(cacheKey, loadedHeatmap);
      heatmapProgress = Math.max(heatmapProgress, 82);
      await renderHeatmap();
      finishHeatmapProgress(loadToken);
    } catch (caught) {
      if (loadToken !== heatmapLoadToken || isAbortError(caught)) {
        return;
      }
      heatmapError =
        caught instanceof Error ? caught.message : 'Could not load stock availability.';
      activeHeatmapKey = '';
      stopHeatmapProgress();
      heatmapLoading = false;
      heatmapProgress = 0;
    }
  }

  async function renderHeatmap() {
    if (!heatmapElement || !heatmap) {
      return;
    }
    if (!heatmapChart) {
      const echarts = await import('echarts');
      heatmapChart = echarts.init(heatmapElement, undefined, { renderer: 'canvas' });
      window.addEventListener('resize', resizeHeatmap);
    }

    const visibleItems = heatmap.items.filter((item) =>
      item.name.toLocaleLowerCase().includes(assetFilter.trim().toLocaleLowerCase())
    );
    const bucket = heatmap.bucket === 'week' ? 'week' : 'day';
    const xLabels =
      visibleItems[0]?.cells.map((cell) => heatmapBucketLabel(cell.bucket_start, bucket)) ?? [];
    const yLabels = visibleItems.map((item) => item.name);
    const values = visibleItems.flatMap((item, yIndex) =>
      item.cells.map((cell, xIndex) => [
        xIndex,
        yIndex,
        normalizedAvailableQuantity(cell.available_quantity, maxQuantityForItem(item)),
        cell.available_quantity
      ])
    );

    heatmapChart.setOption({
      animation: false,
      tooltip: {
        confine: true,
        position: heatmapTooltipPosition,
        formatter(params: { data: [number, number, number, number] }) {
          const [xIndex, yIndex] = params.data;
          const item = visibleItems[yIndex];
          const cell = item?.cells[xIndex];
          if (!item || !cell) {
            return '';
          }
          return [
            `<strong>${item.name}</strong>`,
            item.asset_type === 'tracked' ? 'Tracked item' : 'Stock item',
            heatmapBucketLabel(cell.bucket_start, bucket),
            `Available: ${cell.available_quantity} ${heatmapUnitLabel(item)}`,
            `Reserved: ${cell.reserved_quantity}`,
            `Basket holds: ${cell.held_quantity}`
          ].join('<br />');
        }
      },
      grid: { top: 10, right: 18, bottom: 54, left: 132, containLabel: false },
      xAxis: {
        type: 'category',
        data: xLabels,
        splitArea: { show: true },
        axisLabel: { show: false },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'category',
        data: yLabels,
        splitArea: { show: true }
      },
      visualMap: {
        dimension: 2,
        min: 0,
        max: 1,
        show: false,
        range: [availabilityColorMin / 100, availabilityColorMax / 100],
        inRange: { color: ['#a63d2f', '#e6c75e', '#5d8a4f'] },
        outOfRange: { color: ['rgba(20, 33, 28, 0.08)'] },
        formatter(value: number) {
          return `${Math.round(value * 100)}%`;
        }
      },
      dataZoom: [
        {
          id: 'heatmap-range-slider',
          type: 'slider',
          xAxisIndex: 0,
          filterMode: 'filter',
          bottom: 6,
          height: 24,
          showDataShadow: false,
          brushSelect: false,
          moveHandleSize: 8,
          labelFormatter(value: number) {
            return xLabels[value] ?? '';
          }
        },
        {
          id: 'heatmap-range-inside',
          type: 'inside',
          xAxisIndex: 0,
          filterMode: 'filter',
          zoomOnMouseWheel: false,
          moveOnMouseMove: true,
          moveOnMouseWheel: true
        }
      ],
      series: [
        {
          type: 'heatmap',
          data: values,
          encode: { x: 0, y: 1, value: 2 },
          label: {
            show: showHeatmapNumbers,
            formatter(params: { data: [number, number, number, number] }) {
              return String(params.data[3]);
            }
          },
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

  function heatmapTooltipPosition(
    point: [number, number],
    _params: unknown,
    _dom: unknown,
    _rect: unknown,
    size: { contentSize: [number, number]; viewSize: [number, number] }
  ): [number, number] {
    const offset = 14;
    const [pointerX, pointerY] = point;
    const [contentWidth, contentHeight] = size.contentSize;
    const [viewWidth, viewHeight] = size.viewSize;
    const x =
      pointerX + contentWidth + offset > viewWidth
        ? Math.max(offset, pointerX - contentWidth - offset)
        : pointerX + offset;
    const y =
      pointerY + contentHeight + offset > viewHeight
        ? Math.max(offset, pointerY - contentHeight - offset)
        : pointerY + offset;

    return [x, y];
  }

  function updateHeatmapVisualRange(): void {
    if (!heatmapChart) {
      return;
    }
    heatmapChart.setOption(
      {
        visualMap: {
          range: [availabilityColorMin / 100, availabilityColorMax / 100]
        }
      },
      false
    );
  }

  function heatmapCacheKey(): string {
    const { bucket } = heatmapRangeBounds();
    return [
      heatmapRange,
      heatmapRange === 'month' ? heatmapMonth : heatmapYear,
      bucket,
      locationFilter || 'all',
      String(stockAvailabilityVersion)
    ].join(':');
  }

  function resizeHeatmap(): void {
    heatmapChart?.resize();
  }

  function isAbortError(value: unknown): boolean {
    return value instanceof DOMException && value.name === 'AbortError';
  }

  function startHeatmapProgress(): void {
    stopHeatmapProgress();
    heatmapLoading = true;
    heatmapProgress = 6;
    progressTimer = setInterval(() => {
      const remaining = 88 - heatmapProgress;
      heatmapProgress = Math.min(88, heatmapProgress + Math.max(2, Math.round(remaining * 0.18)));
    }, 180);
  }

  function finishHeatmapProgress(loadToken: number): void {
    stopHeatmapProgress();
    heatmapProgress = 100;
    setTimeout(() => {
      if (loadToken !== heatmapLoadToken) {
        return;
      }
      heatmapLoading = false;
      heatmapProgress = 0;
    }, 280);
  }

  function stopHeatmapProgress(): void {
    if (!progressTimer) {
      return;
    }
    clearInterval(progressTimer);
    progressTimer = null;
  }

  function maxQuantityForItem(item: AvailabilityHeatmap['items'][number]): number {
    return Math.max(
      1,
      item.total_quantity,
      ...item.cells.map((cell) => cell.total_quantity),
      ...item.cells.map((cell) => cell.available_quantity)
    );
  }

  function heatmapUnitLabel(item: AvailabilityHeatmap['items'][number]): string {
    return item.asset_type === 'tracked' ? 'item' : (item.unit_name ?? 'units');
  }

  function normalizedAvailableQuantity(availableQuantity: number, maxQuantity: number): number {
    return Math.max(0, Math.min(1, availableQuantity / maxQuantity));
  }

  function heatmapRangeBounds(): { start: Date; end: Date; bucket: 'day' | 'week' } {
    if (heatmapRange === 'year') {
      const year = Number.parseInt(heatmapYear, 10) || new Date().getFullYear();
      return {
        start: new Date(year, 0, 1),
        end: new Date(year + 1, 0, 1),
        bucket: heatmapBucket
      };
    }
    const [yearText, monthText] = heatmapMonth.split('-');
    const year = Number.parseInt(yearText, 10) || new Date().getFullYear();
    const month = (Number.parseInt(monthText, 10) || 1) - 1;
    return {
      start: new Date(year, month, 1),
      end: new Date(year, month + 1, 1),
      bucket: heatmapBucket
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

  function readStoredNumber(key: string, fallback: number): number {
    const value = Number.parseInt(readStoredString(key, String(fallback)), 10);
    return Number.isFinite(value) ? clampPercentage(value) : fallback;
  }

  function setAvailabilityColorMin(value: number): void {
    availabilityColorMin = Math.min(clampPercentage(value), availabilityColorMax);
  }

  function setAvailabilityColorMax(value: number): void {
    availabilityColorMax = Math.max(clampPercentage(value), availabilityColorMin);
  }

  function clampPercentage(value: number): number {
    return Math.max(0, Math.min(100, Math.round(value)));
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

<section class="booking-workspace heatmap-only-workspace" aria-label="Availability workspace">
  <section class="panel booking-calendar-panel heatmap-panel">
    <div class="booking-toolbar">
      <div>
        <h2>Availability</h2>
        <p>{heatmap?.items.length ?? 0} items / {bookings.length} bookings</p>
      </div>
      <div
        class="heatmap-scale-control"
        aria-label="Availability color range"
        style={`--range-start: ${availabilityColorMin}%; --range-end: ${availabilityColorMax}%;`}
      >
        <span>{availabilityColorMin}%</span>
        <div class="heatmap-scale-slider">
          <div class="heatmap-scale-track"></div>
          <div class="heatmap-scale-window"></div>
          <input
            type="range"
            min="0"
            max="100"
            value={availabilityColorMin}
            aria-label="Minimum highlighted availability"
            oninput={(event) =>
              setAvailabilityColorMin((event.currentTarget as HTMLInputElement).valueAsNumber)}
          />
          <input
            type="range"
            min="0"
            max="100"
            value={availabilityColorMax}
            aria-label="Maximum highlighted availability"
            oninput={(event) =>
              setAvailabilityColorMax((event.currentTarget as HTMLInputElement).valueAsNumber)}
          />
        </div>
        <span>{availabilityColorMax}%</span>
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
          placeholder="Filter item..."
          aria-label="Filter item"
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
        <button
          type="button"
          class="icon-toggle"
          aria-label={`Use ${heatmapBucket === 'day' ? 'weekly' : 'daily'} heatmap buckets`}
          title={heatmapBucket === 'day' ? 'Daily buckets' : 'Weekly buckets'}
          onclick={() => (heatmapBucket = heatmapBucket === 'day' ? 'week' : 'day')}
        >
          {heatmapBucket === 'day' ? 'D' : 'W'}
        </button>
        <button type="button" class="compact" onclick={openNewBooking}>+ New booking</button>
      </div>
    </div>

    <div class="heatmap-shell">
      <div class="heatmap-chart" bind:this={heatmapElement}></div>
      {#if heatmapLoading}
        <div class="heatmap-loading-panel" role="status" aria-live="polite">
          <span>Calculating availability</span>
          <strong>{Math.round(heatmapProgress)}%</strong>
          <div class="heatmap-progress-track" aria-hidden="true">
            <div style={`width: ${heatmapProgress}%`}></div>
          </div>
        </div>
      {/if}
      {#if heatmapError}
        <div class="heatmap-error-panel" role="alert">
          <strong>Could not load stock availability</strong>
          <span>{heatmapError}</span>
        </div>
      {/if}
      {#if heatmap && heatmap.items.length === 0}
        <div class="empty-detail">
          <h2>No availability data</h2>
          <p>No stock or tracked items exist for the selected location/range.</p>
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
      <label>
        Person
        <select bind:value={bookingDraft.person_id} required>
          <option value="">Choose person</option>
          {#each persons as person}
            <option value={person.id}>{person.display_name} / {person.person_type}</option>
          {/each}
        </select>
      </label>
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
        <button
          type="submit"
          disabled={busy || bookingDraft.lines.length === 0 || !bookingDraft.person_id}
        >
          Create booking
        </button>
      </div>
    </form>
  </div>
{/if}
