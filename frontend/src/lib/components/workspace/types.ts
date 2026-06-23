export type WorkspaceTab =
  | 'dashboard'
  | 'inventory'
  | 'basket'
  | 'locations'
  | 'bookings'
  | 'checkout'
  | 'field'
  | 'admin';

export type WorkspaceTabDefinition = {
  id: WorkspaceTab;
  label: string;
  description: string;
};
