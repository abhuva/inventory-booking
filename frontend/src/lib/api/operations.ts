import {
  apiGet,
  apiPost,
  type Checkout,
  type CheckoutCreate,
  type ReturnCreate,
  type ReturnRecord
} from '$lib/api';

export const operationsApi = {
  listCheckouts: () => apiGet<Checkout[]>('/checkouts'),
  getCheckout: (checkoutId: string) => apiGet<Checkout>(`/checkouts/${checkoutId}`),
  createCheckout: (payload: CheckoutCreate) => apiPost<Checkout>('/checkouts', payload),
  listReturns: () => apiGet<ReturnRecord[]>('/returns'),
  createReturn: (payload: ReturnCreate) => apiPost<ReturnRecord>('/returns', payload)
};
