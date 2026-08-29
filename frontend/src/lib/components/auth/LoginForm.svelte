<script lang="ts">
  let {
    email = $bindable(),
    password = $bindable(),
    busy,
    errorMessage = '',
    onLogin
  }: {
    email: string;
    password: string;
    busy: boolean;
    errorMessage?: string;
    onLogin: () => void;
  } = $props();
</script>

<form
  class="login-form"
  onsubmit={(event) => {
    event.preventDefault();
    onLogin();
  }}
>
  <label>
    Email
    <input bind:value={email} type="email" autocomplete="username" required />
  </label>
  <label>
    Password
    <input bind:value={password} type="password" autocomplete="current-password" required />
  </label>
  {#if errorMessage}
    <p class="login-error" role="alert">{errorMessage}</p>
  {/if}
  <button type="submit" disabled={busy}>
    {busy ? 'Signing in...' : 'Sign in'}
  </button>
</form>
