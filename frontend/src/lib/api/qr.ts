import { apiGet, type QrResolve } from '$lib/api';

export const qrApi = {
  resolve: (token: string) => apiGet<QrResolve>(`/qr-codes/${encodeURIComponent(token)}/resolve`)
};
