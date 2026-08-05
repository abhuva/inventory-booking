import type { User } from '$lib/api';

export type AccountFormState = {
  email: string;
  display_name: string;
  password: string;
};

export function createAuthState() {
  let currentUser = $state<User | null>(null);
  let email = $state('');
  let password = $state('');
  let accountForm = $state<AccountFormState>({
    email: '',
    display_name: '',
    password: ''
  });

  return {
    get currentUser() {
      return currentUser;
    },
    set currentUser(value: User | null) {
      currentUser = value;
    },
    get email() {
      return email;
    },
    set email(value: string) {
      email = value;
    },
    get password() {
      return password;
    },
    set password(value: string) {
      password = value;
    },
    get accountForm() {
      return accountForm;
    },
    set accountForm(value: AccountFormState) {
      accountForm = value;
    },
    resetAccountForm() {
      accountForm = {
        email: currentUser?.email ?? '',
        display_name: currentUser?.display_name ?? '',
        password: ''
      };
    }
  };
}
