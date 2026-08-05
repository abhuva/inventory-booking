import { apiGet, apiPatch, apiPost, type User, type UserUpdate } from '$lib/api';

export const authApi = {
  currentUser: () => apiGet<User>('/auth/me'),
  login: (credentials: { email: string; password: string }) =>
    apiPost<User>('/auth/login', credentials),
  logout: () => apiPost<void>('/auth/logout'),
  updateCurrentUser: (payload: UserUpdate) => apiPatch<User>('/auth/me', payload)
};
