<script lang="ts">
  import {
    ApiError,
    apiGet,
    apiPatch,
    apiPost,
    type Availability,
    type Asset,
    type AssetCreate,
    type AssetStateChange,
    type AssetType,
    type Booking,
    type BookingCreate,
    type Category,
    type CategoryCreate,
    type CategoryUpdate,
    type Checkout,
    type CheckoutCreate,
    type Location,
    type LocationCreate,
    type LocationType,
    type MaintenanceComplete,
    type MaintenanceStart,
    type QrAssign,
    type QrCode,
    type QrCodeCreate,
    type QrResolve,
    type ReturnCreate,
    type ReturnRecord,
    type StockLevel,
    type StockLevelCreate,
    type StockTransfer,
    type TrackedAssetTransfer,
    type User,
    type UserCreate,
    type UserRole,
    type UserUpdate
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
  let checkouts = $state<Checkout[]>([]);
  let returns = $state<ReturnRecord[]>([]);
  let qrCodes = $state<QrCode[]>([]);
  let users = $state<User[]>([]);
  let resolvedQr = $state<QrResolve | null>(null);
  let selectedReturnCheckout = $state<Checkout | null>(null);
  let availability = $state<Availability | null>(null);
  let email = $state('admin@example.org');
  let password = $state('change-this-password');
  let loading = $state(true);
  let busy = $state(false);
  let message = $state('');
  let error = $state('');

  let categoryForm = $state<CategoryCreate>({ name: '', description: '' });
  let categoryUpdateForm = $state<CategoryUpdate & { category_id: string }>({
    category_id: '',
    name: '',
    description: ''
  });
  let userCreateForm = $state<UserCreate>({
    email: '',
    display_name: '',
    password: '',
    role: 'user',
    is_active: true
  });
  let userUpdateForm = $state<{
    user_id: string;
    display_name: string;
    role: UserRole;
    is_active: boolean;
    password: string;
  }>({
    user_id: '',
    display_name: '',
    role: 'user',
    is_active: true,
    password: ''
  });
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
  let checkoutForm = $state<CheckoutCreate>({
    booking_id: '',
    condition_out: 'unknown',
    notes: ''
  });
  let returnForm = $state({
    checkout_id: '',
    checkout_line_id: '',
    quantity: 1,
    condition_in: 'unknown' as const,
    notes: ''
  });
  let trackedTransferForm = $state<TrackedAssetTransfer & { asset_id: string }>({
    asset_id: '',
    to_location_id: '',
    to_holder_user_id: null,
    notes: ''
  });
  let stockTransferForm = $state<StockTransfer>({
    asset_id: '',
    from_location_id: '',
    to_location_id: '',
    quantity: 1,
    notes: ''
  });
  let assetStateForm = $state({
    asset_id: '',
    action: 'maintenance_start',
    status: 'damaged',
    condition: 'unknown',
    notes: ''
  });
  let qrCreateForm = $state<QrCodeCreate>({ label: '', notes: '' });
  let qrAssignForm = $state<QrAssign & { token: string }>({
    token: '',
    asset_id: '',
    notes: ''
  });
  let qrResolveToken = $state('');

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
    [categories, locations, assets, stockLevels, bookings, checkouts, returns, qrCodes, users] =
      await Promise.all([
        apiGet<Category[]>('/categories'),
        apiGet<Location[]>('/locations'),
        apiGet<Asset[]>('/assets'),
        apiGet<StockLevel[]>('/stock-levels'),
        apiGet<Booking[]>('/bookings'),
        apiGet<Checkout[]>('/checkouts'),
        apiGet<ReturnRecord[]>('/returns'),
        currentUser ? apiGet<QrCode[]>('/qr-codes') : Promise.resolve([]),
        currentUser?.role === 'admin' ? apiGet<User[]>('/users') : Promise.resolve([])
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
      qrCodes = [];
      users = [];
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

  async function updateCategory() {
    await runAction(async () => {
      const { category_id: categoryId, ...payload } = categoryUpdateForm;
      await apiPatch<Category>(`/categories/${categoryId}`, emptyStringsToNull(payload));
      categoryUpdateForm = { category_id: '', name: '', description: '' };
      await loadInventory();
      message = 'Category updated';
    });
  }

  async function createUser() {
    await runAction(async () => {
      await apiPost<User>('/users', userCreateForm);
      userCreateForm = {
        email: '',
        display_name: '',
        password: '',
        role: 'user',
        is_active: true
      };
      await loadInventory();
      message = 'User created';
    });
  }

  async function updateUser() {
    await runAction(async () => {
      const payload: UserUpdate = {
        display_name: userUpdateForm.display_name,
        role: userUpdateForm.role,
        is_active: userUpdateForm.is_active
      };
      if (userUpdateForm.password) {
        payload.password = userUpdateForm.password;
      }
      await apiPatch<User>(`/users/${userUpdateForm.user_id}`, payload);
      userUpdateForm.password = '';
      await loadInventory();
      message = 'User updated';
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

  async function createCheckout() {
    await runAction(async () => {
      const checkout = await apiPost<Checkout>('/checkouts', emptyStringsToNull(checkoutForm));
      checkoutForm = { booking_id: '', condition_out: 'unknown', notes: '' };
      await loadInventory();
      message = `Checkout created for booking ${bookingTitle(checkout.booking_id)}`;
    });
  }

  async function loadCheckoutForReturn() {
    await runAction(async () => {
      selectedReturnCheckout = await apiGet<Checkout>(`/checkouts/${returnForm.checkout_id}`);
      returnForm.checkout_line_id = selectedReturnCheckout.lines?.[0]?.id ?? '';
      message = 'Checkout lines loaded';
    });
  }

  async function createReturn() {
    await runAction(async () => {
      const payload: ReturnCreate = {
        checkout_id: returnForm.checkout_id,
        notes: returnForm.notes || null,
        lines: [
          {
            checkout_line_id: returnForm.checkout_line_id,
            quantity: selectedReturnLine()?.quantity === null ? null : returnForm.quantity,
            condition_in: returnForm.condition_in,
            notes: returnForm.notes || null
          }
        ]
      };
      await apiPost<ReturnRecord>('/returns', payload);
      returnForm = {
        checkout_id: '',
        checkout_line_id: '',
        quantity: 1,
        condition_in: 'unknown',
        notes: ''
      };
      selectedReturnCheckout = null;
      await loadInventory();
      message = 'Return recorded';
    });
  }

  async function transferTrackedAssetAction() {
    await runAction(async () => {
      const { asset_id, ...payload } = trackedTransferForm;
      await apiPost<Asset>(`/assets/${asset_id}/transfer`, emptyStringsToNull(payload));
      trackedTransferForm = {
        asset_id: '',
        to_location_id: '',
        to_holder_user_id: null,
        notes: ''
      };
      await loadInventory();
      message = 'Tracked asset transferred';
    });
  }

  async function transferStockAction() {
    await runAction(async () => {
      await apiPost<StockLevel[]>('/stock-levels/transfer', emptyStringsToNull(stockTransferForm));
      stockTransferForm = {
        asset_id: '',
        from_location_id: '',
        to_location_id: '',
        quantity: 1,
        notes: ''
      };
      await loadInventory();
      message = 'Stock transferred';
    });
  }

  async function changeAssetOperationalState() {
    await runAction(async () => {
      const assetId = assetStateForm.asset_id;
      if (assetStateForm.action === 'maintenance_start') {
        const payload: MaintenanceStart = { notes: assetStateForm.notes || null };
        await apiPost<Asset>(`/assets/${assetId}/maintenance/start`, payload);
      } else if (assetStateForm.action === 'maintenance_complete') {
        const payload: MaintenanceComplete = {
          condition: assetStateForm.condition as MaintenanceComplete['condition'],
          notes: assetStateForm.notes || null
        };
        await apiPost<Asset>(`/assets/${assetId}/maintenance/complete`, payload);
      } else {
        const payload: AssetStateChange = {
          status: assetStateForm.status as AssetStateChange['status'],
          condition: assetStateForm.condition as AssetStateChange['condition'],
          notes: assetStateForm.notes || null
        };
        await apiPost<Asset>(`/assets/${assetId}/state`, payload);
      }
      assetStateForm = {
        asset_id: '',
        action: 'maintenance_start',
        status: 'damaged',
        condition: 'unknown',
        notes: ''
      };
      await loadInventory();
      message = 'Asset state updated';
    });
  }

  async function createQrCode() {
    await runAction(async () => {
      const qrCode = await apiPost<QrCode>('/qr-codes', emptyStringsToNull(qrCreateForm));
      qrCreateForm = { label: '', notes: '' };
      qrAssignForm.token = qrCode.token;
      await loadInventory();
      message = 'QR label created';
    });
  }

  async function assignQrCode() {
    await runAction(async () => {
      const { token, ...payload } = qrAssignForm;
      await apiPost<QrCode>(`/qr-codes/${token}/assign`, emptyStringsToNull(payload));
      qrAssignForm = { token: '', asset_id: '', notes: '' };
      await loadInventory();
      message = 'QR label assigned';
    });
  }

  async function resolveQrCode() {
    await runAction(async () => {
      resolvedQr = await apiGet<QrResolve>(`/qr-codes/${qrResolveToken}/resolve`);
      message = resolvedQr.assigned ? 'QR label resolved' : 'QR label is unassigned';
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

  function selectedReturnLine() {
    return selectedReturnCheckout?.lines?.find((line) => line.id === returnForm.checkout_line_id);
  }

  function selectCategoryForEdit(event: Event) {
    const categoryId = (event.currentTarget as HTMLSelectElement).value;
    const category = categories.find((entry) => entry.id === categoryId);
    categoryUpdateForm = {
      category_id: categoryId,
      name: category?.name ?? '',
      description: category?.description ?? ''
    };
  }

  function selectUserForEdit(event: Event) {
    const userId = (event.currentTarget as HTMLSelectElement).value;
    const user = users.find((entry) => entry.id === userId);
    userUpdateForm = {
      user_id: userId,
      display_name: user?.display_name ?? '',
      role: user?.role ?? 'user',
      is_active: user?.is_active ?? true,
      password: ''
    };
  }

  function bookingTitle(id: string): string {
    return bookings.find((booking) => booking.id === id)?.title ?? 'Unknown booking';
  }

  function checkoutLabel(checkout: Checkout): string {
    return `${bookingTitle(checkout.booking_id)} · ${checkout.status}`;
  }

  function returnLineLabel(line: NonNullable<Checkout['lines']>[number]): string {
    const quantityText = line.quantity === null ? 'tracked item' : `${line.quantity} total`;
    const returnedText = line.quantity_returned > 0 ? `, ${line.quantity_returned} returned` : '';
    return `${assetName(line.asset_id)} · ${quantityText}${returnedText}`;
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
      <article>
        <span>{checkouts.length}</span>
        <p>checkouts</p>
      </article>
      <article>
        <span>{returns.length}</span>
        <p>returns</p>
      </article>
      <article>
        <span>{qrCodes.length}</span>
        <p>QR labels</p>
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

        {#if currentUser.role === 'admin'}
          <form
            class="panel form-panel"
            onsubmit={(event) => {
              event.preventDefault();
              void updateCategory();
            }}
          >
            <h2>Edit category</h2>
            <label>
              Category
              <select
                value={categoryUpdateForm.category_id}
                onchange={selectCategoryForEdit}
                required
              >
                <option value="">Choose category</option>
                {#each categories as category}
                  <option value={category.id}>{category.name}</option>
                {/each}
              </select>
            </label>
            <label>Name <input bind:value={categoryUpdateForm.name} required /></label>
            <label
              >Description <textarea bind:value={categoryUpdateForm.description}></textarea></label
            >
            <button type="submit" disabled={busy}>Update category</button>
          </form>

          <form
            class="panel form-panel"
            onsubmit={(event) => {
              event.preventDefault();
              void createUser();
            }}
          >
            <h2>Create user</h2>
            <label>Email <input bind:value={userCreateForm.email} type="email" required /></label>
            <label>Name <input bind:value={userCreateForm.display_name} required /></label>
            <label>
              Role
              <select bind:value={userCreateForm.role}>
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </label>
            <label
              >Password <input
                bind:value={userCreateForm.password}
                type="password"
                required
              /></label
            >
            <label class="checkbox-label">
              <input bind:checked={userCreateForm.is_active} type="checkbox" />
              Active
            </label>
            <button type="submit" disabled={busy}>Create user</button>
          </form>

          <form
            class="panel form-panel"
            onsubmit={(event) => {
              event.preventDefault();
              void updateUser();
            }}
          >
            <h2>Edit user</h2>
            <label>
              User
              <select value={userUpdateForm.user_id} onchange={selectUserForEdit} required>
                <option value="">Choose user</option>
                {#each users as user}
                  <option value={user.id}>{user.display_name} · {user.email}</option>
                {/each}
              </select>
            </label>
            <label>Name <input bind:value={userUpdateForm.display_name} required /></label>
            <label>
              Role
              <select bind:value={userUpdateForm.role}>
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </label>
            <label
              >New password <input bind:value={userUpdateForm.password} type="password" /></label
            >
            <label class="checkbox-label">
              <input bind:checked={userUpdateForm.is_active} type="checkbox" />
              Active
            </label>
            <button type="submit" disabled={busy}>Update user</button>
          </form>
        {/if}

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

        <form
          class="panel form-panel"
          onsubmit={(event) => {
            event.preventDefault();
            void createCheckout();
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
            void createReturn();
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

        <form
          class="panel form-panel"
          onsubmit={(event) => {
            event.preventDefault();
            void transferTrackedAssetAction();
          }}
        >
          <h2>Move tracked item</h2>
          <label>
            Asset
            <select bind:value={trackedTransferForm.asset_id} required>
              <option value="">Choose tracked asset</option>
              {#each trackedAssets as asset}
                <option value={asset.id}>{asset.name}</option>
              {/each}
            </select>
          </label>
          <label>
            Destination
            <select bind:value={trackedTransferForm.to_location_id}>
              <option value="">No location</option>
              {#each locations as location}
                <option value={location.id}>{location.name}</option>
              {/each}
            </select>
          </label>
          <label>Notes <textarea bind:value={trackedTransferForm.notes}></textarea></label>
          <button type="submit" disabled={busy}>Move tracked item</button>
        </form>

        <form
          class="panel form-panel wide"
          onsubmit={(event) => {
            event.preventDefault();
            void transferStockAction();
          }}
        >
          <h2>Move stock</h2>
          <div class="split-fields">
            <label>
              Stock asset
              <select bind:value={stockTransferForm.asset_id} required>
                <option value="">Choose stock</option>
                {#each stockAssets as asset}
                  <option value={asset.id}>{asset.name}</option>
                {/each}
              </select>
            </label>
            <label>
              Quantity
              <input bind:value={stockTransferForm.quantity} type="number" min="1" required />
            </label>
          </div>
          <div class="split-fields">
            <label>
              From
              <select bind:value={stockTransferForm.from_location_id} required>
                <option value="">Source location</option>
                {#each locations as location}
                  <option value={location.id}>{location.name}</option>
                {/each}
              </select>
            </label>
            <label>
              To
              <select bind:value={stockTransferForm.to_location_id} required>
                <option value="">Destination location</option>
                {#each locations as location}
                  <option value={location.id}>{location.name}</option>
                {/each}
              </select>
            </label>
          </div>
          <label>Notes <textarea bind:value={stockTransferForm.notes}></textarea></label>
          <button type="submit" disabled={busy}>Move stock</button>
        </form>

        <form
          class="panel form-panel wide"
          onsubmit={(event) => {
            event.preventDefault();
            void changeAssetOperationalState();
          }}
        >
          <h2>Asset state</h2>
          <div class="split-fields">
            <label>
              Asset
              <select bind:value={assetStateForm.asset_id} required>
                <option value="">Choose tracked asset</option>
                {#each trackedAssets as asset}
                  <option value={asset.id}>{asset.name} · {asset.status}</option>
                {/each}
              </select>
            </label>
            <label>
              Action
              <select bind:value={assetStateForm.action}>
                <option value="maintenance_start">start maintenance</option>
                <option value="maintenance_complete">complete maintenance</option>
                <option value="state_change">mark state</option>
              </select>
            </label>
          </div>
          {#if assetStateForm.action === 'state_change'}
            <label>
              State
              <select bind:value={assetStateForm.status}>
                <option value="damaged">damaged</option>
                <option value="lost">lost</option>
                <option value="retired">retired</option>
                <option value="available">available / found</option>
              </select>
            </label>
          {/if}
          {#if assetStateForm.action !== 'maintenance_start'}
            <label>
              Condition
              <select bind:value={assetStateForm.condition}>
                <option value="unknown">unknown</option>
                <option value="good">good</option>
                <option value="worn">worn</option>
                <option value="damaged">damaged</option>
                <option value="needs_repair">needs repair</option>
              </select>
            </label>
          {/if}
          <label>Notes <textarea bind:value={assetStateForm.notes}></textarea></label>
          <button type="submit" disabled={busy}>Update asset state</button>
        </form>

        <form
          class="panel form-panel"
          onsubmit={(event) => {
            event.preventDefault();
            void createQrCode();
          }}
        >
          <h2>QR label</h2>
          <label>Label <input bind:value={qrCreateForm.label} placeholder="Label 001" /></label>
          <label>Notes <textarea bind:value={qrCreateForm.notes}></textarea></label>
          <button type="submit" disabled={busy}>Create QR label</button>
        </form>

        <form
          class="panel form-panel wide"
          onsubmit={(event) => {
            event.preventDefault();
            void assignQrCode();
          }}
        >
          <h2>Assign QR</h2>
          <div class="split-fields">
            <label>
              Token
              <select bind:value={qrAssignForm.token} required>
                <option value="">Choose QR label</option>
                {#each qrCodes as qrCode}
                  <option value={qrCode.token}>
                    {qrCode.label ?? qrCode.token.slice(0, 10)} · {qrCode.asset_id
                      ? assetName(qrCode.asset_id)
                      : 'unassigned'}
                  </option>
                {/each}
              </select>
            </label>
            <label>
              Tracked asset
              <select bind:value={qrAssignForm.asset_id} required>
                <option value="">Choose tracked asset</option>
                {#each trackedAssets.filter((asset) => asset.status !== 'lost' && asset.status !== 'retired') as asset}
                  <option value={asset.id}>{asset.name}</option>
                {/each}
              </select>
            </label>
          </div>
          <label>Notes <textarea bind:value={qrAssignForm.notes}></textarea></label>
          <button type="submit" disabled={busy}>Assign QR label</button>
        </form>

        <form
          class="panel form-panel"
          onsubmit={(event) => {
            event.preventDefault();
            void resolveQrCode();
          }}
        >
          <h2>Scan / resolve QR</h2>
          <label>Token <input bind:value={qrResolveToken} required /></label>
          {#if resolvedQr}
            <div class:availability-ok={resolvedQr.assigned} class="availability-result">
              <strong>{resolvedQr.assigned ? resolvedQr.asset?.name : 'Unassigned label'}</strong>
              {#if resolvedQr.asset}
                <span>{resolvedQr.asset.status} · {resolvedQr.asset.condition}</span>
              {/if}
            </div>
          {/if}
          <button type="submit" disabled={busy}>Resolve QR</button>
        </form>
      </section>
    {/if}

    <section class="data-grid" aria-label="Inventory lists">
      {#if currentUser?.role === 'admin'}
        <article class="panel list-panel">
          <h2>Users</h2>
          {#each users as user}
            <div class="row-card">
              <strong>{user.display_name}</strong>
              <span>{user.email} · {user.role} · {user.is_active ? 'active' : 'disabled'}</span>
            </div>
          {:else}
            <p class="empty">No users visible.</p>
          {/each}
        </article>
      {/if}

      <article class="panel list-panel">
        <h2>QR labels</h2>
        {#each qrCodes as qrCode}
          <div class="row-card">
            <strong>{qrCode.label ?? qrCode.token.slice(0, 14)}</strong>
            <span>{qrCode.asset_id ? assetName(qrCode.asset_id) : 'unassigned'}</span>
          </div>
        {:else}
          <p class="empty">No QR labels yet.</p>
        {/each}
      </article>

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
                checkouts.find((checkout) => checkout.id === returnRecord.checkout_id)
                  ?.booking_id ?? ''
              )}</strong
            >
            <span>{returnRecord.notes ?? 'Return recorded'}</span>
          </div>
        {:else}
          <p class="empty">No returns yet.</p>
        {/each}
      </article>

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
