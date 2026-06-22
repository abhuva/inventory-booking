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

export type User = {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
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
  notes: string | null;
};

export type StockLevel = {
  id: string;
  asset_id: string;
  location_id: string;
  quantity_total: number;
  quantity_reserved: number;
  quantity_checked_out: number;
};

export type CategoryCreate = {
  name: string;
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

export type StockLevelCreate = {
  asset_id: string;
  location_id: string;
  quantity_total: number;
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

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined) {
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
