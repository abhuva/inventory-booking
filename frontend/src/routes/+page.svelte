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
    type BasketLineUpdate,
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
  import { adminApi } from '$lib/api/admin';
  import { authApi } from '$lib/api/auth';
  import { basketApi } from '$lib/api/basket';
  import { bookingsApi } from '$lib/api/bookings';
  import { inventoryApi } from '$lib/api/inventory';
  import { locationsApi } from '$lib/api/locations';
  import { operationsApi } from '$lib/api/operations';
  import { personsApi } from '$lib/api/persons';
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
  import { createAuthState } from '$lib/workspace/auth-state.svelte';
  import { createBasketState } from '$lib/workspace/basket-state.svelte';
  import { createBookingState, type BookingDraftLine } from '$lib/workspace/booking-state.svelte';
  import { createInventoryState } from '$lib/workspace/inventory-state.svelte';
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

  const auth = createAuthState();
  let categories = $state<Category[]>([]);
  let persons = $state<Person[]>([]);
  let locations = $state<Location[]>([]);
  let locationImages = $state<LocationImage[]>([]);
  let assets = $state<Asset[]>([]);
  let assetImages = $state<AssetImage[]>([]);
  let stockLevels = $state<StockLevel[]>([]);
  const basketState = createBasketState();
  const bookingState = createBookingState();
  const inventoryState = createInventoryState();
  let bookings = $state<Booking[]>([]);
  let checkouts = $state<Checkout[]>([]);
  let returns = $state<ReturnRecord[]>([]);
  let qrCodes = $state<QrCode[]>([]);
  let users = $state<User[]>([]);
  let selectedLocationId = $state('');
  let selectedPersonId = $state('');
  let loading = $state(true);
  let busy = $state(false);
  let message = $state('');
  let error = $state('');
  let activeTab = $state<WorkspaceTab>('dashboard');
  let stockAvailabilityVersion = $state(0);
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
  let locationForm = $state<LocationCreate>({ name: '', type: 'storage', is_active: true });
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
  const trackedAssets = $derived(assets.filter((asset) => asset.asset_type === 'tracked'));
  const stockAssets = $derived(assets.filter((asset) => asset.asset_type === 'stock'));
  const filteredAssets = $derived(
    assets.filter((asset) => assetMatchesSearch(asset, inventoryState.assetSearch))
  );

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
      auth.currentUser = await authApi.currentUser();
      resetAccountForm();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        auth.currentUser = null;
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
      adminApi.listCategories(),
      auth.currentUser ? personsApi.listPersons() : Promise.resolve([]),
      locationsApi.listLocations(),
      auth.currentUser ? locationsApi.listLocationImages() : Promise.resolve([]),
      inventoryApi.listAssets(),
      auth.currentUser ? inventoryApi.listAssetImages() : Promise.resolve([]),
      inventoryApi.listStockLevels(),
      auth.currentUser ? basketApi.activeBasket() : Promise.resolve(null),
      bookingsApi.listBookings(),
      operationsApi.listCheckouts(),
      operationsApi.listReturns(),
      auth.currentUser ? inventoryApi.listQrCodes() : Promise.resolve([]),
      auth.currentUser?.role === 'admin' ? adminApi.listUsers() : Promise.resolve([])
    ]);
    categories = loadedCategories;
    persons = loadedPersons;
    locations = loadedLocations;
    locationImages = loadedLocationImages;
    assets = loadedAssets;
    assetImages = loadedAssetImages;
    stockLevels = loadedStockLevels;
    basketState.activeBasket = loadedActiveBasket;
    syncBasketForm();
    checkouts = loadedCheckouts;
    returns = loadedReturns;
    qrCodes = loadedQrCodes;
    users = loadedUsers;
    bookings = await Promise.all(
      bookingSummaries.map((booking) => bookingsApi.getBooking(booking.id))
    );
    stockAvailabilityVersion += 1;
  }

  async function login() {
    await runAction(async () => {
      auth.currentUser = await authApi.login({ email: auth.email, password: auth.password });
      resetAccountForm();
      await loadInventory();
      message = `Logged in as ${auth.currentUser.email}`;
    });
  }

  async function logout() {
    await runAction(async () => {
      await authApi.logout();
      auth.currentUser = null;
      assetImages = [];
      locationImages = [];
      basketState.clear();
      qrCodes = [];
      users = [];
      persons = [];
      inventoryState.clearSelection();
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
        email: auth.accountForm.email,
        display_name: auth.accountForm.display_name
      };
      if (auth.accountForm.password) {
        payload.password = auth.accountForm.password;
      }
      auth.currentUser = await authApi.updateCurrentUser(payload);
      resetAccountForm();
      await loadInventory();
      message = 'Account updated';
    });
  }

  async function createCategory() {
    await runAction(async () => {
      await adminApi.createCategory(emptyStringsToNull(categoryForm));
      categoryForm = { name: '', description: '' };
      await loadInventory();
      message = 'Category created';
    });
  }

  async function updateCategory() {
    await runAction(async () => {
      const { category_id: categoryId, ...payload } = categoryUpdateForm;
      await adminApi.updateCategory(categoryId, emptyStringsToNull(payload));
      categoryUpdateForm = { category_id: '', name: '', description: '' };
      await loadInventory();
      message = 'Category updated';
    });
  }

  async function createUser() {
    await runAction(async () => {
      await adminApi.createUser(userCreateForm);
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
      await adminApi.updateUser(userUpdateForm.user_id, payload);
      userUpdateForm.password = '';
      await loadInventory();
      message = 'User updated';
    });
  }

  async function createPerson() {
    await runAction(async () => {
      await personsApi.createPerson(emptyStringsToNull(personForm));
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
      await personsApi.updatePerson(selectedPersonId, emptyStringsToNull(personEditForm));
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
      await personsApi.deletePerson(selectedPersonId);
      selectedPersonId = '';
      resetPersonEditForm('');
      await loadInventory();
      message = 'Person deleted';
    });
  }

  async function createLocation() {
    await runAction(async () => {
      await locationsApi.createLocation(locationForm);
      locationForm = { name: '', type: 'storage', is_active: true };
      await loadInventory();
      message = 'Location created';
    });
  }

  async function updateSelectedLocation() {
    await runAction(async () => {
      if (!selectedLocationId) {
        throw new Error('Choose a location first.');
      }
      await locationsApi.updateLocation(selectedLocationId, emptyStringsToNull(locationEditForm));
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
      await locationsApi.deleteLocation(selectedLocationId);
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
      await locationsApi.uploadLocationImage(selectedLocationId, formData);
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
      await locationsApi.deleteLocationImage(selectedLocationId);
      await loadInventory();
      resetLocationEditForm(selectedLocationId);
      message = 'Location photo deleted';
    });
  }

  async function createAsset() {
    await runAction(async () => {
      const payload: AssetCreate = {
        ...emptyStringsToNull(inventoryState.assetForm),
        unit_name:
          inventoryState.assetForm.asset_type === 'stock'
            ? inventoryState.assetForm.unit_name
            : null
      };
      await inventoryApi.createAsset(payload);
      inventoryState.resetAssetForm();
      await loadInventory();
      message = 'Asset created';
    });
  }

  async function updateSelectedAsset() {
    await runAction(async () => {
      if (!inventoryState.selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      await inventoryApi.updateAsset(
        inventoryState.selectedAssetId,
        emptyStringsToNull(inventoryState.assetEditForm)
      );
      await loadInventory();
      await selectAssetDetail(inventoryState.selectedAssetId);
      message = 'Asset updated';
    });
  }

  async function deleteSelectedAsset(): Promise<boolean> {
    return await runAction(async () => {
      if (!inventoryState.selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      await inventoryApi.deleteAsset(inventoryState.selectedAssetId);
      inventoryState.clearSelection();
      await loadInventory();
      message = 'Asset deleted';
    });
  }

  async function uploadSelectedAssetImage(file: File) {
    await runAction(async () => {
      if (!inventoryState.selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      const processed = await prepareAssetImage(file);
      const formData = new FormData();
      formData.append('file', processed);
      await inventoryApi.uploadAssetImage(inventoryState.selectedAssetId, formData);
      await loadInventory();
      await selectAssetDetail(inventoryState.selectedAssetId);
      message = 'Asset photo updated';
    });
  }

  async function deleteSelectedAssetImage() {
    await runAction(async () => {
      if (!inventoryState.selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      await inventoryApi.deleteAssetImage(inventoryState.selectedAssetId);
      await loadInventory();
      await selectAssetDetail(inventoryState.selectedAssetId);
      message = 'Asset photo deleted';
    });
  }

  async function generateSelectedAssetQr() {
    await runAction(async () => {
      if (!inventoryState.selectedAssetId) {
        throw new Error('Choose an asset first.');
      }
      await inventoryApi.generateAssetQr(inventoryState.selectedAssetId);
      await loadInventory();
      message = 'QR code ready';
    });
  }

  async function createStockLevel() {
    await runAction(async () => {
      await inventoryApi.createStockLevel(inventoryState.stockForm);
      inventoryState.resetStockForm();
      await loadInventory();
      message = 'Stock level created';
    });
  }

  async function previewBooking(): Promise<boolean> {
    return await runAction(async () => {
      bookingState.availability = await bookingsApi.previewAvailability(buildBookingPayload());
      message = bookingState.availability.available
        ? 'Booking is available'
        : 'Booking has conflicts';
    });
  }

  async function createBooking(): Promise<boolean> {
    return await runAction(async () => {
      const booking = await bookingsApi.createBooking(buildBookingPayload());
      bookingState.resetBookingForm();
      await loadInventory();
      message = `Booking created: ${booking.title}`;
    });
  }

  function clearBookingAvailability() {
    bookingState.clearAvailability();
  }

  async function previewBookingDraft(): Promise<boolean> {
    return await runAction(async () => {
      bookingState.availability = await bookingsApi.previewAvailability(buildBookingDraftPayload());
      message = bookingState.availability.available
        ? 'Booking bundle is available'
        : 'Booking bundle has conflicts';
    });
  }

  async function createBookingDraft(): Promise<boolean> {
    return await runAction(async () => {
      const booking = await bookingsApi.createBooking(buildBookingDraftPayload());
      resetBookingDraft();
      await loadInventory();
      message = `Booking created: ${booking.title}`;
    });
  }

  async function updateBooking(bookingId: string, payload: BookingUpdate): Promise<boolean> {
    return await runAction(async () => {
      await bookingsApi.updateBooking(bookingId, emptyStringsToNull(payload));
      await loadInventory();
      message = 'Booking updated';
    });
  }

  async function deleteBooking(bookingId: string): Promise<boolean> {
    return await runAction(async () => {
      await bookingsApi.deleteBooking(bookingId);
      await loadInventory();
      message = 'Booking deleted';
    });
  }

  async function addBookingFormToBasket(): Promise<boolean> {
    return await runAction(async () => {
      const asset = assets.find((entry) => entry.id === bookingState.bookingForm.asset_id);
      if (!asset) {
        throw new Error('Choose an asset first.');
      }
      const basket = await ensureBasketFromBookingForm();
      basketState.activeBasket = await basketApi.addLine(basket.id, {
        asset_id: bookingState.bookingForm.asset_id,
        location_id: asset.asset_type === 'stock' ? bookingState.bookingForm.location_id : null,
        starts_at: new Date(bookingState.bookingForm.starts_at).toISOString(),
        ends_at: new Date(bookingState.bookingForm.ends_at).toISOString(),
        quantity: asset.asset_type === 'stock' ? bookingState.bookingForm.quantity : null,
        notes: null
      });
      syncBasketForm();
      activeTab = 'basket';
      message = `Added ${asset.name} to basket`;
    });
  }

  async function updateBasket(): Promise<boolean> {
    return await runAction(async () => {
      if (!basketState.activeBasket) {
        throw new Error('No active basket.');
      }
      basketState.activeBasket = await basketApi.updateBasket(
        basketState.activeBasket.id,
        emptyStringsToNull<BasketUpdate>({
          title: basketState.basketTitle,
          person_id: basketState.activeBasket.person_id,
          notes: basketState.basketNotes,
          starts_at: basketState.activeBasket.starts_at,
          ends_at: basketState.activeBasket.ends_at
        })
      );
      syncBasketForm();
      message = 'Basket updated';
    });
  }

  async function removeBasketLine(lineId: string): Promise<boolean> {
    return await runAction(async () => {
      if (!basketState.activeBasket) {
        throw new Error('No active basket.');
      }
      await basketApi.removeLine(basketState.activeBasket.id, lineId);
      basketState.activeBasket = await basketApi.activeBasket();
      syncBasketForm();
      if (!basketState.activeBasket?.lines.length) {
        activeTab = 'inventory';
      }
      message = 'Basket item removed';
    });
  }

  async function updateBasketLine(lineId: string, payload: BasketLineUpdate): Promise<boolean> {
    return await runAction(async () => {
      if (!basketState.activeBasket) {
        throw new Error('No active basket.');
      }
      basketState.activeBasket = await basketApi.updateLine(
        basketState.activeBasket.id,
        lineId,
        emptyStringsToNull<BasketLineUpdate>(payload)
      );
      syncBasketForm();
      message = 'Basket item updated';
    });
  }

  async function confirmBasket(): Promise<boolean> {
    return await runAction(async () => {
      if (!basketState.activeBasket) {
        throw new Error('No active basket.');
      }
      const booking = await basketApi.confirmBasket(basketState.activeBasket.id);
      basketState.clear();
      await loadInventory();
      activeTab = 'bookings';
      message = `Booking created: ${booking.title}`;
    });
  }

  async function cancelBasket(): Promise<boolean> {
    return await runAction(async () => {
      if (!basketState.activeBasket) {
        throw new Error('No active basket.');
      }
      await basketApi.cancelBasket(basketState.activeBasket.id);
      basketState.clear();
      activeTab = 'inventory';
      message = 'Basket cancelled';
    });
  }

  async function ensureBasketFromBookingForm(): Promise<Basket> {
    const payload: BasketCreate = {
      title: bookingState.bookingDraft.title || bookingState.bookingForm.title || 'New basket',
      person_id: bookingState.bookingDraft.person_id,
      starts_at: new Date(
        bookingState.bookingDraft.starts_at || bookingState.bookingForm.starts_at
      ).toISOString(),
      ends_at: new Date(
        bookingState.bookingDraft.ends_at || bookingState.bookingForm.ends_at
      ).toISOString(),
      notes: bookingState.bookingDraft.notes || null
    };
    basketState.activeBasket = await basketApi.createBasket(payload);
    syncBasketForm();
    return basketState.activeBasket;
  }

  function syncBasketForm(): void {
    basketState.syncForm();
  }

  function addBookingDraftLine(line: BookingLineCreate): void {
    bookingState.addDraftLine(line);
  }

  function addBookingDraftLineFromForm(): void {
    const asset = assets.find((entry) => entry.id === bookingState.bookingDraftLineForm.asset_id);
    if (!asset) {
      error = 'Choose an asset first.';
      return;
    }
    if (asset.asset_type === 'stock' && !bookingState.bookingDraftLineForm.location_id) {
      error = 'Choose a stock source location.';
      return;
    }
    addBookingDraftLine({
      asset_id: bookingState.bookingDraftLineForm.asset_id,
      location_id:
        asset.asset_type === 'stock' ? bookingState.bookingDraftLineForm.location_id : null,
      starts_at: new Date(bookingState.bookingDraft.starts_at).toISOString(),
      ends_at: new Date(bookingState.bookingDraft.ends_at).toISOString(),
      quantity: asset.asset_type === 'stock' ? bookingState.bookingDraftLineForm.quantity : null,
      notes: bookingState.bookingDraftLineForm.notes || null
    });
    bookingState.resetDraftLineForm();
    message = 'Added line to booking bundle';
  }

  function removeBookingDraftLine(clientId: string): void {
    bookingState.removeDraftLine(clientId);
  }

  function resetBookingDraft(): void {
    bookingState.resetDraft();
  }

  async function createCheckoutForBooking(
    bookingId: string,
    conditionOut: CheckoutCreate['condition_out'],
    notes: string
  ): Promise<boolean> {
    return await runAction(async () => {
      const checkout = await operationsApi.createCheckout(
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
      checkout = await operationsApi.getCheckout(checkoutId);
      message = 'Checkout lines loaded';
    });
    return loaded ? checkout : null;
  }

  async function createReturnForCheckout(payload: ReturnCreate): Promise<boolean> {
    return await runAction(async () => {
      await operationsApi.createReturn(payload);
      await loadInventory();
      message = 'Check in recorded';
    });
  }

  async function transferTrackedAssetAction() {
    await runAction(async () => {
      const { asset_id, ...payload } = inventoryState.trackedTransferForm;
      await inventoryApi.transferTrackedAsset(asset_id, emptyStringsToNull(payload));
      inventoryState.resetTrackedTransferForm();
      await loadInventory();
      message = 'Tracked asset transferred';
    });
  }

  async function moveSelectedTrackedAsset(payload: TrackedAssetTransfer): Promise<boolean> {
    const assetId = inventoryState.selectedAssetId;
    return await runAction(async () => {
      if (!assetId) {
        throw new Error('Choose a tracked item first.');
      }
      await inventoryApi.transferTrackedAsset(assetId, emptyStringsToNull(payload));
      await loadInventory();
      await selectAssetDetail(assetId);
      message = 'Tracked item moved';
    });
  }

  async function transferStockAction() {
    await runAction(async () => {
      await inventoryApi.transferStock(emptyStringsToNull(inventoryState.stockTransferForm));
      inventoryState.resetStockTransferForm();
      await loadInventory();
      message = 'Stock transferred';
    });
  }

  async function moveSelectedStock(payload: StockTransfer): Promise<boolean> {
    const assetId = inventoryState.selectedAssetId;
    return await runAction(async () => {
      if (!assetId) {
        throw new Error('Choose a stock item first.');
      }
      await inventoryApi.transferStock(emptyStringsToNull(payload));
      await loadInventory();
      await selectAssetDetail(assetId);
      message = 'Stock moved';
    });
  }

  async function addSelectedStock(locationId: string, quantity: number): Promise<boolean> {
    const assetId = inventoryState.selectedAssetId;
    return await runAction(async () => {
      if (!assetId) {
        throw new Error('Choose a stock item first.');
      }
      await inventoryApi.createStockLevel({
        asset_id: assetId,
        location_id: locationId,
        quantity_checked_out: 0,
        quantity_reserved: 0,
        quantity_total: quantity
      });
      await loadInventory();
      await selectAssetDetail(assetId);
      message = 'Stock added';
    });
  }

  async function removeSelectedStock(locationId: string, quantity: number): Promise<boolean> {
    const assetId = inventoryState.selectedAssetId;
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
      await inventoryApi.updateStockLevel(stockLevel.id, {
        quantity_total: stockLevel.quantity_total - quantity
      });
      await loadInventory();
      await selectAssetDetail(assetId);
      message = 'Stock removed';
    });
  }

  async function changeAssetOperationalState() {
    await runAction(async () => {
      const assetId = inventoryState.assetStateForm.asset_id;
      if (inventoryState.assetStateForm.action === 'maintenance_start') {
        const payload: MaintenanceStart = { notes: inventoryState.assetStateForm.notes || null };
        await inventoryApi.startMaintenance(assetId, payload);
      } else if (inventoryState.assetStateForm.action === 'maintenance_complete') {
        const payload: MaintenanceComplete = {
          condition: inventoryState.assetStateForm.condition as MaintenanceComplete['condition'],
          notes: inventoryState.assetStateForm.notes || null
        };
        await inventoryApi.completeMaintenance(assetId, payload);
      } else {
        const payload: AssetStateChange = {
          status: inventoryState.assetStateForm.status as AssetStateChange['status'],
          condition: inventoryState.assetStateForm.condition as AssetStateChange['condition'],
          notes: inventoryState.assetStateForm.notes || null
        };
        await inventoryApi.changeAssetState(assetId, payload);
      }
      inventoryState.resetAssetStateForm();
      await loadInventory();
      message = 'Asset state updated';
    });
  }

  async function selectAssetDetail(assetId: string) {
    await runAction(async () => {
      inventoryState.selectedAssetId = assetId;
      syncAssetEditForm(assets.find((asset) => asset.id === assetId));
      inventoryState.selectedAssetEvents = auth.currentUser
        ? await inventoryApi.getAssetEvents(assetId)
        : [];
      message = 'Asset detail loaded';
    });
  }

  function resetAssetEditForm() {
    inventoryState.resetAssetEditForm();
  }

  function syncAssetEditForm(asset: Asset | undefined) {
    inventoryState.syncAssetEditForm(asset);
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
    const asset = assets.find((entry) => entry.id === bookingState.bookingForm.asset_id);
    const isStock = asset?.asset_type === 'stock';
    return {
      title: bookingState.bookingForm.title,
      starts_at: new Date(bookingState.bookingForm.starts_at).toISOString(),
      ends_at: new Date(bookingState.bookingForm.ends_at).toISOString(),
      lines: [
        {
          asset_id: bookingState.bookingForm.asset_id,
          location_id: isStock ? bookingState.bookingForm.location_id : null,
          starts_at: new Date(bookingState.bookingForm.starts_at).toISOString(),
          ends_at: new Date(bookingState.bookingForm.ends_at).toISOString(),
          quantity: isStock ? bookingState.bookingForm.quantity : null
        }
      ]
    };
  }

  function buildBookingDraftPayload(): BookingCreate {
    if (!bookingState.bookingDraft.lines.length) {
      throw new Error('Add at least one item to the booking bundle.');
    }
    return {
      title: bookingState.bookingDraft.title,
      person_id: bookingState.bookingDraft.person_id,
      starts_at: new Date(bookingState.bookingDraft.starts_at).toISOString(),
      ends_at: new Date(bookingState.bookingDraft.ends_at).toISOString(),
      notes: bookingState.bookingDraft.notes || null,
      lines: bookingState.bookingDraft.lines.map((draftLine: BookingDraftLine) => {
        const { client_id: _clientId, ...line } = draftLine;
        return line;
      })
    };
  }

  function visibleTabs(): { id: WorkspaceTab; label: string; description: string }[] {
    return workspaceTabs.filter((tab) => {
      if (tab.id === 'admin') {
        return auth.currentUser?.role === 'admin';
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
    return assets.find((asset) => asset.id === bookingState.bookingForm.asset_id);
  }

  function selectedBookingDraftAsset(): Asset | undefined {
    return assets.find((asset) => asset.id === bookingState.bookingDraftLineForm.asset_id);
  }

  function personName(id: string | null): string {
    return id === null
      ? 'No person'
      : (persons.find((person) => person.id === id)?.display_name ?? 'Unknown person');
  }

  function selectedAsset(): Asset | undefined {
    return assets.find((asset) => asset.id === inventoryState.selectedAssetId);
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
    if (auth.currentUser?.id === id) {
      return auth.currentUser.display_name;
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
    auth.resetAccountForm();
  }

  function closeNotice(): void {
    error = '';
    message = '';
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
        <strong>{basketState.activeBasket?.lines.length ?? 0}</strong>
      </button>
      <button
        type="button"
        class="account-button"
        class:logged-out-account={!auth.currentUser}
        aria-label={auth.currentUser ? 'Account' : 'Login'}
        onclick={() => (activeTab = 'account')}
      >
        <span class="account-avatar" aria-hidden="true">
          {auth.currentUser ? auth.currentUser.display_name.slice(0, 1).toUpperCase() : ''}
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
            currentUser={auth.currentUser}
            {busy}
            bind:email={auth.email}
            bind:password={auth.password}
            bind:accountForm={auth.accountForm}
            login={() => void login()}
            logout={() => void logout()}
            saveAccount={() => void saveAccount()}
          />
        {/if}

        {#if activeTab === 'basket'}
          <BasketPanel
            basket={basketState.activeBasket}
            {assets}
            {busy}
            bind:basketTitle={basketState.basketTitle}
            bind:basketNotes={basketState.basketNotes}
            {updateBasket}
            {updateBasketLine}
            {removeBasketLine}
            {confirmBasket}
            {cancelBasket}
            {assetName}
            {locationName}
            {personName}
            {formatDateTime}
          />
        {/if}

        {#if auth.currentUser && activeTab !== 'dashboard' && activeTab !== 'account' && activeTab !== 'basket'}
          {#if activeTab === 'admin' && auth.currentUser.role === 'admin'}
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
              availability={bookingState.availability}
              {busy}
              bind:bookingDraft={bookingState.bookingDraft}
              bind:bookingDraftLineForm={bookingState.bookingDraftLineForm}
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
              currentUser={auth.currentUser}
              {stockLevels}
              {bookings}
              {checkouts}
              {returns}
              {filteredAssets}
              selectedAssetEvents={inventoryState.selectedAssetEvents}
              selectedAssetId={inventoryState.selectedAssetId}
              {qrCodes}
              {busy}
              bind:assetForm={inventoryState.assetForm}
              bind:assetEditForm={inventoryState.assetEditForm}
              bind:assetSearch={inventoryState.assetSearch}
              bind:bookingForm={bookingState.bookingForm}
              bind:bookingDraft={bookingState.bookingDraft}
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
                inventoryState.clearSelection();
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
      <div class="notice-stack">
        <button
          type="button"
          class="notice-close"
          aria-label="Close notification"
          onclick={closeNotice}
        >
          x
        </button>
        {#if error}
          <p class="notice error">{error}</p>
        {/if}
        {#if message}
          <p class="notice success">{message}</p>
        {/if}
      </div>
    </section>
  {/if}
</main>
