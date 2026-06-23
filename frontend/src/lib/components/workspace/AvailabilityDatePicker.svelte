<script lang="ts">
  import { apiGet, type AvailabilityDay, type AvailabilityDays } from '$lib/api';

  type CalendarDay = {
    key: string;
    label: string;
    inMonth: boolean;
    availability: AvailabilityDay | null;
  };

  let {
    assetId,
    locationId,
    quantity,
    initialStart,
    initialEnd,
    assetLabel,
    onAccept,
    onCancel
  }: {
    assetId: string;
    locationId: string | null;
    quantity: number;
    initialStart: string;
    initialEnd: string;
    assetLabel: string;
    onAccept: (startsAt: string, endsAt: string) => void;
    onCancel: () => void;
  } = $props();

  let viewMonth = $state(new Date());
  let selectedStart = $state('');
  let selectedEnd = $state('');
  let availability = $state<AvailabilityDays | null>(null);
  let loading = $state(false);
  let error = $state('');
  let initialized = $state(false);

  $effect(() => {
    if (initialized) {
      return;
    }
    viewMonth = monthStartFromValue(initialStart);
    selectedStart = dateKeyFromValue(initialStart);
    selectedEnd = inclusiveEndKeyFromValue(initialEnd);
    initialized = true;
  });

  $effect(() => {
    const _assetId = assetId;
    const _locationId = locationId;
    const _quantity = quantity;
    const _month = monthKey(viewMonth);
    if (!_assetId || _quantity < 1 || !_month) {
      return;
    }
    void loadAvailability();
  });

  async function loadAvailability() {
    loading = true;
    error = '';
    try {
      const start = new Date(Date.UTC(viewMonth.getUTCFullYear(), viewMonth.getUTCMonth(), 1));
      const end = new Date(Date.UTC(viewMonth.getUTCFullYear(), viewMonth.getUTCMonth() + 1, 1));
      const params = new URLSearchParams({
        asset_id: assetId,
        starts_at: start.toISOString(),
        ends_at: end.toISOString(),
        quantity: String(quantity)
      });
      if (locationId) {
        params.set('location_id', locationId);
      }
      availability = await apiGet<AvailabilityDays>(`/bookings/availability/days?${params}`);
    } catch (caught) {
      error = caught instanceof Error ? caught.message : 'Could not load availability.';
    } finally {
      loading = false;
    }
  }

  function calendarDays(): CalendarDay[] {
    const start = new Date(Date.UTC(viewMonth.getUTCFullYear(), viewMonth.getUTCMonth(), 1));
    const firstWeekday = (start.getUTCDay() + 6) % 7;
    const gridStart = new Date(start);
    gridStart.setUTCDate(gridStart.getUTCDate() - firstWeekday);
    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(gridStart);
      date.setUTCDate(gridStart.getUTCDate() + index);
      const key = dateKey(date);
      return {
        key,
        label: String(date.getUTCDate()),
        inMonth: date.getUTCMonth() === viewMonth.getUTCMonth(),
        availability: availabilityForDay(key)
      };
    });
  }

  function availabilityForDay(key: string): AvailabilityDay | null {
    return availability?.days.find((day) => day.bucket_start.slice(0, 10) === key) ?? null;
  }

  function chooseDay(key: string) {
    if (!selectedStart || selectedEnd) {
      selectedStart = key;
      selectedEnd = '';
      return;
    }
    if (key < selectedStart) {
      selectedEnd = selectedStart;
      selectedStart = key;
      return;
    }
    selectedEnd = key;
  }

  function previousMonth() {
    viewMonth = new Date(Date.UTC(viewMonth.getUTCFullYear(), viewMonth.getUTCMonth() - 1, 1));
  }

  function nextMonth() {
    viewMonth = new Date(Date.UTC(viewMonth.getUTCFullYear(), viewMonth.getUTCMonth() + 1, 1));
  }

  function acceptSelection() {
    if (!selectedStart || !selectedEnd || selectedConflictCount() > 0) {
      return;
    }
    onAccept(`${selectedStart}T00:00`, `${nextDateKey(selectedEnd)}T00:00`);
  }

  function selectedConflictCount(): number {
    if (!selectedStart || !selectedEnd) {
      return 0;
    }
    return selectedAvailabilityDays().filter((day) => !day.available).length;
  }

  function selectedAvailabilityDays(): AvailabilityDay[] {
    if (!selectedStart || !selectedEnd) {
      return [];
    }
    return (availability?.days ?? []).filter((day) => {
      const key = day.bucket_start.slice(0, 10);
      return key >= selectedStart && key <= selectedEnd;
    });
  }

  function isSelected(day: CalendarDay): boolean {
    if (!selectedStart) {
      return false;
    }
    if (!selectedEnd) {
      return day.key === selectedStart;
    }
    return day.key >= selectedStart && day.key <= selectedEnd;
  }

  function dayClasses(day: CalendarDay): string {
    const classes = ['availability-day'];
    if (!day.inMonth) {
      classes.push('outside-month');
    }
    if (day.availability && !day.availability.available) {
      classes.push('unavailable-day');
    }
    if (isSelected(day)) {
      classes.push('selected-day');
      if (day.availability && !day.availability.available) {
        classes.push('selected-conflict-day');
      }
    }
    return classes.join(' ');
  }

  function monthTitle(): string {
    return new Intl.DateTimeFormat(undefined, {
      month: 'long',
      year: 'numeric',
      timeZone: 'UTC'
    }).format(viewMonth);
  }

  function availabilityLabel(day: CalendarDay): string {
    if (!day.availability) {
      return '';
    }
    return `${day.availability.available_quantity}/${day.availability.total_quantity}`;
  }

  function rangeLabel(): string {
    if (!selectedStart) {
      return 'Click a start date.';
    }
    if (!selectedEnd) {
      return `${selectedStart} selected. Click an end date.`;
    }
    return `${selectedStart} through ${selectedEnd}`;
  }

  function dateKey(date: Date): string {
    return date.toISOString().slice(0, 10);
  }

  function dateKeyFromValue(value: string): string {
    return value ? value.slice(0, 10) : '';
  }

  function inclusiveEndKeyFromValue(value: string): string {
    if (!value) {
      return '';
    }
    const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() - 1);
    return dateKey(date);
  }

  function nextDateKey(key: string): string {
    const date = new Date(`${key}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + 1);
    return dateKey(date);
  }

  function monthStartFromValue(value: string): Date {
    const source = value ? new Date(`${value.slice(0, 10)}T00:00:00Z`) : new Date();
    return new Date(Date.UTC(source.getUTCFullYear(), source.getUTCMonth(), 1));
  }

  function monthKey(date: Date): string {
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
  }
</script>

<section class="availability-picker" aria-label="Availability date picker">
  <div class="availability-picker-header">
    <div>
      <p class="eyebrow">Availability</p>
      <h2>{assetLabel}</h2>
      <span>{rangeLabel()}</span>
    </div>
    <div class="availability-month-controls">
      <button type="button" class="secondary compact" onclick={previousMonth}>Previous</button>
      <strong>{monthTitle()}</strong>
      <button type="button" class="secondary compact" onclick={nextMonth}>Next</button>
    </div>
  </div>

  {#if error}
    <p class="notice error">{error}</p>
  {/if}

  <div class="availability-weekdays" aria-hidden="true">
    <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span
    ><span>Sun</span>
  </div>
  <div class="availability-calendar-grid">
    {#each calendarDays() as day}
      <button
        type="button"
        class={dayClasses(day)}
        disabled={loading || !day.inMonth || !day.availability}
        onclick={() => chooseDay(day.key)}
      >
        <strong>{day.label}</strong>
        <span>{availabilityLabel(day)}</span>
      </button>
    {/each}
  </div>

  <div class="availability-picker-footer">
    <p class:error-text={selectedConflictCount() > 0}>
      {#if loading}
        Loading availability...
      {:else if selectedConflictCount() > 0}
        {selectedConflictCount()} selected {selectedConflictCount() === 1 ? 'day is' : 'days are'} unavailable.
      {:else if selectedStart && selectedEnd}
        Selected range is available.
      {:else}
        Pick a start and end date.
      {/if}
    </p>
    <div class="button-row compact-button-row">
      <button type="button" class="secondary compact" onclick={onCancel}>Cancel</button>
      <button
        type="button"
        class="compact"
        disabled={loading || !selectedStart || !selectedEnd || selectedConflictCount() > 0}
        onclick={acceptSelection}
      >
        Accept dates
      </button>
    </div>
  </div>
</section>
