<script lang="ts">
  import { PUBLIC_APP_BASE_URL } from '$env/static/public';
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
    type Basket,
    type BasketCreate,
    type BasketUpdate,
    type Booking,
    type BookingCreate,
    type BookingLineCreate,
    type BookingUpdate,
    type Category,
    type CategoryCreate,
    type CategoryUpdate,
    type Checkout,
    type CheckoutCreate,
    type ItemEvent,
    type Location,
    type LocationCreate,
    type LocationImage,
    type LocationType,
    type LocationUpdate,
    type MaintenanceComplete,
    type MaintenanceStart,
    type Person,
    type PersonCreate,
    type PersonUpdate,
    type QrCode,
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
  import AccountPanel from '$lib/components/workspace/AccountPanel.svelte';
  import AdminPanel from '$lib/components/workspace/AdminPanel.svelte';
  import BasketPanel from '$lib/components/workspace/BasketPanel.svelte';
  import BookingListPanel from '$lib/components/workspace/BookingListPanel.svelte';
  import BookingsPanel from '$lib/components/workspace/BookingsPanel.svelte';
  import DashboardPanel from '$lib/components/workspace/DashboardPanel.svelte';
  import InventoryPanel from '$lib/components/workspace/InventoryPanel.svelte';
  import LocationsPanel from '$lib/components/workspace/LocationsPanel.svelte';
  import PersonsPanel from '$lib/components/workspace/PersonsPanel.svelte';
  import { prepareAssetImage, prepareInventoryImage } from '$lib/image';
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
    { id: 'persons', label: 'Persons', description: 'Contacts, team, and borrowers' },
    { id: 'bookings', label: 'Bookings', description: 'Reservation list and details' },
    { id: 'stock', label: 'Stock', description: 'Stock availability heatmap' },
    { id: 'basket', label: 'Basket', description: 'Temporary held items' },
    { id: 'account', label: 'Account', description: 'Login and profile settings' },
    { id: 'admin', label: 'Admin', description: 'Users and categories' }
  ];

  type BookingDraftLine = BookingLineCreate & {
    client_id: string;
  };

  type BookingDraft = {
    title: string;
    person_id: string;
    starts_at: string;
    ends_at: string;
    notes: string;
    lines: BookingDraftLine[];
  };

  let currentUser = $state<User | null>(null);
  let categories = $state<Category[]>([]);
  let persons = $state<Person[]>([]);
  let locations = $state<Location[]>([]);
  let locationImages = $state<LocationImage[]>([]);
  let assets = $state<Asset[]>([]);
  let assetImages = $state<AssetImage[]>([]);
  let stockLevels = $state<StockLevel[]>([]);
  let activeBasket = $state<Basket | null>(null);
  let bookings = $state<Booking[]>([]);
  let checkouts = $state<Checkout[]>([]);
  let returns = $state<ReturnRecord[]>([]);
  let qrCodes = $state<QrCode[]>([]);
  let users = $state<User[]>([]);
  let assetSearch = $state('');
  let selectedAssetId = $state('');
  let selectedAssetEvents = $state<ItemEvent[]>([]);
  let selectedLocationId = $state('');
  let selectedPersonId = $state('');
  let availability = $state<Availability | null>(null);
  let email = $state('admin@example.org');
  let password = $state('change-this-password');
  let loading = $state(true);
  let busy = $state(false);
  let message = $state('');
  let error = $state('');
  let activeTab = $state<WorkspaceTab>('dashboard');
  let stockAvailabilityVersion = $state(0);
  let accountForm = $state({
    email: '',
    display_name: '',
    password: ''
  });

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
  let locationEditForm = $state<LocationUpdate>({
    name: '',
    type: 'storage',
    address: '',
    responsible_user_id: null,
    responsible_person_id: null,
    notes: '',
    is_active: true
  });
  let personForm = $state<PersonCreate>({
    display_name: '',
    person_type: 'user',
    email: null,
    phone: '',
    notes: '',
    user_id: null,
    is_active: true
  });
  let personEditForm = $state<PersonUpdate>({
    display_name: '',
    person_type: 'user',
    email: null,
    phone: '',
    notes: '',
    user_id: null,
    is_active: true
  });
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
  let bookingDraft = $state<BookingDraft>({
    title: '',
    person_id: '',
    starts_at: '',
    ends_at: '',
    notes: '',
    lines: []
  });
  let bookingDraftLineForm = $state({
    asset_id: '',
    location_id: '',
    quantity: 1,
    notes: ''
  });
  let basketTitle = $state('');
  let basketNotes = $state('');
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
      resetAccountForm();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        currentUser = null;
        resetAccountForm();
        return;
      }
      throw caught;
    }
  }

  async function loadInventory() {
    const [
      loadedCategories,
      loadedPersons,
      loadedLocations,
      loadedLocationImages,
      loadedAssets,
      loadedAssetImages,
      loadedStockLevels,
      loadedActiveBasket,
      bookingSummaries,
      loadedCheckouts,
      loadedReturns,
      loadedQrCodes,
      loadedUsers
    ] = await Promise.all([
      apiGet<Category[]>('/categories'),
      currentUser ? apiGet<Person[]>('/persons') : Promise.resolve([]),
      apiGet<Location[]>('/locations'),
      currentUser ? apiGet<LocationImage[]>('/locations/images') : Promise.resolve([]),
      apiGet<Asset[]>('/assets'),
      currentUser ? apiGet<AssetImage[]>('/assets/images') : Promise.resolve([]),
      apiGet<StockLevel[]>('/stock-levels'),
      currentUser ? apiGet<Basket | null>('/basket/active') : Promise.resolve(null),
      apiGet<Booking[]>('/bookings'),
      apiGet<Checkout[]>('/checkouts'),
      apiGet<ReturnRecord[]>('/returns'),
      currentUser ? apiGet<QrCode[]>('/qr-codes') : Promise.resolve([]),
      currentUser?.role === 'admin' ? apiGet<User[]>('/users') : Promise.resolve([])
    ]);
    categories = loadedCategories;
    persons = loadedPersons;
    locations = loadedLocations;
    locationImages = loadedLocationImages;
    assets = loadedAssets;
    assetImages = loadedAssetImages;
    stockLevels = loadedStockLevels;
    activeBasket = loadedActiveBasket;
    syncBasketForm();
    checkouts = loadedCheckouts;
    returns = loadedReturns;
    qrCodes = loadedQrCodes;
    users = loadedUsers;
    bookings = await Promise.all(
      bookingSummaries.map((booking) => apiGet<Booking>(`/bookings/${booking.id}`))
    );
    stockAvailabilityVersion += 1;
  }

  async function login() {
    await runAction(async () => {
      currentUser = await apiPost<User>('/auth/login', { email, password });
      resetAccountForm();
      await loadInventory();
      message = `Logged in as ${currentUser.email}`;
    });
  }

  async function logout() {
    await runAction(async () => {
      await apiPost<void>('/auth/logout');
      currentUser = null;
      assetImages = [];
      locationImages = [];
      activeBasket = null;
      basketTitle = '';
      basketNotes = '';
      qrCodes = [];
      users = [];
      persons = [];
      selectedAssetId = '';
      selectedAssetEvents = [];
      selectedLocationId = '';
      selectedPersonId = '';
      resetAssetEditForm();
      selectedLocationId = '';
      resetLocationEditForm('');
      activeTab = 'account';
      resetAccountForm();
      message = 'Logged out';
    });
  }

  async function saveAccount() {
    await runAction(async () => {
      const payload: UserUpdate = {
        email: accountForm.email,
        display_name: accountForm.display_name
      };
      if (accountForm.password) {
        payload.password = accountForm.password;
      }
      currentUser = await apiPatch<User>('/auth/me', payload);
      resetAccountForm();
      await loadInventory();
      message = 'Account updated';
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

  async function createPerson() {
    await runAction(async () => {
      await apiPost<Person>('/persons', emptyStringsToNull(personForm));
      personForm = {
        display_name: '',
        person_type: 'user',
        email: null,
        phone: '',
        notes: '',
        user_id: null,
        is_active: true
      };
      await loadInventory();
      message = 'Person created';
    });
  }

  async function updateSelectedPerson() {
    await runAction(async () => {
      if (!selectedPersonId) {
        throw new Error('Choose a person first.');
      }
      await apiPatch<Person>(`/persons/${selectedPersonId}`, emptyStringsToNull(personEditForm));
      await loadInventory();
      resetPersonEditForm(selectedPersonId);
      message = 'Person updated';
    });
  }

  async function deleteSelectedPerson(): Promise<boolean> {
    return await runAction(async () => {
      if (!selectedPersonId) {
        throw new Error('Choose a person first.');
      }
      await apiDelete<void>(`/persons/${selectedPersonId}`);
      selectedPersonId = '';
      resetPersonEditForm('');
      await loadInventory();
      message = 'Person deleted';
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

  async function updateSelectedLocation() {
    await runAction(async () => {
      if (!selectedLocationId) {
        throw new Error('Choose a location first.');
      }
      await apiPatch<Location>(
        `/locations/${selectedLocationId}`,
        emptyStringsToNull(locationEditForm)
      );
      await loadInventory();
      resetLocationEditForm(selectedLocationId);
      message = 'Location updated';
    });
  }

  async function deleteSelectedLocation(): Promise<boolean> {
    return await runAction(async () => {
      if (!selectedLocationId) {
        throw new Error('Choose a location first.');
      }
      await apiDelete<void>(`/locations/${selectedLocationId}`);
      selectedLocationId = '';
      resetLocationEditForm('');
      await loadInventory();
      message = 'Location deleted';
    });
  }

  async function uploadSelectedLocationImage(file: File) {
    await runAction(async () => {
      if (!selectedLocationId) {
        throw new Error('Choose a location first.');
      }
      const processed = await prepareInventoryImage(file);
      const formData = new FormData();
      formData.append('file', processed);
      await apiUpload<LocationImage>(`/locations/${selectedLocationId}/image`, formData);
      await loadInventory();
      resetLocationEditForm(selectedLocationId);
      message = 'Location photo updated';
    });
  }

  async function deleteSelectedLocationImage() {
    await runAction(async () => {
      if (!selectedLocationId) {
        throw new Error('Choose a location first.');
      }
      await apiDelete<void>(`/locations/${selectedLocationId}/image`);
      await loadInventory();
      resetLocationEditForm(selectedLocationId);
      message = 'Location photo deleted';
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

  async function deleteSelectedAsset(): Promise<boolean> {
    return await runAction(async () => {
      if (!selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      await apiDelete<void>(`/assets/${selectedAssetId}`);
      selectedAssetId = '';
      selectedAssetEvents = [];
      resetAssetEditForm();
      await loadInventory();
      message = 'Asset deleted';
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

  async function generateSelectedAssetQr() {
    await runAction(async () => {
      if (!selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      await apiPost<QrCode>(`/assets/${selectedAssetId}/qr`);
      await loadInventory();
      message = 'QR code ready';
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

  async function previewBooking(): Promise<boolean> {
    return await runAction(async () => {
      availability = await apiPost<Availability>('/bookings/availability', buildBookingPayload());
      message = availability.available ? 'Booking is available' : 'Booking has conflicts';
    });
  }

  async function createBooking(): Promise<boolean> {
    return await runAction(async () => {
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

  function clearBookingAvailability() {
    availability = null;
  }

  async function previewBookingDraft(): Promise<boolean> {
    return await runAction(async () => {
      availability = await apiPost<Availability>(
        '/bookings/availability',
        buildBookingDraftPayload()
      );
      message = availability.available
        ? 'Booking bundle is available'
        : 'Booking bundle has conflicts';
    });
  }

  async function createBookingDraft(): Promise<boolean> {
    return await runAction(async () => {
      const booking = await apiPost<Booking>('/bookings', buildBookingDraftPayload());
      resetBookingDraft();
      availability = null;
      await loadInventory();
      message = `Booking created: ${booking.title}`;
    });
  }

  async function updateBooking(bookingId: string, payload: BookingUpdate): Promise<boolean> {
    return await runAction(async () => {
      await apiPatch<Booking>(`/bookings/${bookingId}`, emptyStringsToNull(payload));
      await loadInventory();
      message = 'Booking updated';
    });
  }

  async function deleteBooking(bookingId: string): Promise<boolean> {
    return await runAction(async () => {
      await apiDelete<void>(`/bookings/${bookingId}`);
      await loadInventory();
      message = 'Booking deleted';
    });
  }

  async function addBookingFormToBasket(): Promise<boolean> {
    return await runAction(async () => {
      const asset = assets.find((entry) => entry.id === bookingForm.asset_id);
      if (!asset) {
        throw new Error('Choose an asset first.');
      }
      const basket = await ensureBasketFromBookingForm();
      activeBasket = await apiPost<Basket>(`/basket/${basket.id}/lines`, {
        asset_id: bookingForm.asset_id,
        location_id: asset.asset_type === 'stock' ? bookingForm.location_id : null,
        quantity: asset.asset_type === 'stock' ? bookingForm.quantity : null,
        notes: null
      });
      syncBasketForm();
      activeTab = 'basket';
      message = `Added ${asset.name} to basket`;
    });
  }

  async function updateBasket(): Promise<boolean> {
    return await runAction(async () => {
      if (!activeBasket) {
        throw new Error('No active basket.');
      }
      activeBasket = await apiPatch<Basket>(
        `/basket/${activeBasket.id}`,
        emptyStringsToNull<BasketUpdate>({
          title: basketTitle,
          person_id: activeBasket.person_id,
          notes: basketNotes,
          starts_at: activeBasket.starts_at,
          ends_at: activeBasket.ends_at
        })
      );
      syncBasketForm();
      message = 'Basket updated';
    });
  }

  async function removeBasketLine(lineId: string): Promise<boolean> {
    return await runAction(async () => {
      if (!activeBasket) {
        throw new Error('No active basket.');
      }
      await apiDelete<void>(`/basket/${activeBasket.id}/lines/${lineId}`);
      activeBasket = await apiGet<Basket | null>('/basket/active');
      syncBasketForm();
      if (!activeBasket?.lines.length) {
        activeTab = 'inventory';
      }
      message = 'Basket item removed';
    });
  }

  async function confirmBasket(): Promise<boolean> {
    return await runAction(async () => {
      if (!activeBasket) {
        throw new Error('No active basket.');
      }
      const booking = await apiPost<Booking>(`/basket/${activeBasket.id}/confirm`);
      activeBasket = null;
      basketTitle = '';
      basketNotes = '';
      await loadInventory();
      activeTab = 'bookings';
      message = `Booking created: ${booking.title}`;
    });
  }

  async function cancelBasket(): Promise<boolean> {
    return await runAction(async () => {
      if (!activeBasket) {
        throw new Error('No active basket.');
      }
      await apiPost<Basket>(`/basket/${activeBasket.id}/cancel`);
      activeBasket = null;
      basketTitle = '';
      basketNotes = '';
      activeTab = 'inventory';
      message = 'Basket cancelled';
    });
  }

  async function ensureBasketFromBookingForm(): Promise<Basket> {
    const payload: BasketCreate = {
      title: bookingDraft.title || bookingForm.title || 'New basket',
      person_id: bookingDraft.person_id,
      starts_at: new Date(bookingDraft.starts_at || bookingForm.starts_at).toISOString(),
      ends_at: new Date(bookingDraft.ends_at || bookingForm.ends_at).toISOString(),
      notes: bookingDraft.notes || null
    };
    activeBasket = await apiPost<Basket>('/basket', payload);
    syncBasketForm();
    return activeBasket;
  }

  function syncBasketForm(): void {
    basketTitle = activeBasket?.title ?? '';
    basketNotes = activeBasket?.notes ?? '';
  }

  function addBookingDraftLine(line: BookingLineCreate): void {
    bookingDraft.lines = [
      ...bookingDraft.lines,
      {
        ...line,
        client_id: crypto.randomUUID()
      }
    ];
    availability = null;
  }

  function addBookingDraftLineFromForm(): void {
    const asset = assets.find((entry) => entry.id === bookingDraftLineForm.asset_id);
    if (!asset) {
      error = 'Choose an asset first.';
      return;
    }
    if (asset.asset_type === 'stock' && !bookingDraftLineForm.location_id) {
      error = 'Choose a stock source location.';
      return;
    }
    addBookingDraftLine({
      asset_id: bookingDraftLineForm.asset_id,
      location_id: asset.asset_type === 'stock' ? bookingDraftLineForm.location_id : null,
      quantity: asset.asset_type === 'stock' ? bookingDraftLineForm.quantity : null,
      notes: bookingDraftLineForm.notes || null
    });
    bookingDraftLineForm = {
      asset_id: '',
      location_id: '',
      quantity: 1,
      notes: ''
    };
    message = 'Added line to booking bundle';
  }

  function removeBookingDraftLine(clientId: string): void {
    bookingDraft.lines = bookingDraft.lines.filter((line) => line.client_id !== clientId);
    availability = null;
  }

  function resetBookingDraft(): void {
    bookingDraft = {
      title: '',
      person_id: '',
      starts_at: '',
      ends_at: '',
      notes: '',
      lines: []
    };
    bookingDraftLineForm = {
      asset_id: '',
      location_id: '',
      quantity: 1,
      notes: ''
    };
  }

  async function createCheckoutForBooking(
    bookingId: string,
    conditionOut: CheckoutCreate['condition_out'],
    notes: string
  ): Promise<boolean> {
    return await runAction(async () => {
      const checkout = await apiPost<Checkout>(
        '/checkouts',
        emptyStringsToNull({
          booking_id: bookingId,
          condition_out: conditionOut,
          notes
        })
      );
      await loadInventory();
      message = `Checkout created for booking ${bookingTitle(checkout.booking_id)}`;
    });
  }

  async function loadCheckoutDetails(checkoutId: string): Promise<Checkout | null> {
    let checkout: Checkout | null = null;
    const loaded = await runAction(async () => {
      checkout = await apiGet<Checkout>(`/checkouts/${checkoutId}`);
      message = 'Checkout lines loaded';
    });
    return loaded ? checkout : null;
  }

  async function createReturnForCheckout(payload: ReturnCreate): Promise<boolean> {
    return await runAction(async () => {
      await apiPost<ReturnRecord>('/returns', payload);
      await loadInventory();
      message = 'Check in recorded';
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

  async function addSelectedStock(locationId: string, quantity: number): Promise<boolean> {
    const assetId = selectedAssetId;
    return await runAction(async () => {
      if (!assetId) {
        throw new Error('Choose a stock item first.');
      }
      await apiPost<StockLevel>('/stock-levels', {
        asset_id: assetId,
        location_id: locationId,
        quantity_total: quantity
      });
      await loadInventory();
      await selectAssetDetail(assetId);
      message = 'Stock added';
    });
  }

  async function removeSelectedStock(locationId: string, quantity: number): Promise<boolean> {
    const assetId = selectedAssetId;
    return await runAction(async () => {
      if (!assetId) {
        throw new Error('Choose a stock item first.');
      }
      const stockLevel = stockLevels.find(
        (level) => level.asset_id === assetId && level.location_id === locationId
      );
      if (!stockLevel) {
        throw new Error('No stock exists at this location.');
      }
      const availableQuantity = stockLevel.quantity_total - stockLevel.quantity_checked_out;
      if (quantity > availableQuantity) {
        throw new Error(`Only ${availableQuantity} available at this location.`);
      }
      await apiPatch<StockLevel>(`/stock-levels/${stockLevel.id}`, {
        quantity_total: stockLevel.quantity_total - quantity
      });
      await loadInventory();
      await selectAssetDetail(assetId);
      message = 'Stock removed';
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

  function buildBookingDraftPayload(): BookingCreate {
    if (!bookingDraft.lines.length) {
      throw new Error('Add at least one item to the booking bundle.');
    }
    return {
      title: bookingDraft.title,
      person_id: bookingDraft.person_id,
      starts_at: new Date(bookingDraft.starts_at).toISOString(),
      ends_at: new Date(bookingDraft.ends_at).toISOString(),
      notes: bookingDraft.notes || null,
      lines: bookingDraft.lines.map(({ client_id: _clientId, ...line }) => line)
    };
  }

  function visibleTabs(): { id: WorkspaceTab; label: string; description: string }[] {
    return workspaceTabs.filter((tab) => {
      if (tab.id === 'admin') {
        return currentUser?.role === 'admin';
      }
      return true;
    });
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

  function selectedBookingDraftAsset(): Asset | undefined {
    return assets.find((asset) => asset.id === bookingDraftLineForm.asset_id);
  }

  function personName(id: string | null): string {
    return id === null
      ? 'No person'
      : (persons.find((person) => person.id === id)?.display_name ?? 'Unknown person');
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

  function qrCodeForAsset(assetId: string): QrCode | undefined {
    return qrCodes.find((qrCode) => qrCode.asset_id === assetId);
  }

  function qrScanUrl(token: string): string {
    return `${PUBLIC_APP_BASE_URL.replace(/\/$/, '')}/qr/${encodeURIComponent(token)}`;
  }

  function locationImageForLocation(locationId: string): LocationImage | undefined {
    return locationImages.find((image) => image.location_id === locationId);
  }

  function locationImageUrl(locationId: string): string | null {
    const image = locationImageForLocation(locationId);
    if (!image) {
      return null;
    }
    return apiUrl(
      `/locations/${encodeURIComponent(locationId)}/image/content?v=${encodeURIComponent(image.created_at)}`
    );
  }

  function selectedLocation(): Location | undefined {
    return locations.find((location) => location.id === selectedLocationId);
  }

  function selectLocationDetail(locationId: string): void {
    selectedLocationId = locationId;
    resetLocationEditForm(locationId);
  }

  function resetLocationEditForm(locationId: string): void {
    const location = locations.find((entry) => entry.id === locationId);
    locationEditForm = {
      name: location?.name ?? '',
      type: location?.type ?? 'storage',
      address: location?.address ?? '',
      responsible_user_id: location?.responsible_user_id ?? null,
      responsible_person_id: location?.responsible_person_id ?? null,
      notes: location?.notes ?? '',
      is_active: location?.is_active ?? true
    };
  }

  function selectedPerson(): Person | undefined {
    return persons.find((person) => person.id === selectedPersonId);
  }

  function selectPersonDetail(personId: string): void {
    selectedPersonId = personId;
    resetPersonEditForm(personId);
  }

  function resetPersonEditForm(personId: string): void {
    const person = persons.find((entry) => entry.id === personId);
    personEditForm = {
      display_name: person?.display_name ?? '',
      person_type: person?.person_type ?? 'user',
      email: person?.email ?? null,
      phone: person?.phone ?? '',
      notes: person?.notes ?? '',
      user_id: person?.user_id ?? null,
      is_active: person?.is_active ?? true
    };
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

  function bookingTitle(id: string): string {
    return bookings.find((booking) => booking.id === id)?.title ?? 'Unknown booking';
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
    if (id === null) {
      return 'No responsible person';
    }
    return persons.find((person) => person.id === id)?.display_name ?? 'Unknown person';
  }

  function resetAccountForm(): void {
    accountForm = {
      email: currentUser?.email ?? '',
      display_name: currentUser?.display_name ?? '',
      password: ''
    };
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
    <h1>NICA e.V. Inventar</h1>
    <div class="header-actions">
      <button
        type="button"
        class="basket-button"
        aria-label="Open basket"
        onclick={() => (activeTab = 'basket')}
      >
        <span class="basket-icon" aria-hidden="true"></span>
        <strong>{activeBasket?.lines.length ?? 0}</strong>
      </button>
      <button
        type="button"
        class="account-button"
        class:logged-out-account={!currentUser}
        aria-label={currentUser ? 'Account' : 'Login'}
        onclick={() => (activeTab = 'account')}
      >
        <span class="account-avatar" aria-hidden="true">
          {currentUser ? currentUser.display_name.slice(0, 1).toUpperCase() : ''}
        </span>
      </button>
    </div>
  </section>

  <section class="workspace-frame">
    {#if loading}
      <section class="panel loading-panel">Loading inventory workspace...</section>
    {:else}
      <WorkspaceTabs tabs={visibleTabs()} {activeTab} onSwitch={switchTab} />

      <section class="workspace-content">
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

        {#if activeTab === 'account'}
          <AccountPanel
            {currentUser}
            {busy}
            bind:email
            bind:password
            bind:accountForm
            login={() => void login()}
            logout={() => void logout()}
            saveAccount={() => void saveAccount()}
          />
        {/if}

        {#if activeTab === 'basket'}
          <BasketPanel
            basket={activeBasket}
            {assets}
            {busy}
            bind:basketTitle
            bind:basketNotes
            {updateBasket}
            {removeBasketLine}
            {confirmBasket}
            {cancelBasket}
            {assetName}
            {locationName}
            {personName}
            {formatDateTime}
          />
        {/if}

        {#if currentUser && activeTab !== 'dashboard' && activeTab !== 'account' && activeTab !== 'basket'}
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
            />
          {/if}

          {#if activeTab === 'locations'}
            <LocationsPanel
              {locationTypes}
              {persons}
              {locations}
              {selectedLocationId}
              {busy}
              bind:locationForm
              bind:locationEditForm
              createLocation={() => void createLocation()}
              {selectLocationDetail}
              updateSelectedLocation={() => void updateSelectedLocation()}
              {deleteSelectedLocation}
              closeLocationDetail={() => {
                selectedLocationId = '';
                resetLocationEditForm('');
              }}
              {selectedLocation}
              {stockLevelsAtLocation}
              {trackedAssetsAtLocation}
              {totalStockAtLocation}
              {responsibleLabel}
              {locationImageUrl}
              uploadSelectedLocationImage={(file) => void uploadSelectedLocationImage(file)}
              deleteSelectedLocationImage={() => void deleteSelectedLocationImage()}
            />
          {/if}

          {#if activeTab === 'persons'}
            <PersonsPanel
              {persons}
              {bookings}
              {locations}
              {users}
              {selectedPersonId}
              {busy}
              bind:personForm
              bind:personEditForm
              createPerson={() => void createPerson()}
              updateSelectedPerson={() => void updateSelectedPerson()}
              {deleteSelectedPerson}
              {selectPersonDetail}
              closePersonDetail={() => {
                selectedPersonId = '';
                resetPersonEditForm('');
              }}
              {selectedPerson}
              {userLabel}
            />
          {/if}

          {#if activeTab === 'stock'}
            <BookingsPanel
              {assets}
              {persons}
              {locations}
              {bookings}
              {stockAvailabilityVersion}
              {availability}
              {busy}
              bind:bookingDraft
              bind:bookingDraftLineForm
              {selectedBookingDraftAsset}
              {assetName}
              {createBookingDraft}
              {previewBookingDraft}
              {addBookingDraftLineFromForm}
              {removeBookingDraftLine}
              {resetBookingDraft}
              {clearBookingAvailability}
            />
          {/if}

          {#if activeTab === 'bookings'}
            <BookingListPanel
              {bookings}
              {checkouts}
              {assets}
              {persons}
              {users}
              {busy}
              {assetName}
              {locationName}
              {personName}
              {userLabel}
              {formatDateTime}
              {updateBooking}
              {deleteBooking}
              {createCheckoutForBooking}
              {loadCheckoutDetails}
              {createReturnForCheckout}
            />
          {/if}

          {#if activeTab === 'inventory'}
            <InventoryPanel
              {assets}
              {categories}
              {locations}
              {persons}
              {users}
              {currentUser}
              {stockLevels}
              {bookings}
              {checkouts}
              {returns}
              {filteredAssets}
              {selectedAssetEvents}
              {selectedAssetId}
              {qrCodes}
              {busy}
              bind:assetForm
              bind:assetEditForm
              bind:assetSearch
              bind:bookingForm
              bind:bookingDraft
              createAsset={() => void createAsset()}
              updateSelectedAsset={() => void updateSelectedAsset()}
              {deleteSelectedAsset}
              {moveSelectedTrackedAsset}
              {moveSelectedStock}
              {addSelectedStock}
              {removeSelectedStock}
              {addBookingFormToBasket}
              {clearBookingAvailability}
              uploadSelectedAssetImage={(file) => void uploadSelectedAssetImage(file)}
              deleteSelectedAssetImage={() => void deleteSelectedAssetImage()}
              generateSelectedAssetQr={() => void generateSelectedAssetQr()}
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
              {qrCodeForAsset}
              {qrScanUrl}
              {formatDateTime}
            />
          {/if}
        {/if}
      </section>
    {/if}
  </section>

  {#if error || message}
    <section class="notice-dock" aria-live="polite">
      {#if error}
        <p class="notice error">{error}</p>
      {/if}
      {#if message}
        <p class="notice success">{message}</p>
      {/if}
    </section>
  {/if}
</main>
