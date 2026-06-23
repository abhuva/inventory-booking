export type WorkspaceTab =
  | 'dashboard'
  | 'inventory'
  | 'basket'
  | 'locations'
  | 'stock'
  | 'bookings'
  | 'field'
  | 'admin';

export type WorkspaceTabDefinition = {
  id: WorkspaceTab;
  label: string;
  description: string;
};
