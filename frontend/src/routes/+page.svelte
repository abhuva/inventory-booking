<script lang="ts">
  import {
    ApiError,
    apiGet,
    apiPost,
    type Availability,
    type Asset,
    type AssetCreate,
    type AssetType,
    type Booking,
    type BookingCreate,
    type Category,
    type CategoryCreate,
    type Location,
    type LocationCreate,
    type LocationType,
    type StockLevel,
    type StockLevelCreate,
    type User
  } from '$lib/api';

  const locationTypes: LocationType[] = [
    'storage',
    'room',
    'vehicle',
    'project_site',
    'external_space',
    'person_home',
    'repair',
    'unknown'
  ];

  let currentUser = $state<User | null>(null);
  let categories = $state<Category[]>([]);
  let locations = $state<Location[]>([]);
  let assets = $state<Asset[]>([]);
  let stockLevels = $state<StockLevel[]>([]);
  let bookings = $state<Booking[]>([]);
  let availability = $state<Availability | null>(null);
  let email = $state('admin@example.org');
  let password = $state('change-this-password');
  let loading = $state(true);
  let busy = $state(false);
  let message = $state('');
  let error = $state('');

  let categoryForm = $state<CategoryCreate>({ name: '', description: '' });
  let locationForm = $state<LocationCreate>({ name: '', type: 'storage' });
  let assetForm = $state<AssetCreate>({
    name: '',
    asset_type: 'tracked',
    category_id: null,
    unit_name: null,
    current_location_id: null
  });
  let stockForm = $state<StockLevelCreate>({ asset_id: '', location_id: '', quantity_total: 0 });
  let bookingForm = $state({
    title: '',
    starts_at: '',
    ends_at: '',
    asset_id: '',
    location_id: '',
    quantity: 1
  });

  const trackedAssets = $derived(assets.filter((asset) => asset.asset_type === 'tracked'));
  const stockAssets = $derived(assets.filter((asset) => asset.asset_type === 'stock'));

  $effect(() => {
    void bootstrap();
  });

  async function bootstrap() {
    loading = true;
    try {
      await loadCurrentUser();
      await loadInventory();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status !== 401) {
        error = caught.message;
      }
    } finally {
      loading = false;
    }
  }

  async function loadCurrentUser() {
    try {
      currentUser = await apiGet<User>('/auth/me');
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        currentUser = null;
        return;
      }
      throw caught;
    }
  }

  async function loadInventory() {
    [categories, locations, assets, stockLevels, bookings] = await Promise.all([
      apiGet<Category[]>('/categories'),
      apiGet<Location[]>('/locations'),
      apiGet<Asset[]>('/assets'),
      apiGet<StockLevel[]>('/stock-levels'),
      apiGet<Booking[]>('/bookings')
    ]);
  }

  async function login() {
    await runAction(async () => {
      currentUser = await apiPost<User>('/auth/login', { email, password });
      await loadInventory();
      message = `Logged in as ${currentUser.email}`;
    });
  }

  async function logout() {
    await runAction(async () => {
      await apiPost<void>('/auth/logout');
      currentUser = null;
      message = 'Logged out';
    });
  }

  async function createCategory() {
    await runAction(async () => {
      await apiPost<Category>('/categories', emptyStringsToNull(categoryForm));
      categoryForm = { name: '', description: '' };
      await loadInventory();
      message = 'Category created';
    });
  }

  async function createLocation() {
    await runAction(async () => {
      await apiPost<Location>('/locations', locationForm);
      locationForm = { name: '', type: 'storage' };
      await loadInventory();
      message = 'Location created';
    });
  }

  async function createAsset() {
    await runAction(async () => {
      const payload: AssetCreate = {
        ...emptyStringsToNull(assetForm),
        unit_name: assetForm.asset_type === 'stock' ? assetForm.unit_name : null
      };
      await apiPost<Asset>('/assets', payload);
      assetForm = {
        name: '',
        asset_type: 'tracked',
        category_id: null,
        unit_name: null,
        current_location_id: null
      };
      await loadInventory();
      message = 'Asset created';
    });
  }

  async function createStockLevel() {
    await runAction(async () => {
      await apiPost<StockLevel>('/stock-levels', stockForm);
      stockForm = { asset_id: '', location_id: '', quantity_total: 0 };
      await loadInventory();
      message = 'Stock level created';
    });
  }

  async function previewBooking() {
    await runAction(async () => {
      availability = await apiPost<Availability>('/bookings/availability', buildBookingPayload());
      message = availability.available ? 'Booking is available' : 'Booking has conflicts';
    });
  }

  async function createBooking() {
    await runAction(async () => {
      const booking = await apiPost<Booking>('/bookings', buildBookingPayload());
      bookingForm = {
        title: '',
        starts_at: '',
        ends_at: '',
        asset_id: '',
        location_id: '',
        quantity: 1
      };
      availability = null;
      await loadInventory();
      message = `Booking created: ${booking.title}`;
    });
  }

  async function runAction(action: () => Promise<void>) {
    busy = true;
    error = '';
    message = '';
    try {
      await action();
    } catch (caught) {
      error = caught instanceof Error ? caught.message : 'Unknown error';
    } finally {
      busy = false;
    }
  }

  function emptyStringsToNull<T extends Record<string, unknown>>(value: T): T {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => [key, entry === '' ? null : entry])
    ) as T;
  }

  function buildBookingPayload(): BookingCreate {
    const asset = assets.find((entry) => entry.id === bookingForm.asset_id);
    const isStock = asset?.asset_type === 'stock';
    return {
      title: bookingForm.title,
      starts_at: new Date(bookingForm.starts_at).toISOString(),
      ends_at: new Date(bookingForm.ends_at).toISOString(),
      lines: [
        {
          asset_id: bookingForm.asset_id,
          location_id: isStock ? bookingForm.location_id : null,
          quantity: isStock ? bookingForm.quantity : null
        }
      ]
    };
  }

  function categoryName(id: string | null): string {
    return categories.find((category) => category.id === id)?.name ?? 'No category';
  }

  function locationName(id: string | null): string {
    return locations.find((location) => location.id === id)?.name ?? 'No location';
  }

  function stockAssetName(id: string): string {
    return assets.find((asset) => asset.id === id)?.name ?? 'Unknown stock';
  }

  function stockLocationName(id: string): string {
    return locations.find((location) => location.id === id)?.name ?? 'Unknown location';
  }

  function assetName(id: string): string {
    return assets.find((asset) => asset.id === id)?.name ?? 'Unknown asset';
  }

  function selectedBookingAsset(): Asset | undefined {
    return assets.find((asset) => asset.id === bookingForm.asset_id);
  }

  function formatDateTime(value: string): string {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(new Date(value));
  }
</script>

<svelte:head>
  <title>Inventory Booking</title>
  <meta
    name="description"
    content="Internal inventory and equipment booking system for QR-based checkout workflows."
  />
</svelte:head>

<main class="app-shell">
  <section class="masthead">
    <div>
      <p class="eyebrow">Circus pedagogy inventory</p>
      <h1>Inventory that knows the room, the person, and the date.</h1>
    </div>
    <div class="session-card">
      {#if currentUser}
        <p class="session-label">Signed in</p>
        <strong>{currentUser.display_name}</strong>
        <span>{currentUser.email} · {currentUser.role}</span>
        <button type="button" class="secondary" onclick={logout} disabled={busy}>Logout</button>
      {:else}
        <form
          onsubmit={(event) => {
            event.preventDefault();
            void login();
          }}
        >
          <label>
            Email
            <input bind:value={email} type="email" autocomplete="username" />
          </label>
          <label>
            Password
            <input bind:value={password} type="password" autocomplete="current-password" />
          </label>
          <button type="submit" disabled={busy}>Login</button>
        </form>
      {/if}
    </div>
  </section>

  {#if error}
    <p class="notice error">{error}</p>
  {/if}
  {#if message}
    <p class="notice success">{message}</p>
  {/if}

  {#if loading}
    <section class="panel loading-panel">Loading inventory workspace...</section>
  {:else}
    <section class="stats-grid" aria-label="Inventory summary">
      <article>
        <span>{trackedAssets.length}</span>
        <p>tracked assets</p>
      </article>
      <article>
        <span>{stockAssets.length}</span>
        <p>stock assets</p>
      </article>
      <article>
        <span>{locations.length}</span>
        <p>locations</p>
      </article>
      <article>
        <span>{stockLevels.reduce((sum, level) => sum + level.quantity_total, 0)}</span>
        <p>stock units</p>
      </article>
      <article>
        <span>{bookings.length}</span>
        <p>bookings</p>
      </article>
    </section>

    {#if currentUser}
      <section class="forms-grid" aria-label="Create inventory data">
        <form
          class="panel form-panel"
          onsubmit={(event) => {
            event.preventDefault();
            void createCategory();
          }}
        >
          <h2>Category</h2>
          <label>Name <input bind:value={categoryForm.name} required /></label>
          <label>Description <textarea bind:value={categoryForm.description}></textarea></label>
          <button type="submit" disabled={busy}>Create category</button>
        </form>

        <form
          class="panel form-panel"
          onsubmit={(event) => {
            event.preventDefault();
            void createLocation();
          }}
        >
          <h2>Location</h2>
          <label>Name <input bind:value={locationForm.name} required /></label>
          <label>
            Type
            <select bind:value={locationForm.type}>
              {#each locationTypes as type}
                <option value={type}>{type.replaceAll('_', ' ')}</option>
              {/each}
            </select>
          </label>
          <button type="submit" disabled={busy}>Create location</button>
        </form>

        <form
          class="panel form-panel wide"
          onsubmit={(event) => {
            event.preventDefault();
            void createAsset();
          }}
        >
          <h2>Asset</h2>
          <div class="split-fields">
            <label>Name <input bind:value={assetForm.name} required /></label>
            <label>
              Mode
              <select bind:value={assetForm.asset_type}>
                <option value="tracked">tracked exact item</option>
                <option value="stock">stock quantity</option>
              </select>
            </label>
          </div>
          <div class="split-fields">
            <label>
              Category
              <select bind:value={assetForm.category_id}>
                <option value={null}>No category</option>
                {#each categories as category}
                  <option value={category.id}>{category.name}</option>
                {/each}
              </select>
            </label>
            <label>
              Current location
              <select bind:value={assetForm.current_location_id}>
                <option value={null}>No location</option>
                {#each locations as location}
                  <option value={location.id}>{location.name}</option>
                {/each}
              </select>
            </label>
          </div>
          {#if assetForm.asset_type === 'stock'}
            <label
              >Unit name <input
                bind:value={assetForm.unit_name}
                placeholder="piece, set, box"
                required
              /></label
            >
          {/if}
          <button type="submit" disabled={busy}>Create asset</button>
        </form>

        <form
          class="panel form-panel"
          onsubmit={(event) => {
            event.preventDefault();
            void createStockLevel();
          }}
        >
          <h2>Stock level</h2>
          <label>
            Stock asset
            <select bind:value={stockForm.asset_id} required>
              <option value="">Choose stock</option>
              {#each stockAssets as asset}
                <option value={asset.id}>{asset.name}</option>
              {/each}
            </select>
          </label>
          <label>
            Location
            <select bind:value={stockForm.location_id} required>
              <option value="">Choose location</option>
              {#each locations as location}
                <option value={location.id}>{location.name}</option>
              {/each}
            </select>
          </label>
          <label
            >Total quantity <input
              bind:value={stockForm.quantity_total}
              type="number"
              min="0"
            /></label
          >
          <button type="submit" disabled={busy}>Set stock level</button>
        </form>

        <form
          class="panel form-panel wide"
          onsubmit={(event) => {
            event.preventDefault();
            void createBooking();
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
    {/if}

    <section class="data-grid" aria-label="Inventory lists">
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

      <article class="panel list-panel">
        <h2>Assets</h2>
        {#each assets as asset}
          <div class="row-card">
            <strong>{asset.name}</strong>
            <span
              >{asset.asset_type} · {categoryName(asset.category_id)} · {locationName(
                asset.current_location_id
              )}</span
            >
          </div>
        {:else}
          <p class="empty">No assets yet.</p>
        {/each}
      </article>

      <article class="panel list-panel">
        <h2>Stock levels</h2>
        {#each stockLevels as level}
          <div class="row-card">
            <strong>{stockAssetName(level.asset_id)}</strong>
            <span>{stockLocationName(level.location_id)} · {level.quantity_total} total</span>
          </div>
        {:else}
          <p class="empty">No stock levels yet.</p>
        {/each}
      </article>

      <article class="panel list-panel">
        <h2>Locations</h2>
        {#each locations as location}
          <div class="row-card">
            <strong>{location.name}</strong>
            <span>{location.type.replaceAll('_', ' ')}</span>
          </div>
        {:else}
          <p class="empty">No locations yet.</p>
        {/each}
      </article>

      <article class="panel list-panel">
        <h2>Categories</h2>
        {#each categories as category}
          <div class="row-card">
            <strong>{category.name}</strong>
            <span>{category.description ?? 'No description'}</span>
          </div>
        {:else}
          <p class="empty">No categories yet.</p>
        {/each}
      </article>
    </section>
  {/if}
</main>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  .app-shell {
    width: min(1280px, calc(100% - 2rem));
    margin: 0 auto;
    padding: clamp(1.5rem, 5vw, 4rem) 0;
  }

  .masthead {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(18rem, 24rem);
    gap: clamp(1rem, 4vw, 3rem);
    align-items: stretch;
    margin-bottom: 1rem;
  }

  .eyebrow {
    margin: 0 0 1rem;
    color: #61713e;
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  h1 {
    max-width: 13ch;
    margin: 0;
    color: #14211c;
    font-size: clamp(3.4rem, 9vw, 7rem);
    line-height: 0.86;
    letter-spacing: -0.075em;
  }

  h2 {
    margin: 0 0 1rem;
    font-size: 1.1rem;
    letter-spacing: -0.03em;
  }

  .panel,
  .session-card,
  .stats-grid article {
    border: 1px solid rgba(20, 33, 28, 0.12);
    border-radius: 28px;
    background: rgba(255, 252, 242, 0.82);
    box-shadow: 0 24px 80px rgba(42, 68, 51, 0.12);
    backdrop-filter: blur(18px);
  }

  .session-card {
    padding: 1.25rem;
  }

  .session-card form,
  .form-panel {
    display: grid;
    gap: 0.85rem;
  }

  .session-label {
    margin: 0 0 0.35rem;
    color: #68765d;
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  .session-card strong,
  .session-card span {
    display: block;
  }

  .session-card span {
    margin: 0.35rem 0 1rem;
    color: #4f5e52;
  }

  label {
    display: grid;
    gap: 0.35rem;
    color: #33443a;
    font-size: 0.88rem;
    font-weight: 750;
  }

  input,
  select,
  textarea {
    width: 100%;
    border: 1px solid rgba(20, 33, 28, 0.18);
    border-radius: 16px;
    padding: 0.78rem 0.9rem;
    color: #14211c;
    background: rgba(255, 255, 255, 0.72);
  }

  textarea {
    min-height: 5rem;
    resize: vertical;
  }

  button {
    min-height: 2.8rem;
    border: 0;
    border-radius: 999px;
    padding: 0 1.1rem;
    color: #fffaf0;
    background: #254c37;
    font-weight: 800;
    cursor: pointer;
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  button.secondary {
    width: 100%;
    background: #6f7345;
  }

  .notice {
    margin: 1rem 0;
    border-radius: 18px;
    padding: 0.85rem 1rem;
    font-weight: 750;
  }

  .error {
    color: #6d1f1a;
    background: #f9d7cf;
  }

  .success {
    color: #254c37;
    background: #dbeacb;
  }

  .stats-grid,
  .forms-grid,
  .data-grid {
    display: grid;
    gap: 1rem;
    margin-top: 1rem;
  }

  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  }

  .stats-grid article {
    padding: 1.25rem;
  }

  .stats-grid span {
    display: block;
    font-size: clamp(2rem, 4vw, 3.4rem);
    font-weight: 900;
    letter-spacing: -0.07em;
  }

  .stats-grid p {
    margin: 0.25rem 0 0;
    color: #526358;
    font-weight: 750;
  }

  .forms-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .form-panel,
  .list-panel,
  .loading-panel {
    padding: 1.25rem;
  }

  .wide {
    grid-column: span 2;
  }

  .split-fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem;
  }

  .button-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
  }

  .button-row button {
    flex: 1 1 12rem;
  }

  .availability-result {
    display: grid;
    gap: 0.25rem;
    border-radius: 18px;
    padding: 0.85rem 1rem;
    color: #6d1f1a;
    background: #f9d7cf;
  }

  .availability-ok {
    color: #254c37;
    background: #dbeacb;
  }

  .data-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .list-panel {
    display: grid;
    align-content: start;
    gap: 0.75rem;
  }

  .row-card {
    display: grid;
    gap: 0.25rem;
    border-radius: 18px;
    padding: 0.85rem 1rem;
    background: rgba(37, 76, 55, 0.08);
  }

  .row-card span,
  .empty {
    color: #526358;
  }

  @media (max-width: 960px) {
    .masthead,
    .forms-grid,
    .data-grid {
      grid-template-columns: 1fr;
    }

    .stats-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .wide {
      grid-column: auto;
    }
  }

  @media (max-width: 560px) {
    .stats-grid,
    .split-fields {
      grid-template-columns: 1fr;
    }
  }
</style>
