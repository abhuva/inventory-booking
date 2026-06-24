<script lang="ts">
  import type { User } from '$lib/api';

  let {
    currentUser,
    busy,
    email = $bindable(),
    password = $bindable(),
    accountForm = $bindable(),
    login,
    logout,
    saveAccount
  }: {
    currentUser: User | null;
    busy: boolean;
    email: string;
    password: string;
    accountForm: {
      email: string;
      display_name: string;
      password: string;
    };
    login: () => void;
    logout: () => void;
    saveAccount: () => void;
  } = $props();
</script>

<section class="account-workspace" aria-label="Account workspace">
  <section class="panel account-panel">
    <div class="detail-header">
      <div>
        <p class="eyebrow">Account</p>
        <h2>{currentUser ? currentUser.display_name : 'Sign in'}</h2>
      </div>
    </div>

    {#if currentUser}
      <form
        class="asset-edit-form"
        onsubmit={(event) => {
          event.preventDefault();
          saveAccount();
        }}
      >
        <label>
          Name
          <input bind:value={accountForm.display_name} autocomplete="name" required />
        </label>
        <label>
          Email
          <input bind:value={accountForm.email} type="email" autocomplete="email" required />
        </label>
        <label>
          New password
          <input
            bind:value={accountForm.password}
            type="password"
            autocomplete="new-password"
            minlength="8"
            placeholder="Leave empty to keep current password"
          />
        </label>
        <div class="readonly-field">
          <span>Role</span>
          <strong>{currentUser.role}</strong>
        </div>
        <div class="button-row compact-button-row">
          <button type="submit" class="compact" disabled={busy}>Save account</button>
          <button type="button" class="secondary compact" disabled={busy} onclick={logout}>
            Logout
          </button>
        </div>
      </form>
    {:else}
      <form
        class="asset-edit-form"
        onsubmit={(event) => {
          event.preventDefault();
          login();
        }}
      >
        <label>
          Email
          <input bind:value={email} type="email" autocomplete="username" />
        </label>
        <label>
          Password
          <input bind:value={password} type="password" autocomplete="current-password" />
        </label>
        <button type="submit" disabled={busy}>Login</button>
      </form>
    {/if}
  </section>
</section>
