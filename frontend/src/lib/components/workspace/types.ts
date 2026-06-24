export type WorkspaceTab =
  | 'dashboard'
  | 'inventory'
  | 'basket'
  | 'locations'
  | 'persons'
  | 'stock'
  | 'bookings'
  | 'account'
  | 'admin';

export type WorkspaceTabDefinition = {
  id: WorkspaceTab;
  label: string;
  description: string;
};
