import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  apiUpload,
  type Asset,
  type AssetCreate,
  type AssetImage,
  type AssetStateChange,
  type AssetUpdate,
  type ItemEvent,
  type InventoryValueSummary,
  type MaintenanceComplete,
  type MaintenanceStart,
  type QrCode,
  type StockLevel,
  type StockLevelCreate,
  type StockTransfer,
  type TrackedAssetTransfer
} from '$lib/api';

export const inventoryApi = {
  listAssets: () => apiGet<Asset[]>('/assets'),
  getValueSummary: () => apiGet<InventoryValueSummary>('/assets/value-summary'),
  getAsset: (assetId: string) => apiGet<Asset>(`/assets/${assetId}`),
  createAsset: (payload: AssetCreate) => apiPost<Asset>('/assets', payload),
  updateAsset: (assetId: string, payload: AssetUpdate) =>
    apiPatch<Asset>(`/assets/${assetId}`, payload),
  deleteAsset: (assetId: string) => apiDelete<void>(`/assets/${assetId}`),
  getAssetImage: (assetId: string) => apiGet<AssetImage>(`/assets/${assetId}/image`),
  listAssetImages: () => apiGet<AssetImage[]>('/assets/images'),
  uploadAssetImage: (assetId: string, payload: FormData) =>
    apiUpload<AssetImage>(`/assets/${assetId}/image`, payload),
  deleteAssetImage: (assetId: string) => apiDelete<void>(`/assets/${assetId}/image`),
  generateAssetQr: (assetId: string) => apiPost<QrCode>(`/assets/${assetId}/qr`),
  listQrCodes: () => apiGet<QrCode[]>('/qr-codes'),
  getAssetEvents: (assetId: string, limit = 50) =>
    apiGet<ItemEvent[]>(
      `/audit/item-events?asset_id=${encodeURIComponent(assetId)}&limit=${limit}`
    ),
  listStockLevels: () => apiGet<StockLevel[]>('/stock-levels'),
  createStockLevel: (payload: StockLevelCreate) => apiPost<StockLevel>('/stock-levels', payload),
  updateStockLevel: (stockLevelId: string, payload: Partial<StockLevelCreate>) =>
    apiPatch<StockLevel>(`/stock-levels/${stockLevelId}`, payload),
  transferTrackedAsset: (assetId: string, payload: TrackedAssetTransfer) =>
    apiPost<Asset>(`/assets/${assetId}/transfer`, payload),
  transferStock: (payload: StockTransfer) =>
    apiPost<StockLevel[]>('/stock-levels/transfer', payload),
  startMaintenance: (assetId: string, payload: MaintenanceStart) =>
    apiPost<Asset>(`/assets/${assetId}/maintenance/start`, payload),
  completeMaintenance: (assetId: string, payload: MaintenanceComplete) =>
    apiPost<Asset>(`/assets/${assetId}/maintenance/complete`, payload),
  changeAssetState: (assetId: string, payload: AssetStateChange) =>
    apiPost<Asset>(`/assets/${assetId}/state`, payload)
};
