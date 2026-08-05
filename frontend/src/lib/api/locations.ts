import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  apiUpload,
  type Location,
  type LocationCreate,
  type LocationImage,
  type LocationUpdate
} from '$lib/api';

export const locationsApi = {
  listLocations: () => apiGet<Location[]>('/locations'),
  createLocation: (payload: LocationCreate) => apiPost<Location>('/locations', payload),
  updateLocation: (locationId: string, payload: LocationUpdate) =>
    apiPatch<Location>(`/locations/${locationId}`, payload),
  deleteLocation: (locationId: string) => apiDelete<void>(`/locations/${locationId}`),
  listLocationImages: () => apiGet<LocationImage[]>('/locations/images'),
  uploadLocationImage: (locationId: string, payload: FormData) =>
    apiUpload<LocationImage>(`/locations/${locationId}/image`, payload),
  deleteLocationImage: (locationId: string) => apiDelete<void>(`/locations/${locationId}/image`)
};
