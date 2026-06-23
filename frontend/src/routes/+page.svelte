<script lang="ts">
  import {
    ApiError,
    apiDelete,
    apiGet,
    apiPatch,
    apiPost,
    apiUpload,
    apiUrl,
    type Availability,
    type Asset,
    type AssetCreate,
    type AssetImage,
    type AssetStateChange,
    type AssetType,
    type AssetUpdate,
    type Booking,
    type BookingCreate,
    type Category,
    type CategoryCreate,
    type CategoryUpdate,
    type Checkout,
    type CheckoutCreate,
    type ItemEvent,
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
  import AdminPanel from '$lib/components/workspace/AdminPanel.svelte';
  import BookingsPanel from '$lib/components/workspace/BookingsPanel.svelte';
  import CheckoutPanel from '$lib/components/workspace/CheckoutPanel.svelte';
  import DashboardPanel from '$lib/components/workspace/DashboardPanel.svelte';
  import FieldQrPanel from '$lib/components/workspace/FieldQrPanel.svelte';
  import InventoryPanel from '$lib/components/workspace/InventoryPanel.svelte';
  import LocationsPanel from '$lib/components/workspace/LocationsPanel.svelte';
  import { prepareAssetImage } from '$lib/image';
  import WorkspaceTabs from '$lib/components/workspace/WorkspaceTabs.svelte';
  import type { WorkspaceTab, WorkspaceTabDefinition } from '$lib/components/workspace/types';

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

  const workspaceTabs: WorkspaceTabDefinition[] = [
    { id: 'dashboard', label: 'Dashboard', description: 'Counts and workspace overview' },
    { id: 'inventory', label: 'Inventory', description: 'Assets, state, and history' },
    { id: 'locations', label: 'Locations', description: 'Spaces, stock, and movement' },
    { id: 'bookings', label: 'Bookings', description: 'Reservations and availability' },
    { id: 'checkout', label: 'Checkout', description: 'Hand out and return equipment' },
    { id: 'field', label: 'Field / QR', description: 'QR labels and quick lookup' },
    { id: 'admin', label: 'Admin', description: 'Users and categories' }
  ];

  let currentUser = $state<User | null>(null);
  let categories = $state<Category[]>([]);
  let locations = $state<Location[]>([]);
  let assets = $state<Asset[]>([]);
  let assetImages = $state<AssetImage[]>([]);
  let stockLevels = $state<StockLevel[]>([]);
  let bookings = $state<Booking[]>([]);
  let checkouts = $state<Checkout[]>([]);
  let returns = $state<ReturnRecord[]>([]);
  let qrCodes = $state<QrCode[]>([]);
  let users = $state<User[]>([]);
  let assetSearch = $state('');
  let selectedAssetId = $state('');
  let selectedAssetEvents = $state<ItemEvent[]>([]);
  let selectedLocationId = $state('');
  let resolvedQr = $state<QrResolve | null>(null);
  let selectedReturnCheckout = $state<Checkout | null>(null);
  let availability = $state<Availability | null>(null);
  let email = $state('admin@example.org');
  let password = $state('change-this-password');
  let loading = $state(true);
  let busy = $state(false);
  let message = $state('');
  let error = $state('');
  let activeTab = $state<WorkspaceTab>('dashboard');

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
  let assetEditForm = $state<AssetUpdate>({
    name: '',
    category_id: null,
    status: 'available',
    condition: 'unknown',
    home_location_id: null,
    current_location_id: null,
    current_holder_user_id: null,
    manufacturer: '',
    model: '',
    serial_number: '',
    asset_tag: '',
    replacement_value: null,
    description: '',
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
  const filteredAssets = $derived(assets.filter((asset) => assetMatchesSearch(asset, assetSearch)));

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
    [
      categories,
      locations,
      assets,
      assetImages,
      stockLevels,
      bookings,
      checkouts,
      returns,
      qrCodes,
      users
    ] = await Promise.all([
      apiGet<Category[]>('/categories'),
      apiGet<Location[]>('/locations'),
      apiGet<Asset[]>('/assets'),
      currentUser ? apiGet<AssetImage[]>('/assets/images') : Promise.resolve([]),
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
      assetImages = [];
      qrCodes = [];
      users = [];
      selectedAssetId = '';
      selectedAssetEvents = [];
      resetAssetEditForm();
      selectedLocationId = '';
      activeTab = 'dashboard';
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

  async function updateSelectedAsset() {
    await runAction(async () => {
      if (!selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      await apiPatch<Asset>(`/assets/${selectedAssetId}`, emptyStringsToNull(assetEditForm));
      await loadInventory();
      await selectAssetDetail(selectedAssetId);
      message = 'Asset updated';
    });
  }

  async function uploadSelectedAssetImage(file: File) {
    await runAction(async () => {
      if (!selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      const processed = await prepareAssetImage(file);
      const formData = new FormData();
      formData.append('file', processed);
      await apiUpload<AssetImage>(`/assets/${selectedAssetId}/image`, formData);
      await loadInventory();
      await selectAssetDetail(selectedAssetId);
      message = 'Asset photo updated';
    });
  }

  async function deleteSelectedAssetImage() {
    await runAction(async () => {
      if (!selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      await apiDelete<void>(`/assets/${selectedAssetId}/image`);
      await loadInventory();
      await selectAssetDetail(selectedAssetId);
      message = 'Asset photo deleted';
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

  async function moveSelectedTrackedAsset(payload: TrackedAssetTransfer): Promise<boolean> {
    const assetId = selectedAssetId;
    return await runAction(async () => {
      if (!assetId) {
        throw new Error('Choose a tracked item first.');
      }
      await apiPost<Asset>(`/assets/${assetId}/transfer`, emptyStringsToNull(payload));
      await loadInventory();
      await selectAssetDetail(assetId);
      message = 'Tracked item moved';
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

  async function moveSelectedStock(payload: StockTransfer): Promise<boolean> {
    const assetId = selectedAssetId;
    return await runAction(async () => {
      if (!assetId) {
        throw new Error('Choose a stock item first.');
      }
      await apiPost<StockLevel[]>('/stock-levels/transfer', emptyStringsToNull(payload));
      await loadInventory();
      await selectAssetDetail(assetId);
      message = 'Stock moved';
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

  async function selectAssetDetail(assetId: string) {
    await runAction(async () => {
      selectedAssetId = assetId;
      syncAssetEditForm(assets.find((asset) => asset.id === assetId));
      selectedAssetEvents = currentUser
        ? await apiGet<ItemEvent[]>(
            `/audit/item-events?asset_id=${encodeURIComponent(assetId)}&limit=50`
          )
        : [];
      message = 'Asset detail loaded';
    });
  }

  function resetAssetEditForm() {
    assetEditForm = {
      name: '',
      category_id: null,
      status: 'available',
      condition: 'unknown',
      home_location_id: null,
      current_location_id: null,
      current_holder_user_id: null,
      manufacturer: '',
      model: '',
      serial_number: '',
      asset_tag: '',
      replacement_value: null,
      description: '',
      notes: ''
    };
  }

  function syncAssetEditForm(asset: Asset | undefined) {
    if (!asset) {
      resetAssetEditForm();
      return;
    }
    assetEditForm = {
      name: asset.name,
      category_id: asset.category_id,
      status: asset.status,
      condition: asset.condition,
      home_location_id: asset.home_location_id,
      current_location_id: asset.current_location_id,
      current_holder_user_id: asset.current_holder_user_id,
      manufacturer: asset.manufacturer ?? '',
      model: asset.model ?? '',
      serial_number: asset.serial_number ?? '',
      asset_tag: asset.asset_tag ?? '',
      replacement_value: asset.replacement_value,
      description: asset.description ?? '',
      notes: asset.notes ?? ''
    };
  }

  async function runAction(action: () => Promise<void>): Promise<boolean> {
    busy = true;
    error = '';
    message = '';
    try {
      await action();
      return true;
    } catch (caught) {
      error = caught instanceof Error ? caught.message : 'Unknown error';
      return false;
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

  function visibleTabs(): { id: WorkspaceTab; label: string; description: string }[] {
    return workspaceTabs.filter((tab) => tab.id !== 'admin' || currentUser?.role === 'admin');
  }

  function switchTab(tab: WorkspaceTab) {
    activeTab = tab;
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

  function stockLocationName(id: string | null): string {
    return id === null
      ? 'No location'
      : (locations.find((location) => location.id === id)?.name ?? 'Unknown location');
  }

  function assetName(id: string): string {
    return assets.find((asset) => asset.id === id)?.name ?? 'Unknown asset';
  }

  function assetMatchesSearch(asset: Asset, query: string): boolean {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    if (!normalizedQuery) {
      return true;
    }

    return [
      asset.name,
      asset.asset_type,
      asset.status,
      asset.condition,
      asset.asset_tag,
      asset.serial_number,
      asset.manufacturer,
      asset.model,
      asset.description,
      asset.notes,
      categoryName(asset.category_id),
      locationName(asset.current_location_id),
      holderLabel(asset.current_holder_user_id)
    ]
      .filter((value): value is string => typeof value === 'string')
      .some((value) => value.toLocaleLowerCase().includes(normalizedQuery));
  }

  function selectedBookingAsset(): Asset | undefined {
    return assets.find((asset) => asset.id === bookingForm.asset_id);
  }

  function selectedAsset(): Asset | undefined {
    return assets.find((asset) => asset.id === selectedAssetId);
  }

  function assetImageForAsset(assetId: string): AssetImage | undefined {
    return assetImages.find((image) => image.asset_id === assetId);
  }

  function assetImageUrl(assetId: string): string | null {
    const image = assetImageForAsset(assetId);
    if (!image) {
      return null;
    }
    return apiUrl(
      `/assets/${encodeURIComponent(assetId)}/image/content?v=${encodeURIComponent(image.created_at)}`
    );
  }

  function selectedLocation(): Location | undefined {
    return locations.find((location) => location.id === selectedLocationId);
  }

  function stockLevelsAtLocation(locationId: string): StockLevel[] {
    return stockLevels.filter((level) => level.location_id === locationId);
  }

  function trackedAssetsAtLocation(locationId: string): Asset[] {
    return trackedAssets.filter((asset) => asset.current_location_id === locationId);
  }

  function totalStockAtLocation(locationId: string): number {
    return stockLevelsAtLocation(locationId).reduce((sum, level) => sum + level.quantity_total, 0);
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

  function userLabel(id: string | null): string {
    if (id === null) {
      return 'system';
    }
    if (currentUser?.id === id) {
      return currentUser.display_name;
    }
    return users.find((user) => user.id === id)?.display_name ?? 'user';
  }

  function holderLabel(id: string | null): string {
    return id === null ? 'No holder' : userLabel(id);
  }

  function responsibleLabel(id: string | null): string {
    return id === null ? 'No responsible person' : userLabel(id);
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
      <h1>Inventory workspace</h1>
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
    <WorkspaceTabs tabs={visibleTabs()} {activeTab} onSwitch={switchTab} />

    {#if activeTab === 'dashboard'}
      <DashboardPanel
        trackedAssetCount={trackedAssets.length}
        stockAssetCount={stockAssets.length}
        locationCount={locations.length}
        stockUnitCount={stockLevels.reduce((sum, level) => sum + level.quantity_total, 0)}
        bookingCount={bookings.length}
        checkoutCount={checkouts.length}
        returnCount={returns.length}
        qrCodeCount={qrCodes.length}
      />
    {/if}

    {#if currentUser && activeTab !== 'dashboard'}
      {#if activeTab === 'admin' && currentUser.role === 'admin'}
        <AdminPanel
          {categories}
          {users}
          {busy}
          bind:categoryForm
          bind:categoryUpdateForm
          bind:userCreateForm
          bind:userUpdateForm
          createCategory={() => void createCategory()}
          updateCategory={() => void updateCategory()}
          createUser={() => void createUser()}
          updateUser={() => void updateUser()}
          {selectCategoryForEdit}
          {selectUserForEdit}
        />
      {/if}

      {#if activeTab === 'locations'}
        <LocationsPanel
          {locationTypes}
          {locations}
          {stockAssets}
          {trackedAssets}
          {stockLevels}
          {selectedLocationId}
          {busy}
          bind:locationForm
          bind:stockForm
          bind:trackedTransferForm
          bind:stockTransferForm
          createLocation={() => void createLocation()}
          createStockLevel={() => void createStockLevel()}
          transferTrackedAssetAction={() => void transferTrackedAssetAction()}
          transferStockAction={() => void transferStockAction()}
          selectLocation={(locationId) => {
            selectedLocationId = locationId;
          }}
          closeLocationDetail={() => {
            selectedLocationId = '';
          }}
          {selectedLocation}
          {stockLevelsAtLocation}
          {trackedAssetsAtLocation}
          {totalStockAtLocation}
          {responsibleLabel}
          {stockAssetName}
          {stockLocationName}
          selectAssetDetail={(assetId) => void selectAssetDetail(assetId)}
        />
      {/if}

      {#if activeTab === 'bookings'}
        <BookingsPanel
          {assets}
          {locations}
          {bookings}
          {availability}
          {busy}
          bind:bookingForm
          {selectedBookingAsset}
          {assetName}
          createBooking={() => void createBooking()}
          previewBooking={() => void previewBooking()}
          {formatDateTime}
        />
      {/if}

      {#if activeTab === 'checkout'}
        <CheckoutPanel
          {bookings}
          {checkouts}
          {returns}
          {busy}
          bind:checkoutForm
          bind:returnForm
          {selectedReturnCheckout}
          createCheckout={() => void createCheckout()}
          createReturn={() => void createReturn()}
          loadCheckoutForReturn={() => void loadCheckoutForReturn()}
          {selectedReturnLine}
          {checkoutLabel}
          {returnLineLabel}
          {bookingTitle}
        />
      {/if}

      {#if activeTab === 'field'}
        <FieldQrPanel
          {qrCodes}
          {trackedAssets}
          {resolvedQr}
          {busy}
          bind:qrCreateForm
          bind:qrAssignForm
          bind:qrResolveToken
          createQrCode={() => void createQrCode()}
          assignQrCode={() => void assignQrCode()}
          resolveQrCode={() => void resolveQrCode()}
          {assetName}
        />
      {/if}

      {#if activeTab === 'inventory'}
        <InventoryPanel
          {assets}
          {categories}
          {locations}
          {users}
          {currentUser}
          {stockLevels}
          {filteredAssets}
          {selectedAssetEvents}
          {selectedAssetId}
          {busy}
          bind:assetForm
          bind:assetEditForm
          bind:assetSearch
          createAsset={() => void createAsset()}
          updateSelectedAsset={() => void updateSelectedAsset()}
          {moveSelectedTrackedAsset}
          {moveSelectedStock}
          uploadSelectedAssetImage={(file) => void uploadSelectedAssetImage(file)}
          deleteSelectedAssetImage={() => void deleteSelectedAssetImage()}
          selectAssetDetail={(assetId) => void selectAssetDetail(assetId)}
          closeAssetDetail={() => {
            selectedAssetId = '';
            selectedAssetEvents = [];
            resetAssetEditForm();
          }}
          {selectedAsset}
          {categoryName}
          {locationName}
          {holderLabel}
          {userLabel}
          {assetImageUrl}
          {formatDateTime}
        />
      {/if}
    {/if}
  {/if}
</main>
