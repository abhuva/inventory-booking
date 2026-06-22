<script lang="ts">
  import type { Checkout, CheckoutCreate, ReturnRecord } from '$lib/api';

  let {
    bookings,
    checkouts,
    returns,
    busy,
    checkoutForm = $bindable(),
    returnForm = $bindable(),
    selectedReturnCheckout,
    createCheckout,
    createReturn,
    loadCheckoutForReturn,
    selectedReturnLine,
    checkoutLabel,
    returnLineLabel,
    bookingTitle
  }: {
    bookings: { id: string; title: string; status: string }[];
    checkouts: Checkout[];
    returns: ReturnRecord[];
    busy: boolean;
    checkoutForm: CheckoutCreate;
    returnForm: {
      checkout_id: string;
      checkout_line_id: string;
      quantity: number;
      condition_in: 'unknown' | 'good' | 'worn' | 'damaged' | 'needs_repair';
      notes: string;
    };
    selectedReturnCheckout: Checkout | null;
    createCheckout: () => void;
    createReturn: () => void;
    loadCheckoutForReturn: () => void;
    selectedReturnLine: () => NonNullable<Checkout['lines']>[number] | undefined;
    checkoutLabel: (checkout: Checkout) => string;
    returnLineLabel: (line: NonNullable<Checkout['lines']>[number]) => string;
    bookingTitle: (id: string) => string;
  } = $props();
</script>

<section class="forms-grid" aria-label="Checkout and return controls">
  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      createCheckout();
    }}
  >
    <h2>Checkout</h2>
    <label>
      Reserved booking
      <select bind:value={checkoutForm.booking_id} required>
        <option value="">Choose booking</option>
        {#each bookings.filter((booking) => booking.status === 'reserved') as booking}
          <option value={booking.id}>{booking.title}</option>
        {/each}
      </select>
    </label>
    <label>
      Condition out
      <select bind:value={checkoutForm.condition_out}>
        <option value="unknown">unknown</option>
        <option value="good">good</option>
        <option value="worn">worn</option>
        <option value="damaged">damaged</option>
        <option value="needs_repair">needs repair</option>
      </select>
    </label>
    <label>Notes <textarea bind:value={checkoutForm.notes}></textarea></label>
    <button type="submit" disabled={busy}>Create checkout</button>
  </form>

  <form
    class="panel form-panel wide"
    onsubmit={(event) => {
      event.preventDefault();
      createReturn();
    }}
  >
    <h2>Return</h2>
    <div class="split-fields">
      <label>
        Checkout
        <select bind:value={returnForm.checkout_id} required>
          <option value="">Choose checkout</option>
          {#each checkouts.filter((checkout) => checkout.status !== 'returned') as checkout}
            <option value={checkout.id}>{checkoutLabel(checkout)}</option>
          {/each}
        </select>
      </label>
      <label>
        Lines
        <button
          type="button"
          class="secondary"
          onclick={loadCheckoutForReturn}
          disabled={busy || !returnForm.checkout_id}
        >
          Load lines
        </button>
      </label>
    </div>
    {#if selectedReturnCheckout?.lines?.length}
      <label>
        Checkout line
        <select bind:value={returnForm.checkout_line_id} required>
          {#each selectedReturnCheckout.lines as line}
            <option value={line.id}>{returnLineLabel(line)}</option>
          {/each}
        </select>
      </label>
      {#if selectedReturnLine()?.quantity !== null}
        <label>
          Quantity
          <input bind:value={returnForm.quantity} type="number" min="1" required />
        </label>
      {/if}
      <label>
        Condition in
        <select bind:value={returnForm.condition_in}>
          <option value="unknown">unknown</option>
          <option value="good">good</option>
          <option value="worn">worn</option>
          <option value="damaged">damaged</option>
          <option value="needs_repair">needs repair</option>
        </select>
      </label>
      <label>Notes <textarea bind:value={returnForm.notes}></textarea></label>
      <button type="submit" disabled={busy}>Record return</button>
    {:else}
      <p class="empty">Load a checkout to choose return lines.</p>
    {/if}
  </form>
</section>

<section class="data-grid" aria-label="Checkout and return lists">
  <article class="panel list-panel">
    <h2>Checkouts</h2>
    {#each checkouts as checkout}
      <div class="row-card">
        <strong>{bookingTitle(checkout.booking_id)}</strong>
        <span>{checkout.status}</span>
      </div>
    {:else}
      <p class="empty">No checkouts yet.</p>
    {/each}
  </article>

  <article class="panel list-panel">
    <h2>Returns</h2>
    {#each returns as returnRecord}
      <div class="row-card">
        <strong
          >{bookingTitle(
            checkouts.find((checkout) => checkout.id === returnRecord.checkout_id)?.booking_id ?? ''
          )}</strong
        >
        <span>{returnRecord.notes ?? 'Return recorded'}</span>
      </div>
    {:else}
      <p class="empty">No returns yet.</p>
    {/each}
  </article>
</section>
