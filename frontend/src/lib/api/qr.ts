import {
  apiGet,
  apiPost,
  type QrResolve,
  type QrScanEvent,
  type QrScanEventCreate,
  type QrScanEventList
} from '$lib/api';

export const qrApi = {
  resolve: (token: string) => apiGet<QrResolve>(`/qr-codes/${encodeURIComponent(token)}/resolve`),
  reportScan: (token: string, payload: QrScanEventCreate) =>
    apiPost<QrScanEvent>(`/qr-codes/${encodeURIComponent(token)}/scan-events`, payload),
  listScanEvents: (after?: string) =>
    apiGet<QrScanEventList>(
      after ? `/qr-codes/scan-events?after=${encodeURIComponent(after)}` : '/qr-codes/scan-events'
    )
};
