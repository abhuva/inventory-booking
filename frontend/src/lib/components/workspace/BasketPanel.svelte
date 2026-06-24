<script lang="ts">
  import type { Asset, Basket, BasketLine, BasketLineUpdate } from '$lib/api';
  import AvailabilityDatePicker from './AvailabilityDatePicker.svelte';

  let selectedLineId = $state('');
  let selectedQuantity = $state('1');
  let showDatePicker = $state(false);

  let {
    basket,
    assets,
    busy,
    basketTitle = $bindable(),
    basketNotes = $bindable(),
    updateBasket,
    updateBasketLine,
    removeBasketLine,
    confirmBasket,
    cancelBasket,
    assetName,
    locationName,
    personName,
    formatDateTime
  }: {
    basket: Basket | null;
    assets: Asset[];
    busy: boolean;
    basketTitle: string;
    basketNotes: string;
    updateBasket: () => Promise<boolean>;
    updateBasketLine: (lineId: string, payload: BasketLineUpdate) => Promise<boolean>;
    removeBasketLine: (lineId: string) => Promise<boolean>;
    confirmBasket: () => Promise<boolean>;
    cancelBasket: () => Promise<boolean>;
    assetName: (id: string) => string;
    locationName: (id: string | null) => string;
    personName: (id: string | null) => string;
    formatDateTime: (value: string) => string;
  } = $props();

  const selectedLine = $derived(
    basket?.lines.find((line) => line.id === selectedLineId) ?? basket?.lines[0]
  );

  $effect(() => {
    selectedQuantity = String(selectedLine?.quantity ?? 1);
  });

  function selectedAsset(): Asset | undefined {
    return assets.find((asset) => asset.id === selectedLine?.asset_id);
  }

  function assetForLine(line: BasketLine): Asset | undefined {
    return assets.find((asset) => asset.id === line.asset_id);
  }

  function lineQuantity(line: BasketLine): string {
    const asset = assets.find((entry) => entry.id === line.asset_id);
    if (line.quantity === null) {
      return '1 exact item';
    }
    return `${line.quantity} ${asset?.unit_name ?? 'units'}`;
  }

  function selectedLineQuantity(): number {
    const parsed = Number.parseInt(selectedQuantity, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
  }

  async function submitLineQuantity(): Promise<void> {
    if (!selectedLine || selectedLine.quantity === null) {
      return;
    }
    await updateBasketLine(selectedLine.id, {
      starts_at: selectedLine.starts_at,
      ends_at: selectedLine.ends_at,
      quantity: selectedLineQuantity(),
      notes: selectedLine.notes
    });
  }

  async function acceptLineDates(startsAt: string, endsAt: string): Promise<void> {
    if (!selectedLine) {
      return;
    }
    const updated = await updateBasketLine(selectedLine.id, {
      starts_at: new Date(startsAt).toISOString(),
      ends_at: new Date(endsAt).toISOString(),
      quantity: selectedLine.quantity,
      notes: selectedLine.notes
    });
    showDatePicker = !updated;
  }
</script>

<section class="basket-workspace" aria-label="Basket workspace">
  <section class="panel basket-table-panel">
    <div class="inventory-toolbar">
      <div>
        <h2>Basket</h2>
        <p>{basket?.lines.length ?? 0} held item lines</p>
      </div>
    </div>

    {#if basket && basket.lines.length}
      <div class="asset-table-wrap">
        <table class="asset-table">
          <thead>
            <tr>
              <th>Item</th>
              <th>Quantity</th>
              <th>Location</th>
              <th>Dates</th>
            </tr>
          </thead>
          <tbody>
            {#each basket.lines as line}
              <tr
                class:selected-row={line.id === selectedLine?.id}
                onclick={() => (selectedLineId = line.id)}
              >
                <td>
                  <strong>{assetName(line.asset_id)}</strong>
                  <span>{assetForLine(line)?.asset_type ?? 'asset'}</span>
                </td>
                <td>{lineQuantity(line)}</td>
                <td>{locationName(line.location_id)}</td>
                <td>{formatDateTime(line.starts_at)} - {formatDateTime(line.ends_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="empty-detail">
        <h2>No basket yet</h2>
        <p>Add items from Inventory. Temporary holds appear here before confirmation.</p>
      </div>
    {/if}
  </section>

  <aside class="panel basket-detail-panel" aria-label="Basket details">
    {#if basket}
      <form
        class="asset-edit-form"
        onsubmit={(event) => {
          event.preventDefault();
          void updateBasket();
        }}
      >
        <div class="detail-header">
          <div>
            <p class="eyebrow">Temporary hold</p>
            <h2>{basket.title}</h2>
          </div>
        </div>

        <label>Basket name <input bind:value={basketTitle} required /></label>
        <div class="readonly-field">
          <span>Person</span>
          <strong>{personName(basket.person_id)}</strong>
        </div>
        <p class="form-help">Basket range is derived from the earliest and latest item line.</p>
        <div class="split-fields">
          <label>
            Start
            <input value={basket.starts_at.slice(0, 16)} type="datetime-local" disabled />
          </label>
          <label>
            End
            <input value={basket.ends_at.slice(0, 16)} type="datetime-local" disabled />
          </label>
        </div>
        <label>Notes <textarea bind:value={basketNotes}></textarea></label>
        <div class="readonly-field">
          <span>Hold expires</span>
          <strong>{formatDateTime(basket.expires_at)}</strong>
        </div>
        <div class="button-row compact-button-row">
          <button type="submit" class="compact" disabled={busy}>Update basket</button>
          <button type="button" class="secondary compact" disabled={busy} onclick={confirmBasket}>
            Confirm booking
          </button>
          <button type="button" class="secondary compact" disabled={busy} onclick={cancelBasket}>
            Cancel basket
          </button>
        </div>
      </form>

      {#if selectedLine}
        <div class="detail-tab-panel basket-line-detail">
          <div class="detail-header">
            <div>
              <p class="eyebrow">Selected item</p>
              <h2>{assetName(selectedLine.asset_id)}</h2>
            </div>
            <button
              type="button"
              class="secondary micro-button"
              disabled={busy}
              onclick={() => void removeBasketLine(selectedLine.id)}
            >
              Remove
            </button>
          </div>
          <div class="physical-summary-grid">
            <article>
              <span>Quantity</span>
              <strong>{lineQuantity(selectedLine)}</strong>
            </article>
            <article>
              <span>Location</span>
              <strong>{locationName(selectedLine.location_id)}</strong>
            </article>
            <article>
              <span>Type</span>
              <strong>{selectedAsset()?.asset_type ?? 'unknown'}</strong>
            </article>
            <article>
              <span>Reserved from</span>
              <strong>{formatDateTime(selectedLine.starts_at)}</strong>
            </article>
            <article>
              <span>Reserved until</span>
              <strong>{formatDateTime(selectedLine.ends_at)}</strong>
            </article>
          </div>
          <div class="button-row compact-button-row">
            <button
              type="button"
              class="compact"
              disabled={busy}
              onclick={() => (showDatePicker = true)}
            >
              Choose date
            </button>
          </div>
          {#if selectedAsset()?.asset_type === 'stock'}
            <form
              class="compact-field-row"
              onsubmit={(event) => {
                event.preventDefault();
                void submitLineQuantity();
              }}
            >
              <label>
                Amount
                <input bind:value={selectedQuantity} min="1" type="number" required />
              </label>
              <button type="submit" class="compact" disabled={busy}>Update amount</button>
            </form>
          {/if}
          <label>
            Notes
            <textarea value={selectedLine.notes ?? ''} disabled></textarea>
          </label>
        </div>
      {:else}
        <div class="empty-detail">
          <h2>Select a basket item</h2>
          <p>Click a row to inspect or remove it.</p>
        </div>
      {/if}
    {:else}
      <div class="empty-detail">
        <h2>No active basket</h2>
        <p>Use Inventory to add items to a temporary basket hold.</p>
      </div>
    {/if}
  </aside>

  {#if showDatePicker && selectedLine}
    <div class="modal-backdrop">
      <div class="panel modal-panel">
        <AvailabilityDatePicker
          assetId={selectedLine.asset_id}
          locationId={selectedLine.location_id}
          quantity={selectedLine.quantity ?? 1}
          initialStart={selectedLine.starts_at}
          initialEnd={selectedLine.ends_at}
          assetLabel={assetName(selectedLine.asset_id)}
          onAccept={(startsAt, endsAt) => void acceptLineDates(startsAt, endsAt)}
          onCancel={() => (showDatePicker = false)}
        />
      </div>
    </div>
  {/if}
</section>
