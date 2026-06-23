import { PUBLIC_API_BASE_URL } from '$env/static/public';

export type UserRole = 'admin' | 'user';
export type AssetType = 'tracked' | 'stock';
export type AssetStatus =
  | 'available'
  | 'reserved'
  | 'checked_out'
  | 'in_transfer'
  | 'maintenance'
  | 'damaged'
  | 'lost'
  | 'retired';
export type AssetCondition = 'unknown' | 'good' | 'worn' | 'damaged' | 'needs_repair';
export type LocationType =
  | 'room'
  | 'storage'
  | 'vehicle'
  | 'project_site'
  | 'external_space'
  | 'person_home'
  | 'repair'
  | 'unknown';
export type BookingStatus = 'reserved' | 'cancelled' | 'checked_out' | 'completed';
export type CheckoutStatus = 'checked_out' | 'partially_returned' | 'returned';

export type User = {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
};

export type UserCreate = {
  email: string;
  display_name: string;
  password: string;
  role: UserRole;
  is_active: boolean;
};

export type UserUpdate = {
  email?: string | null;
  display_name?: string | null;
  password?: string | null;
  role?: UserRole | null;
  is_active?: boolean | null;
};

export type Category = {
  id: string;
  name: string;
  description: string | null;
};

export type Location = {
  id: string;
  name: string;
  type: LocationType;
  address: string | null;
  responsible_user_id: string | null;
  notes: string | null;
  is_active: boolean;
};

export type Asset = {
  id: string;
  name: string;
  asset_type: AssetType;
  category_id: string | null;
  status: AssetStatus;
  condition: AssetCondition;
  unit_name: string | null;
  home_location_id: string | null;
  current_location_id: string | null;
  current_holder_user_id: string | null;
  manufacturer: string | null;
  model: string | null;
  serial_number: string | null;
  asset_tag: string | null;
  replacement_value: string | null;
  description: string | null;
  notes: string | null;
};

export type AssetImage = {
  id: string;
  asset_id: string;
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  created_by_user_id: string | null;
  created_at: string;
};

export type StockLevel = {
  id: string;
  asset_id: string;
  location_id: string | null;
  quantity_total: number;
  quantity_reserved: number;
  quantity_checked_out: number;
};

export type BookingLine = {
  id: string;
  booking_id: string;
  asset_id: string;
  location_id: string | null;
  quantity: number | null;
  notes: string | null;
};

export type Booking = {
  id: string;
  requested_by_user_id: string;
  title: string;
  status: BookingStatus;
  starts_at: string;
  ends_at: string;
  notes: string | null;
  lines?: BookingLine[];
};

export type AvailabilityLine = {
  asset_id: string;
  location_id: string | null;
  requested_quantity: number | null;
  available_quantity: number | null;
  available: boolean;
  reason: string | null;
};

export type Availability = {
  available: boolean;
  lines: AvailabilityLine[];
};

export type CheckoutLine = {
  id: string;
  checkout_id: string;
  asset_id: string;
  location_id: string | null;
  quantity: number | null;
  quantity_returned: number;
  condition_out: AssetCondition;
  notes: string | null;
};

export type Checkout = {
  id: string;
  booking_id: string;
  checked_out_by_user_id: string;
  checked_out_to_user_id: string | null;
  status: CheckoutStatus;
  notes: string | null;
  lines?: CheckoutLine[];
};

export type ReturnLine = {
  id: string;
  return_id: string;
  checkout_line_id: string;
  asset_id: string;
  location_id: string | null;
  quantity: number | null;
  condition_in: AssetCondition;
  notes: string | null;
};

export type ReturnRecord = {
  id: string;
  checkout_id: string;
  returned_by_user_id: string;
  notes: string | null;
  lines?: ReturnLine[];
};

export type ItemEvent = {
  id: string;
  created_at: string;
  asset_id: string;
  event_type: string;
  actor_user_id: string | null;
  from_location_id: string | null;
  to_location_id: string | null;
  notes: string | null;
  details: Record<string, unknown> | null;
};

export type QrCode = {
  id: string;
  token: string;
  asset_id: string | null;
  label: string | null;
  notes: string | null;
};

export type QrResolve = {
  token: string;
  assigned: boolean;
  asset: Pick<
    Asset,
    | 'id'
    | 'name'
    | 'asset_type'
    | 'status'
    | 'condition'
    | 'current_location_id'
    | 'current_holder_user_id'
  > | null;
};

export type CategoryCreate = {
  name: string;
  description?: string | null;
};

export type CategoryUpdate = {
  name?: string | null;
  description?: string | null;
};

export type LocationCreate = {
  name: string;
  type: LocationType;
};

export type AssetCreate = {
  name: string;
  asset_type: AssetType;
  category_id?: string | null;
  unit_name?: string | null;
  current_location_id?: string | null;
};

export type AssetUpdate = {
  name?: string | null;
  category_id?: string | null;
  status?: AssetStatus | null;
  condition?: AssetCondition | null;
  home_location_id?: string | null;
  current_location_id?: string | null;
  current_holder_user_id?: string | null;
  manufacturer?: string | null;
  model?: string | null;
  serial_number?: string | null;
  asset_tag?: string | null;
  replacement_value?: string | null;
  description?: string | null;
  notes?: string | null;
};

export type StockLevelCreate = {
  asset_id: string;
  location_id: string;
  quantity_total: number;
};

export type BookingLineCreate = {
  asset_id: string;
  location_id?: string | null;
  quantity?: number | null;
  notes?: string | null;
};

export type BookingCreate = {
  title: string;
  starts_at: string;
  ends_at: string;
  notes?: string | null;
  lines: BookingLineCreate[];
};

export type CheckoutCreate = {
  booking_id: string;
  checked_out_to_user_id?: string | null;
  condition_out?: AssetCondition;
  notes?: string | null;
};

export type ReturnLineCreate = {
  checkout_line_id: string;
  quantity?: number | null;
  condition_in?: AssetCondition;
  notes?: string | null;
};

export type ReturnCreate = {
  checkout_id: string;
  notes?: string | null;
  lines: ReturnLineCreate[];
};

export type TrackedAssetTransfer = {
  to_location_id?: string | null;
  to_holder_user_id?: string | null;
  notes?: string | null;
};

export type StockTransfer = {
  asset_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  notes?: string | null;
};

export type MaintenanceStart = {
  notes?: string | null;
};

export type MaintenanceComplete = {
  condition?: AssetCondition;
  notes?: string | null;
};

export type AssetStateChange = {
  status: AssetStatus;
  condition?: AssetCondition | null;
  notes?: string | null;
};

export type QrCodeCreate = {
  label?: string | null;
  notes?: string | null;
};

export type QrAssign = {
  asset_id: string;
  notes?: string | null;
};

const csrfCookieName = 'inventory_booking_csrf';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' });
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
