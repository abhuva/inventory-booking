export type WorkspaceTab =
  | 'dashboard'
  | 'inventory'
  | 'basket'
  | 'locations'
  | 'persons'
  | 'stock'
  | 'bookings'
  | 'admin';

export type WorkspaceTabDefinition = {
  id: WorkspaceTab;
  label: string;
  description: string;
};
