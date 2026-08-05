import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  type Availability,
  type AvailabilityDays,
  type AvailabilityHeatmap,
  type Booking,
  type BookingCreate,
  type BookingUpdate
} from '$lib/api';

export const bookingsApi = {
  previewAvailability: (payload: BookingCreate) =>
    apiPost<Availability>('/bookings/availability', payload),
  listBookings: () => apiGet<Booking[]>('/bookings'),
  getBooking: (bookingId: string) => apiGet<Booking>(`/bookings/${bookingId}`),
  createBooking: (payload: BookingCreate) => apiPost<Booking>('/bookings', payload),
  updateBooking: (bookingId: string, payload: BookingUpdate) =>
    apiPatch<Booking>(`/bookings/${bookingId}`, payload),
  deleteBooking: (bookingId: string) => apiDelete<void>(`/bookings/${bookingId}`),
  availabilityDays: (query: string) =>
    apiGet<AvailabilityDays>(`/bookings/availability/days?${query}`),
  heatmap: (query: string, init?: RequestInit) =>
    apiGet<AvailabilityHeatmap>(`/bookings/availability/heatmap?${query}`, init)
};
