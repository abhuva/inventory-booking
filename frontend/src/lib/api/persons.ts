import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  type Person,
  type PersonCreate,
  type PersonUpdate
} from '$lib/api';

export const personsApi = {
  listPersons: () => apiGet<Person[]>('/persons'),
  createPerson: (payload: PersonCreate) => apiPost<Person>('/persons', payload),
  updatePerson: (personId: string, payload: PersonUpdate) =>
    apiPatch<Person>(`/persons/${personId}`, payload),
  deletePerson: (personId: string) => apiDelete<void>(`/persons/${personId}`)
};
