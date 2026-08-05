import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  type Category,
  type CategoryCreate,
  type CategoryUpdate,
  type User,
  type UserCreate,
  type UserUpdate
} from '$lib/api';

export const adminApi = {
  listCategories: () => apiGet<Category[]>('/categories'),
  createCategory: (payload: CategoryCreate) => apiPost<Category>('/categories', payload),
  updateCategory: (categoryId: string, payload: CategoryUpdate) =>
    apiPatch<Category>(`/categories/${categoryId}`, payload),
  listUsers: () => apiGet<User[]>('/users'),
  createUser: (payload: UserCreate) => apiPost<User>('/users', payload),
  updateUser: (userId: string, payload: UserUpdate) => apiPatch<User>(`/users/${userId}`, payload),
  deleteUser: (userId: string) => apiDelete<void>(`/users/${userId}`)
};
