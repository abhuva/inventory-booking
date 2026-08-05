<script lang="ts">
  import AvailabilityDatePicker from './AvailabilityDatePicker.svelte';
  import AssetExtraPanel from './AssetExtraPanel.svelte';
  import AssetHistoryPanel from './AssetHistoryPanel.svelte';
  import AssetInfoPanel from './AssetInfoPanel.svelte';
  import AssetQrPanel from './AssetQrPanel.svelte';
  import AssetStockPanel from './AssetStockPanel.svelte';
  import InventoryAssetTable from './InventoryAssetTable.svelte';
  import TrackedUnitPanel from './TrackedUnitPanel.svelte';
  import { readStoredString, writeStoredValue } from '$lib/persisted';
  import { downloadSvg, renderQrSvg, safeFilename } from '$lib/qr';
  import type {
    Asset,
    AssetCondition,
    AssetCreate,
    AssetStatus,
    AssetUpdate,
    Booking,
    Category,
    Checkout,
    ItemEvent,
    Location,
    Person,
    QrCode,
    ReturnRecord,
    StockLevel,
    StockTransfer,
    TrackedAssetTransfer,
    User
  } from '$lib/api';

  const assetStatuses: AssetStatus[] = [
    'available',
    'reserved',
    'checked_out',
    'in_transfer',
    'maintenance',
    'damaged',
    'lost',
    'retired'
  ];
  const assetConditions: AssetCondition[] = ['unknown', 'good', 'worn', 'damaged', 'needs_repair'];
  type AssetDetailTab = 'info' | 'unit' | 'stock' | 'extra' | 'qr' | 'history';
  type StockAdjustMode = 'add' | 'remove';

  let showAddAsset = $state(false);
  let showMoveAsset = $state(false);
  let showStockAdjust = $state(false);
  let showReserveAsset = $state(false);
  let showDatePicker = $state(false);
  let dateSelectionAccepted = $state(false);
  let activeDetailTab = $state<AssetDetailTab>('info');
  let qrSvg = $state('');
  let qrError = $state('');
  let inventoryLocationFilter = $state(readStoredString('inventory.locationFilter'));
  let moveError = $state('');
  let stockAdjustMode = $state<StockAdjustMode>('add');
  let stockAdjustLocationId = $state('');
  let stockAdjustAmount = $state(1);
  let stockAdjustError = $state('');
  let trackedMoveForm = $state<TrackedAssetTransfer>({
    to_location_id: '',
    to_holder_user_id: null,
    notes: ''
  });
  let stockMoveForm = $state<StockTransfer>({
    asset_id: '',
    from_location_id: '',
    to_location_id: '',
    quantity: 1,
    notes: ''
  });

  let {
    assets,
    categories,
    locations,
    persons,
    users,
    currentUser,
    stockLevels,
    bookings,
    checkouts,
    returns,
    filteredAssets,
    selectedAssetEvents,
    selectedAssetId,
    qrCodes,
    busy,
    assetForm = $bindable(),
    assetEditForm = $bindable(),
    assetSearch = $bindable(),
    bookingForm = $bindable(),
    bookingDraft = $bindable(),
    createAsset,
    updateSelectedAsset,
    deleteSelectedAsset,
    moveSelectedTrackedAsset,
    moveSelectedStock,
    addSelectedStock,
    removeSelectedStock,
    addBookingFormToBasket,
    clearBookingAvailability,
    uploadSelectedAssetImage,
    deleteSelectedAssetImage,
    generateSelectedAssetQr,
    selectAssetDetail,
    closeAssetDetail,
    selectedAsset,
    categoryName,
    locationName,
    holderLabel,
    userLabel,
    assetImageUrl,
    qrCodeForAsset,
    qrScanUrl,
    formatDateTime
  }: {
    assets: Asset[];
    categories: Category[];
    locations: Location[];
    persons: Person[];
    users: User[];
    currentUser: User | null;
    stockLevels: StockLevel[];
    bookings: Booking[];
    checkouts: Checkout[];
    returns: ReturnRecord[];
    filteredAssets: Asset[];
    selectedAssetEvents: ItemEvent[];
    selectedAssetId: string;
    qrCodes: QrCode[];
    busy: boolean;
    assetForm: AssetCreate;
    assetEditForm: AssetUpdate;
    assetSearch: string;
    bookingForm: {
      title: string;
      starts_at: string;
      ends_at: string;
      asset_id: string;
      location_id: string;
      quantity: number;
    };
    bookingDraft: {
      title: string;
      person_id: string;
      starts_at: string;
      ends_at: string;
      notes: string;
      lines: Array<{
        client_id: string;
        asset_id: string;
        location_id?: string | null;
        quantity?: number | null;
        notes?: string | null;
      }>;
    };
    createAsset: () => void;
    updateSelectedAsset: () => void;
    deleteSelectedAsset: () => Promise<boolean>;
    moveSelectedTrackedAsset: (payload: TrackedAssetTransfer) => Promise<boolean>;
    moveSelectedStock: (payload: StockTransfer) => Promise<boolean>;
    addSelectedStock: (locationId: string, quantity: number) => Promise<boolean>;
    removeSelectedStock: (locationId: string, quantity: number) => Promise<boolean>;
    addBookingFormToBasket: () => Promise<boolean>;
    clearBookingAvailability: () => void;
    uploadSelectedAssetImage: (file: File) => void;
    deleteSelectedAssetImage: () => void;
    generateSelectedAssetQr: () => void;
    selectAssetDetail: (assetId: string) => void;
    closeAssetDetail: () => void;
    selectedAsset: () => Asset | undefined;
    categoryName: (id: string | null) => string;
    locationName: (id: string | null) => string;
    holderLabel: (id: string | null) => string;
    userLabel: (id: string | null) => string;
    assetImageUrl: (assetId: string) => string | null;
    qrCodeForAsset: (assetId: string) => QrCode | undefined;
    qrScanUrl: (token: string) => string;
    formatDateTime: (value: string) => string;
  } = $props();

  $effect(() => {
    writeStoredValue('inventory.locationFilter', inventoryLocationFilter);
  });

  function submitNewAsset() {
    createAsset();
    showAddAsset = false;
  }

  function openReserveDialog() {
    const asset = selectedAsset();
    if (!asset) {
      return;
    }
    const start = new Date();
    start.setHours(start.getHours() + 1, 0, 0, 0);
    const end = new Date(start);
    end.setHours(end.getHours() + 2);
    bookingForm = {
      title: `Reserve ${asset.name}`,
      starts_at: toDateTimeLocalValue(start),
      ends_at: toDateTimeLocalValue(end),
      asset_id: asset.id,
      location_id: asset.asset_type === 'stock' ? defaultBookingLocation(asset.id) : '',
      quantity: 1
    };
    if (!bookingDraft.title) {
      bookingDraft.title = `Reserve ${asset.name}`;
    }
    if (!bookingDraft.starts_at) {
      bookingDraft.starts_at = bookingForm.starts_at;
    }
    if (!bookingDraft.ends_at) {
      bookingDraft.ends_at = bookingForm.ends_at;
    }
    clearBookingAvailability();
    dateSelectionAccepted = false;
    showReserveAsset = true;
  }

  async function submitReserve() {
    const added = await addBookingFormToBasket();
    showReserveAsset = !added;
  }

  function acceptBookingDates(startsAt: string, endsAt: string) {
    bookingDraft.starts_at = startsAt;
    bookingDraft.ends_at = endsAt;
    bookingForm.starts_at = startsAt;
    bookingForm.ends_at = endsAt;
    showDatePicker = false;
    dateSelectionAccepted = true;
  }

  function openMoveDialog() {
    const asset = selectedAsset();
    if (!asset) {
      return;
    }
    moveError = '';
    if (asset.asset_type === 'tracked') {
      trackedMoveForm = {
        to_location_id: asset.current_location_id ?? '',
        to_holder_user_id: null,
        notes: ''
      };
    } else {
      stockMoveForm = {
        asset_id: asset.id,
        from_location_id: defaultStockMoveSourceLocation(),
        to_location_id: '',
        quantity: 1,
        notes: ''
      };
    }
    showMoveAsset = true;
  }

  async function submitMove() {
    const asset = selectedAsset();
    if (!asset) {
      return;
    }
    moveError = '';
    if (asset.asset_type === 'tracked') {
      if (!trackedMoveForm.to_location_id) {
        moveError = 'Choose a destination.';
        return;
      }
      const moved = await moveSelectedTrackedAsset(trackedMoveForm);
      showMoveAsset = !moved;
      return;
    }

    const availableQuantity = selectedStockMoveSourceAvailable();
    if (!stockMoveForm.from_location_id) {
      moveError = 'Choose a source location.';
      return;
    }
    if (!stockMoveForm.to_location_id) {
      moveError = 'Choose a destination.';
      return;
    }
    if (stockMoveForm.from_location_id === stockMoveForm.to_location_id) {
      moveError = 'Source and destination must differ.';
      return;
    }
    if (!Number.isFinite(stockMoveForm.quantity) || stockMoveForm.quantity < 1) {
      moveError = 'Quantity must be at least 1.';
      return;
    }
    if (stockMoveForm.quantity > availableQuantity) {
      moveError = `Only ${availableQuantity} available at the source.`;
      return;
    }

    const moved = await moveSelectedStock(stockMoveForm);
    showMoveAsset = !moved;
  }

  function openStockAdjustDialog(mode: StockAdjustMode) {
    stockAdjustMode = mode;
    stockAdjustLocationId = inventoryLocationFilter;
    stockAdjustAmount = 1;
    stockAdjustError = '';
    showStockAdjust = true;
  }

  async function submitStockAdjust() {
    stockAdjustError = '';
    if (!stockAdjustLocationId) {
      stockAdjustError = 'Choose a location first.';
      return;
    }
    if (!Number.isFinite(stockAdjustAmount) || stockAdjustAmount < 1) {
      stockAdjustError = 'Amount must be at least 1.';
      return;
    }
    if (
      stockAdjustMode === 'remove' &&
      stockAdjustAmount > stockAvailableAtLocation(stockAdjustLocationId)
    ) {
      stockAdjustError = `Only ${stockAvailableAtLocation(stockAdjustLocationId)} available at this location.`;
      return;
    }

    const adjusted =
      stockAdjustMode === 'add'
        ? await addSelectedStock(stockAdjustLocationId, stockAdjustAmount)
        : await removeSelectedStock(stockAdjustLocationId, stockAdjustAmount);
    showStockAdjust = !adjusted;
  }

  function availableHolderUsers(): User[] {
    if (!currentUser) {
      return users;
    }
    return users.some((user) => user.id === currentUser.id) ? users : [currentUser, ...users];
  }

  function selectedStockLevels(): StockLevel[] {
    return visibleStockLevelsForAsset(selectedAssetId);
  }

  function selectedStockTotal(): number {
    return selectedStockLevels().reduce((sum, level) => sum + level.quantity_total, 0);
  }

  function selectedStockCheckedOut(): number {
    return selectedStockLevels().reduce((sum, level) => sum + level.quantity_checked_out, 0);
  }

  function displayedAssets(): Asset[] {
    return filteredAssets.filter((asset) => assetMatchesLocation(asset));
  }

  function assetMatchesLocation(asset: Asset): boolean {
    if (!inventoryLocationFilter) {
      return true;
    }
    if (asset.asset_type === 'tracked') {
      return asset.current_location_id === inventoryLocationFilter;
    }
    return stockLevelsForAsset(asset.id).some(
      (level) => level.location_id === inventoryLocationFilter && level.quantity_total > 0
    );
  }

  function stockLevelsForAsset(assetId: string): StockLevel[] {
    return stockLevels.filter((level) => level.asset_id === assetId);
  }

  function bookableStockLevelsForAsset(assetId: string): StockLevel[] {
    return stockLevelsForAsset(assetId).filter(
      (level) => level.location_id !== null && stockLevelAvailable(level) > 0
    );
  }

  function movableStockLevelsForAsset(assetId: string): StockLevel[] {
    return stockLevelsForAsset(assetId).filter(
      (level) => level.location_id !== null && stockLevelAvailable(level) > 0
    );
  }

  function visibleStockLevelsForAsset(assetId: string): StockLevel[] {
    const levels = stockLevelsForAsset(assetId);
    if (!inventoryLocationFilter) {
      return levels;
    }
    return levels.filter((level) => level.location_id === inventoryLocationFilter);
  }

  function stockTotalForAsset(assetId: string): number {
    return visibleStockLevelsForAsset(assetId).reduce(
      (sum, level) => sum + level.quantity_total,
      0
    );
  }

  function stockCheckedOutForAsset(assetId: string): number {
    return visibleStockLevelsForAsset(assetId).reduce(
      (sum, level) => sum + level.quantity_checked_out,
      0
    );
  }

  function stockAvailableForAsset(assetId: string): number {
    return stockTotalForAsset(assetId) - stockCheckedOutForAsset(assetId);
  }

  function stockLevelAvailable(level: StockLevel): number {
    return level.quantity_total - level.quantity_checked_out;
  }

  function defaultStockMoveSourceLocation(): string {
    if (inventoryLocationFilter) {
      return inventoryLocationFilter;
    }
    const movableLevels = movableStockLevelsForAsset(selectedAssetId);
    return movableLevels.length === 1 ? (movableLevels[0].location_id ?? '') : '';
  }

  function selectedStockMoveSourceAvailable(): number {
    const sourceLevel = movableStockLevelsForAsset(selectedAssetId).find(
      (level) => level.location_id === stockMoveForm.from_location_id
    );
    return sourceLevel ? stockLevelAvailable(sourceLevel) : 0;
  }

  function selectedLocationStockLevel(): StockLevel | undefined {
    if (!inventoryLocationFilter) {
      return undefined;
    }
    return stockLevelsForAsset(selectedAssetId).find(
      (level) => level.location_id === inventoryLocationFilter
    );
  }

  function selectedLocationStockAvailable(): number {
    return inventoryLocationFilter ? stockAvailableAtLocation(inventoryLocationFilter) : 0;
  }

  function stockAvailableAtLocation(locationId: string): number {
    const level = stockLevelsForAsset(selectedAssetId).find(
      (entry) => entry.location_id === locationId
    );
    return level ? stockLevelAvailable(level) : 0;
  }

  function defaultBookingLocation(assetId: string): string {
    if (inventoryLocationFilter && stockAvailableAtLocation(inventoryLocationFilter) > 0) {
      return inventoryLocationFilter;
    }
    const levels = bookableStockLevelsForAsset(assetId);
    return levels.length === 1 ? (levels[0].location_id ?? '') : '';
  }

  function showStockMoveSourceSelect(): boolean {
    return !inventoryLocationFilter && movableStockLevelsForAsset(selectedAssetId).length !== 1;
  }

  function assetLocationSummary(asset: Asset): string {
    if (asset.asset_type === 'tracked') {
      return locationName(asset.current_location_id);
    }
    if (inventoryLocationFilter) {
      return locationName(inventoryLocationFilter);
    }
    const levels = stockLevelsForAsset(asset.id).filter((level) => level.quantity_total > 0);
    if (levels.length === 0) {
      return 'No stock location';
    }
    if (levels.length === 1) {
      return locationName(levels[0].location_id);
    }
    return `${levels.length} locations`;
  }

  function assetHolderSummary(asset: Asset): string {
    if (asset.asset_type === 'tracked') {
      return holderLabel(asset.current_holder_user_id);
    }
    const checkedOutQuantity = stockCheckedOutForAsset(asset.id);
    return checkedOutQuantity > 0 ? `${checkedOutQuantity} checked out` : 'Stock item';
  }

  function assetStatusSummary(asset: Asset): string {
    if (asset.asset_type === 'tracked') {
      return asset.status.replaceAll('_', ' ');
    }
    const checkedOutQuantity = stockCheckedOutForAsset(asset.id);
    const availableQuantity = stockAvailableForAsset(asset.id);
    return checkedOutQuantity > 0
      ? `${availableQuantity} available / ${checkedOutQuantity} out`
      : `${availableQuantity} available`;
  }

  function stockDetailScopeLabel(): string {
    return inventoryLocationFilter ? locationName(inventoryLocationFilter) : 'All locations';
  }

  function moveDialogTitle(): string {
    return selectedAsset()?.asset_type === 'stock' ? 'Move stock' : 'Move tracked item';
  }

  function stockAdjustDialogTitle(): string {
    return stockAdjustMode === 'add' ? 'Add stock' : 'Remove stock';
  }

  function canRemoveStock(): boolean {
    if (inventoryLocationFilter) {
      return selectedLocationStockAvailable() > 0;
    }
    return stockAvailableForAsset(selectedAssetId) > 0;
  }

  function selectedAssetQr(): QrCode | undefined {
    return selectedAssetId ? qrCodeForAsset(selectedAssetId) : undefined;
  }

  function downloadSelectedAssetQr(): void {
    const asset = selectedAsset();
    if (!asset || !qrSvg) {
      return;
    }
    downloadSvg(`qr-${safeFilename(asset.name) || 'asset'}.svg`, qrSvg);
  }

  async function confirmDeleteAsset(): Promise<void> {
    const asset = selectedAsset();
    if (!asset) {
      return;
    }
    const bookingLineCount = bookings.reduce(
      (sum, booking) =>
        sum + (booking.lines ?? []).filter((line) => line.asset_id === asset.id).length,
      0
    );
    const checkoutLineCount = checkouts.reduce(
      (sum, checkout) =>
        sum + (checkout.lines ?? []).filter((line) => line.asset_id === asset.id).length,
      0
    );
    const returnLineCount = returns.reduce(
      (sum, returnRecord) =>
        sum + (returnRecord.lines ?? []).filter((line) => line.asset_id === asset.id).length,
      0
    );
    const stockCount = stockLevelsForAsset(asset.id).length;
    const historyCount = selectedAssetEvents.length;
    const qrCount = selectedAssetQr() ? 1 : 0;
    const confirmed = window.confirm(
      [
        `Delete asset "${asset.name}"?`,
        '',
        `${stockCount} stock/location rows, ${qrCount} QR assignment, and current basket references can be removed.`,
        `${bookingLineCount} booking lines, ${checkoutLineCount} checkout lines, ${returnLineCount} return lines, and ${historyCount} history events reference this asset.`,
        'If historical references exist, the backend will refuse deletion to preserve history.',
        '',
        'This cannot be undone.'
      ].join('\n')
    );
    if (confirmed) {
      await deleteSelectedAsset();
    }
  }

  function toDateTimeLocalValue(date: Date): string {
    const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return offsetDate.toISOString().slice(0, 16);
  }

  function bookingDateLabel(): string {
    if (!bookingDraft.starts_at || !bookingDraft.ends_at) {
      return 'Choose dates';
    }
    const start = bookingDraft.starts_at.slice(0, 10);
    const end = inclusiveEndDateLabel(bookingDraft.ends_at);
    return `${start} - ${end}`;
  }

  function inclusiveEndDateLabel(value: string): string {
    const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() - 1);
    return date.toISOString().slice(0, 10);
  }

  $effect(() => {
    const asset = selectedAsset();
    if (!asset) {
      return;
    }
    if (activeDetailTab === 'unit' && asset.asset_type !== 'tracked') {
      activeDetailTab = 'stock';
    }
    if (activeDetailTab === 'stock' && asset.asset_type !== 'stock') {
      activeDetailTab = 'unit';
    }
  });

  $effect(() => {
    const qrCode = selectedAssetQr();
    const renderKey = `${activeDetailTab}:${selectedAssetId}:${qrCode?.token ?? ''}:${qrCodes.length}`;
    void renderKey;
    qrSvg = '';
    qrError = '';
    if (activeDetailTab !== 'qr' || !qrCode) {
      return;
    }
    renderQrSvg(qrScanUrl(qrCode.token))
      .then((svg) => {
        qrSvg = svg;
      })
      .catch((caught: unknown) => {
        qrError = caught instanceof Error ? caught.message : 'Could not render QR code.';
      });
  });
</script>

<section class="inventory-workspace" aria-label="Inventory workspace">
  <InventoryAssetTable
    {assets}
    {locations}
    displayedAssets={displayedAssets()}
    {selectedAssetId}
    bind:assetSearch
    bind:locationFilter={inventoryLocationFilter}
    {assetImageUrl}
    {categoryName}
    {assetStatusSummary}
    {assetLocationSummary}
    {assetHolderSummary}
    onAddAsset={() => (showAddAsset = true)}
    onSelectAsset={selectAssetDetail}
  />

  <aside class="panel inventory-detail-panel" aria-label="Selected asset details">
    {#if selectedAsset()}
      <div class="detail-header asset-detail-header">
        <div>
          <p class="eyebrow">Asset detail</p>
          <h2>{selectedAsset()?.name}</h2>
        </div>
        <div class="button-row compact-button-row">
          <button
            type="button"
            class="danger micro-button"
            onclick={() => void confirmDeleteAsset()}
          >
            Delete
          </button>
          <button type="button" class="secondary micro-button" onclick={closeAssetDetail}>
            Close
          </button>
        </div>
      </div>

      <div class="detail-tab-bar" aria-label="Asset detail sections">
        <button
          type="button"
          class:active-detail-tab={activeDetailTab === 'info'}
          onclick={() => (activeDetailTab = 'info')}
        >
          Info
        </button>
        {#if selectedAsset()?.asset_type === 'tracked'}
          <button
            type="button"
            class:active-detail-tab={activeDetailTab === 'unit'}
            onclick={() => (activeDetailTab = 'unit')}
          >
            Unit
          </button>
        {/if}
        {#if selectedAsset()?.asset_type === 'stock'}
          <button
            type="button"
            class:active-detail-tab={activeDetailTab === 'stock'}
            onclick={() => (activeDetailTab = 'stock')}
          >
            Stock
          </button>
        {/if}
        <button
          type="button"
          class:active-detail-tab={activeDetailTab === 'extra'}
          onclick={() => (activeDetailTab = 'extra')}
        >
          Extra
        </button>
        <button
          type="button"
          class:active-detail-tab={activeDetailTab === 'qr'}
          onclick={() => (activeDetailTab = 'qr')}
        >
          QR
        </button>
        <button
          type="button"
          class:active-detail-tab={activeDetailTab === 'history'}
          onclick={() => (activeDetailTab = 'history')}
        >
          History
        </button>
      </div>

      {#if activeDetailTab === 'info'}
        {@const infoAsset = selectedAsset()}
        {#if infoAsset}
          <AssetInfoPanel
            asset={infoAsset}
            bind:assetEditForm
            {categories}
            imageUrl={assetImageUrl(selectedAssetId)}
            {busy}
            onUpdate={updateSelectedAsset}
            onMove={openMoveDialog}
            onReserve={openReserveDialog}
            onUploadImage={uploadSelectedAssetImage}
            onDeleteImage={deleteSelectedAssetImage}
          />
        {/if}
      {/if}
      {#if activeDetailTab === 'unit' && selectedAsset()?.asset_type === 'tracked'}
        {@const trackedAsset = selectedAsset()}
        {#if trackedAsset}
          <TrackedUnitPanel
            asset={trackedAsset}
            bind:assetEditForm
            {assetStatuses}
            {assetConditions}
            {locations}
            availableHolderUsers={availableHolderUsers()}
            {busy}
            {locationName}
            {holderLabel}
            onUpdate={updateSelectedAsset}
          />
        {/if}
      {/if}

      {#if activeDetailTab === 'stock' && selectedAsset()?.asset_type === 'stock'}
        <AssetStockPanel
          {busy}
          canRemoveStock={canRemoveStock()}
          locationFilter={inventoryLocationFilter}
          scopeLabel={stockDetailScopeLabel()}
          stockLevels={selectedStockLevels()}
          total={selectedStockTotal()}
          checkedOut={selectedStockCheckedOut()}
          unitName={selectedAsset()?.unit_name ?? 'units'}
          {locationName}
          onAddStock={() => openStockAdjustDialog('add')}
          onRemoveStock={() => openStockAdjustDialog('remove')}
        />
      {/if}

      {#if activeDetailTab === 'extra'}
        {@const extraAsset = selectedAsset()}
        {#if extraAsset}
          <AssetExtraPanel
            asset={extraAsset}
            bind:assetEditForm
            {busy}
            onUpdate={updateSelectedAsset}
          />
        {/if}
      {/if}
      {#if activeDetailTab === 'qr'}
        <AssetQrPanel
          assetName={selectedAsset()?.name ?? ''}
          qrCode={selectedAssetQr()}
          {qrSvg}
          {qrError}
          {busy}
          onGenerateQr={generateSelectedAssetQr}
          onDownloadQr={downloadSelectedAssetQr}
        />
      {/if}

      {#if activeDetailTab === 'history'}
        <AssetHistoryPanel
          events={selectedAssetEvents}
          {formatDateTime}
          {userLabel}
          {locationName}
        />
      {/if}
    {:else}
      <div class="empty-detail">
        <h2>Select an asset</h2>
        <p>Click a row in the table to view and edit details.</p>
      </div>
    {/if}
  </aside>
</section>

{#if showReserveAsset && selectedAsset()}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label="Reserve asset"
      onsubmit={(event) => {
        event.preventDefault();
        void submitReserve();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">{selectedAsset()?.name}</p>
          <h2>Add to basket</h2>
        </div>
        <button type="button" class="secondary compact" onclick={() => (showReserveAsset = false)}
          >Cancel</button
        >
      </div>

      <label>Basket name <input bind:value={bookingDraft.title} required /></label>
      <label>
        Person
        <select bind:value={bookingDraft.person_id} required>
          <option value="">Choose person</option>
          {#each persons as person}
            <option value={person.id}>{person.display_name} / {person.person_type}</option>
          {/each}
        </select>
      </label>
      <div class="date-pick-row">
        <div class="readonly-field">
          <span>Dates</span>
          <strong>{bookingDateLabel()}</strong>
        </div>
        <button
          type="button"
          class="secondary compact"
          disabled={selectedAsset()?.asset_type === 'stock' && !bookingForm.location_id}
          onclick={() => (showDatePicker = true)}
        >
          Choose dates
        </button>
      </div>

      {#if selectedAsset()?.asset_type === 'stock'}
        <div class="split-fields">
          <label>
            Location
            <select
              bind:value={bookingForm.location_id}
              required
              onchange={() => {
                dateSelectionAccepted = false;
                showDatePicker = false;
              }}
            >
              <option value="">Choose location</option>
              {#each bookableStockLevelsForAsset(selectedAssetId) as level}
                <option value={level.location_id ?? ''}>
                  {locationName(level.location_id)} ({stockLevelAvailable(level)} available)
                </option>
              {/each}
            </select>
          </label>
          <label>
            Quantity
            <input
              bind:value={bookingForm.quantity}
              type="number"
              min="1"
              required
              onchange={() => {
                dateSelectionAccepted = false;
                showDatePicker = false;
              }}
            />
          </label>
        </div>
      {:else}
        <div class="readonly-field">
          <span>Item</span>
          <strong>Exact tracked item</strong>
        </div>
      {/if}

      {#if showDatePicker && selectedAsset()}
        <AvailabilityDatePicker
          assetId={selectedAssetId}
          locationId={selectedAsset()?.asset_type === 'stock' ? bookingForm.location_id : null}
          quantity={selectedAsset()?.asset_type === 'stock' ? bookingForm.quantity : 1}
          initialStart={bookingDraft.starts_at}
          initialEnd={bookingDraft.ends_at}
          assetLabel={selectedAsset()?.name ?? 'Asset'}
          onAccept={acceptBookingDates}
          onCancel={() => (showDatePicker = false)}
        />
      {/if}

      <div class="button-row">
        <button type="button" class="secondary" onclick={() => (showReserveAsset = false)}
          >Cancel</button
        >
        <button type="submit" disabled={busy || !dateSelectionAccepted || !bookingDraft.person_id}
          >Add to basket</button
        >
      </div>
    </form>
  </div>
{/if}

{#if showStockAdjust && selectedAsset()}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label={stockAdjustDialogTitle()}
      onsubmit={(event) => {
        event.preventDefault();
        void submitStockAdjust();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">
            {selectedAsset()?.name}
            {#if stockAdjustLocationId}
              / {locationName(stockAdjustLocationId)}
            {/if}
          </p>
          <h2>{stockAdjustDialogTitle()}</h2>
        </div>
        <button
          type="button"
          class="secondary compact"
          onclick={() => {
            showStockAdjust = false;
            stockAdjustError = '';
          }}
        >
          Cancel
        </button>
      </div>

      {#if stockAdjustError}
        <p class="notice error">{stockAdjustError}</p>
      {/if}

      {#if inventoryLocationFilter}
        <div class="readonly-field">
          <span>Location</span>
          <strong>{locationName(stockAdjustLocationId)}</strong>
        </div>
      {:else}
        <label>
          Location
          <select bind:value={stockAdjustLocationId} required>
            <option value="">Choose location</option>
            {#each locations as location}
              <option value={location.id}>{location.name}</option>
            {/each}
          </select>
        </label>
      {/if}

      {#if stockAdjustLocationId}
        <div class="readonly-field">
          <span>Current available</span>
          <strong
            >{stockAvailableAtLocation(stockAdjustLocationId)}
            {selectedAsset()?.unit_name ?? 'units'}</strong
          >
        </div>
      {/if}

      <label>
        Amount
        <input
          bind:value={stockAdjustAmount}
          type="number"
          min="1"
          max={stockAdjustMode === 'remove'
            ? stockAvailableAtLocation(stockAdjustLocationId) || undefined
            : undefined}
          required
        />
      </label>

      <div class="button-row">
        <button
          type="button"
          class="secondary"
          onclick={() => {
            showStockAdjust = false;
            stockAdjustError = '';
          }}
        >
          Cancel
        </button>
        <button type="submit" disabled={busy}>
          {stockAdjustMode === 'add' ? 'Add' : 'Remove'}
        </button>
      </div>
    </form>
  </div>
{/if}

{#if showMoveAsset && selectedAsset()}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label={moveDialogTitle()}
      onsubmit={(event) => {
        event.preventDefault();
        void submitMove();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">{selectedAsset()?.name}</p>
          <h2>{moveDialogTitle()}</h2>
        </div>
        <button
          type="button"
          class="secondary compact"
          onclick={() => {
            showMoveAsset = false;
            moveError = '';
          }}
        >
          Cancel
        </button>
      </div>

      {#if moveError}
        <p class="notice error">{moveError}</p>
      {/if}

      {#if selectedAsset()?.asset_type === 'stock'}
        {#if showStockMoveSourceSelect()}
          <label>
            Source
            <select bind:value={stockMoveForm.from_location_id} required>
              <option value="">Choose source</option>
              {#each movableStockLevelsForAsset(selectedAssetId) as level}
                <option value={level.location_id ?? ''}>
                  {locationName(level.location_id)} ({stockLevelAvailable(level)} available)
                </option>
              {/each}
            </select>
          </label>
        {:else}
          <div class="readonly-field">
            <span>Source</span>
            <strong>{locationName(stockMoveForm.from_location_id)}</strong>
            <small>{selectedStockMoveSourceAvailable()} available</small>
          </div>
        {/if}

        <div class="split-fields">
          <label>
            Destination
            <select bind:value={stockMoveForm.to_location_id} required>
              <option value="">Choose destination</option>
              {#each locations as location}
                <option value={location.id}>{location.name}</option>
              {/each}
            </select>
          </label>
          <label>
            Amount
            <input
              bind:value={stockMoveForm.quantity}
              type="number"
              min="1"
              max={selectedStockMoveSourceAvailable() || undefined}
              required
            />
          </label>
        </div>
        <label>Notes <textarea bind:value={stockMoveForm.notes}></textarea></label>
      {:else}
        <label>
          Destination
          <select bind:value={trackedMoveForm.to_location_id} required>
            <option value="">Choose destination</option>
            {#each locations as location}
              <option value={location.id}>{location.name}</option>
            {/each}
          </select>
        </label>
        <label>Notes <textarea bind:value={trackedMoveForm.notes}></textarea></label>
      {/if}

      <div class="button-row">
        <button
          type="button"
          class="secondary"
          onclick={() => {
            showMoveAsset = false;
            moveError = '';
          }}
        >
          Cancel
        </button>
        <button type="submit" disabled={busy}>
          {selectedAsset()?.asset_type === 'stock' ? 'Move' : 'Move tracked item'}
        </button>
      </div>
    </form>
  </div>
{/if}

{#if showAddAsset}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label="Add asset"
      onsubmit={(event) => {
        event.preventDefault();
        submitNewAsset();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">New asset</p>
          <h2>Add asset</h2>
        </div>
        <button type="button" class="secondary compact" onclick={() => (showAddAsset = false)}
          >Cancel</button
        >
      </div>
      <label>Name <input bind:value={assetForm.name} required /></label>
      <div class="split-fields">
        <label>
          Mode
          <select bind:value={assetForm.asset_type}>
            <option value="tracked">tracked exact item</option>
            <option value="stock">stock quantity</option>
          </select>
        </label>
        <label>
          Category
          <select bind:value={assetForm.category_id}>
            <option value={null}>No category</option>
            {#each categories as category}
              <option value={category.id}>{category.name}</option>
            {/each}
          </select>
        </label>
      </div>
      <label>
        Current location
        <select bind:value={assetForm.current_location_id}>
          <option value={null}>No location</option>
          {#each locations as location}
            <option value={location.id}>{location.name}</option>
          {/each}
        </select>
      </label>
      {#if assetForm.asset_type === 'stock'}
        <label
          >Unit name <input
            bind:value={assetForm.unit_name}
            placeholder="piece, set, box"
            required
          /></label
        >
      {/if}
      <div class="button-row">
        <button type="button" class="secondary" onclick={() => (showAddAsset = false)}
          >Cancel</button
        >
        <button type="submit" disabled={busy}>Save asset</button>
      </div>
    </form>
  </div>
{/if}
