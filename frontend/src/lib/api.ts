import { PUBLIC_API_BASE_URL } from '$env/static/public';
import type { components } from '$lib/api/generated';

type Schema = components['schemas'];

export type UserRole = Schema['UserRole'];
export type PersonType = Schema['PersonType'];
export type AssetType = Schema['AssetType'];
export type AssetStatus = Schema['AssetStatus'];
export type AssetCondition = Schema['AssetCondition'];
export type LocationType = Schema['LocationType'];
export type BookingStatus = Schema['BookingStatus'];
export type BasketStatus = Schema['BasketStatus'];
export type CheckoutStatus = Schema['CheckoutStatus'];

export type User = Schema['UserRead'];
export type UserCreate = Schema['UserCreate'];
export type UserUpdate = Schema['UserUpdate'];
export type Person = Schema['PersonRead'];
export type PersonCreate = Schema['PersonCreate'];
export type PersonUpdate = Schema['PersonUpdate'];
export type Category = Schema['CategoryRead'];
export type CategoryCreate = Schema['CategoryCreate'];
export type CategoryUpdate = Schema['CategoryUpdate'];
export type Location = Schema['LocationRead'];
export type LocationCreate = Schema['LocationCreate'];
export type LocationUpdate = Schema['LocationUpdate'];
export type LocationImage = Schema['LocationImageRead'];
export type Asset = Schema['AssetRead'];
export type AssetCreate = Schema['AssetCreate'];
export type AssetUpdate = Schema['AssetUpdate'];
export type AssetImage = Schema['AssetImageRead'];
export type InventoryValueSummary = Schema['InventoryValueSummaryRead'];
export type StockLevel = Schema['StockLevelRead'];
export type StockLevelCreate = Schema['StockLevelCreate'];
export type BookingLine = Schema['BookingLineRead'];
export type Booking = Schema['BookingRead'];
export type BookingLineCreate = Schema['BookingLineCreate'];
export type BookingCreate = Schema['BookingCreate'];
export type BookingUpdate = Schema['BookingUpdate'];
export type BasketLine = Schema['BasketLineRead'];
export type Basket = Schema['BasketRead'];
export type BasketCreate = Schema['BasketCreate'];
export type BasketUpdate = Schema['BasketUpdate'];
export type BasketLineUpdate = Schema['BasketLineUpdate'];
export type AvailabilityLine = Schema['AvailabilityLineRead'];
export type Availability = Schema['AvailabilityRead'];
export type AvailabilityDay = Schema['AvailabilityDayRead'];
export type AvailabilityDays = Schema['AvailabilityDaysRead'];
export type HeatmapCell = Schema['HeatmapCellRead'];
export type HeatmapItem = Schema['HeatmapItemRead'];
export type AvailabilityHeatmap = Schema['AvailabilityHeatmapRead'];
export type CheckoutLine = Schema['CheckoutLineRead'];
export type Checkout = Schema['CheckoutRead'];
export type CheckoutCreate = Schema['CheckoutCreate'];
export type ReturnLine = Schema['ReturnLineRead'];
export type ReturnRecord = Schema['ReturnRead'];
export type ReturnLineCreate = Schema['ReturnLineCreate'];
export type ReturnCreate = Schema['ReturnCreate'];
export type ItemEvent = Schema['ItemEventRead'];
export type QrCode = Schema['QrCodeRead'];
export type QrResolve = Schema['QrResolveRead'];
export type QrCodeCreate = Schema['QrCodeCreate'];
export type QrAssign = Schema['QrAssign'];
export type QrScanEvent = Schema['QrScanEventRead'];
export type QrScanEventCreate = Schema['QrScanEventCreate'];
export type QrScanEventList = Schema['QrScanEventListRead'];
export type TrackedAssetTransfer = Schema['TrackedAssetTransfer'];
export type StockTransfer = Schema['StockTransfer'];
export type MaintenanceStart = Schema['MaintenanceStart'];
export type MaintenanceComplete = Schema['MaintenanceComplete'];
export type AssetStateChange = Schema['AssetStateChange'];
const csrfCookieName = 'inventory_booking_csrf';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

export async function apiGet<T>(path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(path, { ...init, method: 'GET' });
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
}

export async function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' });
}

export async function apiUpload<T>(path: string, body: FormData): Promise<T> {
  return request<T>(path, { method: 'POST', body });
}

export function apiUrl(path: string): string {
  return `${PUBLIC_API_BASE_URL}${path}`;
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (init.method && !['GET', 'HEAD', 'OPTIONS'].includes(init.method)) {
    const csrfToken = readCookie(csrfCookieName);
    if (csrfToken) {
      headers.set('X-CSRF-Token', csrfToken);
    }
  }

  const response = await fetch(`${PUBLIC_API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include'
  });

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === 'string') {
      return payload.detail;
    }
    return JSON.stringify(payload.detail ?? payload);
  } catch {
    return response.statusText;
  }
}

function readCookie(name: string): string | null {
  const cookie = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(`${encodeURIComponent(name)}=`));
  if (!cookie) {
    return null;
  }
  return decodeURIComponent(cookie.split('=').slice(1).join('='));
}
