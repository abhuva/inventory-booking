import type {
  Asset,
  AssetCreate,
  AssetUpdate,
  ItemEvent,
  StockLevelCreate,
  StockTransfer,
  TrackedAssetTransfer
} from '$lib/api';

export type AssetStateFormState = {
  asset_id: string;
  action: 'maintenance_start' | 'maintenance_complete' | 'state_change';
  status: string;
  condition: string;
  notes: string;
};

export function createInventoryState() {
  let assetSearch = $state('');
  let selectedAssetId = $state('');
  let selectedAssetEvents = $state<ItemEvent[]>([]);
  let assetForm = $state<AssetCreate>(emptyAssetForm());
  let stockForm = $state<StockLevelCreate>(emptyStockForm());
  let trackedTransferForm = $state<TrackedAssetTransfer & { asset_id: string }>(
    emptyTrackedTransferForm()
  );
  let stockTransferForm = $state<StockTransfer>(emptyStockTransferForm());
  let assetStateForm = $state<AssetStateFormState>(emptyAssetStateForm());
  let assetEditForm = $state<AssetUpdate>(emptyAssetEditForm());

  return {
    get assetSearch() {
      return assetSearch;
    },
    set assetSearch(value: string) {
      assetSearch = value;
    },
    get selectedAssetId() {
      return selectedAssetId;
    },
    set selectedAssetId(value: string) {
      selectedAssetId = value;
    },
    get selectedAssetEvents() {
      return selectedAssetEvents;
    },
    set selectedAssetEvents(value: ItemEvent[]) {
      selectedAssetEvents = value;
    },
    get assetForm() {
      return assetForm;
    },
    set assetForm(value: AssetCreate) {
      assetForm = value;
    },
    get stockForm() {
      return stockForm;
    },
    set stockForm(value: StockLevelCreate) {
      stockForm = value;
    },
    get trackedTransferForm() {
      return trackedTransferForm;
    },
    set trackedTransferForm(value: TrackedAssetTransfer & { asset_id: string }) {
      trackedTransferForm = value;
    },
    get stockTransferForm() {
      return stockTransferForm;
    },
    set stockTransferForm(value: StockTransfer) {
      stockTransferForm = value;
    },
    get assetStateForm() {
      return assetStateForm;
    },
    set assetStateForm(value: AssetStateFormState) {
      assetStateForm = value;
    },
    get assetEditForm() {
      return assetEditForm;
    },
    set assetEditForm(value: AssetUpdate) {
      assetEditForm = value;
    },
    clearSelection() {
      selectedAssetId = '';
      selectedAssetEvents = [];
      assetEditForm = emptyAssetEditForm();
    },
    resetAssetForm() {
      assetForm = emptyAssetForm();
    },
    resetStockForm() {
      stockForm = emptyStockForm();
    },
    resetTrackedTransferForm() {
      trackedTransferForm = emptyTrackedTransferForm();
    },
    resetStockTransferForm() {
      stockTransferForm = emptyStockTransferForm();
    },
    resetAssetStateForm() {
      assetStateForm = emptyAssetStateForm();
    },
    resetAssetEditForm() {
      assetEditForm = emptyAssetEditForm();
    },
    syncAssetEditForm(asset: Asset | undefined) {
      if (!asset) {
        assetEditForm = emptyAssetEditForm();
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
        rental_recoup_days: asset.rental_recoup_days,
        rental_maintenance_cost_per_day: asset.rental_maintenance_cost_per_day,
        rental_profit_margin_percent: asset.rental_profit_margin_percent,
        description: asset.description ?? '',
        notes: asset.notes ?? ''
      };
    }
  };
}

function emptyAssetForm(): AssetCreate {
  return {
    name: '',
    asset_type: 'tracked',
    category_id: null,
    condition: 'unknown',
    status: 'available',
    unit_name: null,
    current_location_id: null
  };
}

function emptyStockForm(): StockLevelCreate {
  return {
    asset_id: '',
    location_id: '',
    quantity_checked_out: 0,
    quantity_reserved: 0,
    quantity_total: 0
  };
}

function emptyTrackedTransferForm(): TrackedAssetTransfer & { asset_id: string } {
  return {
    asset_id: '',
    to_location_id: '',
    to_holder_user_id: null,
    notes: ''
  };
}

function emptyStockTransferForm(): StockTransfer {
  return {
    asset_id: '',
    from_location_id: '',
    to_location_id: '',
    quantity: 1,
    notes: ''
  };
}

function emptyAssetStateForm(): AssetStateFormState {
  return {
    asset_id: '',
    action: 'maintenance_start',
    status: 'damaged',
    condition: 'unknown',
    notes: ''
  };
}

function emptyAssetEditForm(): AssetUpdate {
  return {
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
    rental_recoup_days: null,
    rental_maintenance_cost_per_day: null,
    rental_profit_margin_percent: null,
    description: '',
    notes: ''
  };
}
