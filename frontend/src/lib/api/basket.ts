import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  type Basket,
  type BasketCreate,
  type BasketLineUpdate,
  type BasketUpdate,
  type Booking
} from '$lib/api';

export const basketApi = {
  activeBasket: () => apiGet<Basket | null>('/basket/active'),
  createBasket: (payload: BasketCreate) => apiPost<Basket>('/basket', payload),
  updateBasket: (basketId: string, payload: BasketUpdate) =>
    apiPatch<Basket>(`/basket/${basketId}`, payload),
  addLine: (basketId: string, payload: unknown) =>
    apiPost<Basket>(`/basket/${basketId}/lines`, payload),
  updateLine: (basketId: string, lineId: string, payload: BasketLineUpdate) =>
    apiPatch<Basket>(`/basket/${basketId}/lines/${lineId}`, payload),
  removeLine: (basketId: string, lineId: string) =>
    apiDelete<void>(`/basket/${basketId}/lines/${lineId}`),
  confirmBasket: (basketId: string) => apiPost<Booking>(`/basket/${basketId}/confirm`),
  cancelBasket: (basketId: string) => apiPost<Basket>(`/basket/${basketId}/cancel`)
};
