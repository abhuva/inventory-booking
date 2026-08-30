<script lang="ts">
  import { onMount } from 'svelte';
  import {
    ApiError,
    apiUrl,
    type Asset,
    type AssetImage,
    type Category,
    type ItemEvent,
    type Location,
    type StockLevel,
    type User
  } from '$lib/api';
  import { adminApi } from '$lib/api/admin';
  import { authApi } from '$lib/api/auth';
  import { inventoryApi } from '$lib/api/inventory';
  import { locationsApi } from '$lib/api/locations';
  import { qrApi } from '$lib/api/qr';
  import LoginForm from '$lib/components/auth/LoginForm.svelte';
  import QrAssetView from '$lib/components/qr/QrAssetView.svelte';
  import QrRouteNotice from '$lib/components/qr/QrRouteNotice.svelte';
  import type { PageData } from './$types';

  type RouteState =
    | 'checking-session'
    | 'login-required'
    | 'authenticating'
    | 'resolving'
    | 'loading-asset'
    | 'ready'
    | 'unassigned'
    | 'not-found'
    | 'error';

  let { data }: { data: PageData } = $props();

  let routeState = $state<RouteState>('checking-session');
  let currentUser = $state<User | null>(null);
  let email = $state('');
  let password = $state('');
  let errorMessage = $state('');
  let asset = $state<Asset | null>(null);
  let assetImage = $state<AssetImage | null>(null);
  let categories = $state<Category[]>([]);
  let locations = $state<Location[]>([]);
  let stockLevels = $state<StockLevel[]>([]);
  let events = $state<ItemEvent[]>([]);
  let clientScanEventId = '';

  const imageUrl = $derived(
    asset && assetImage
      ? apiUrl(
          `/assets/${encodeURIComponent(asset.id)}/image/content?v=${encodeURIComponent(assetImage.created_at)}`
        )
      : null
  );
  const inventoryUrl = $derived(
    asset ? `/?tab=inventory&asset=${encodeURIComponent(asset.id)}` : '/'
  );
  const busy = $derived(
    routeState === 'checking-session' ||
      routeState === 'authenticating' ||
      routeState === 'resolving' ||
      routeState === 'loading-asset'
  );

  onMount(() => {
    document.body.classList.add('qr-route-body');
    clientScanEventId = createClientEventId();
    void checkSession();
    return () => document.body.classList.remove('qr-route-body');
  });

  async function checkSession(): Promise<void> {
    routeState = 'checking-session';
    errorMessage = '';
    try {
      currentUser = await authApi.currentUser();
      await resolveAsset();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        currentUser = null;
        routeState = 'login-required';
        return;
      }
      setError(caught);
    }
  }

  async function login(): Promise<void> {
    routeState = 'authenticating';
    errorMessage = '';
    try {
      currentUser = await authApi.login({ email, password });
      password = '';
      await resolveAsset();
    } catch (caught) {
      currentUser = null;
      routeState = 'login-required';
      errorMessage = caught instanceof Error ? caught.message : 'Could not sign in.';
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout();
      currentUser = null;
      clearAsset();
      routeState = 'login-required';
    } catch (caught) {
      setError(caught);
    }
  }

  async function resolveAsset(): Promise<void> {
    if (!data.token) {
      routeState = 'not-found';
      return;
    }

    routeState = 'resolving';
    errorMessage = '';
    clearAsset();
    try {
      const resolved = await qrApi.resolve(data.token);
      if (!resolved.assigned || !resolved.asset) {
        routeState = 'unassigned';
        return;
      }

      routeState = 'loading-asset';
      const loadedAsset = await inventoryApi.getAsset(resolved.asset.id);
      const [loadedImage, loadedCategories, loadedLocations, loadedStock, loadedEvents] =
        await Promise.all([
          getOptionalAssetImage(loadedAsset.id),
          adminApi.listCategories(),
          locationsApi.listLocations(),
          loadedAsset.asset_type === 'stock' ? inventoryApi.listStockLevels() : Promise.resolve([]),
          inventoryApi.getAssetEvents(loadedAsset.id, 12)
        ]);

      asset = loadedAsset;
      assetImage = loadedImage;
      categories = loadedCategories;
      locations = loadedLocations;
      stockLevels = loadedStock.filter((level) => level.asset_id === loadedAsset.id);
      events = loadedEvents;
      routeState = 'ready';
      void reportScan();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        currentUser = null;
        routeState = 'login-required';
        return;
      }
      if (caught instanceof ApiError && caught.status === 404) {
        routeState = 'not-found';
        return;
      }
      setError(caught);
    }
  }

  async function reportScan(): Promise<void> {
    if (!clientScanEventId || !data.token) {
      return;
    }
    try {
      await qrApi.reportScan(data.token, { client_event_id: clientScanEventId });
    } catch {
      // The asset view remains usable if the optional cross-device notification fails.
    }
  }

  function createClientEventId(): string {
    if (typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }

  async function getOptionalAssetImage(assetId: string): Promise<AssetImage | null> {
    try {
      return await inventoryApi.getAssetImage(assetId);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) {
        return null;
      }
      throw caught;
    }
  }

  function clearAsset(): void {
    asset = null;
    assetImage = null;
    categories = [];
    locations = [];
    stockLevels = [];
    events = [];
  }

  function setError(caught: unknown): void {
    routeState = 'error';
    errorMessage = caught instanceof Error ? caught.message : 'The item could not be loaded.';
  }
</script>

<svelte:head>
  <title>{asset ? `${asset.name} | NICA Inventar` : 'Asset lookup | NICA Inventar'}</title>
  <meta name="description" content="Authenticated inventory asset lookup." />
</svelte:head>

<main class="qr-route-shell">
  <header class="qr-route-header">
    <a href="/" class="qr-brand">NICA e.V. Inventar</a>
    {#if currentUser}
      <div class="qr-account">
        <span>{currentUser.display_name}</span>
        <button type="button" class="secondary" disabled={busy} onclick={() => void logout()}>
          Logout
        </button>
      </div>
    {/if}
  </header>

  <section class="qr-route-content">
    {#if routeState === 'checking-session'}
      <QrRouteNotice title="Checking access" message="Connecting to inventory..." />
    {:else if routeState === 'login-required' || routeState === 'authenticating'}
      <section class="qr-login-panel">
        <p class="eyebrow">Asset lookup</p>
        <h1>Sign in</h1>
        <p>Your account is required before asset details are shown.</p>
        <LoginForm
          bind:email
          bind:password
          busy={routeState === 'authenticating'}
          {errorMessage}
          onLogin={() => void login()}
        />
      </section>
    {:else if routeState === 'resolving'}
      <QrRouteNotice title="Reading label" message="Finding the assigned asset..." />
    {:else if routeState === 'loading-asset'}
      <QrRouteNotice title="Loading asset" message="Preparing the current item record..." />
    {:else if routeState === 'unassigned'}
      <QrRouteNotice
        tone="warning"
        title="Label not assigned"
        message="This QR label exists, but it is not assigned to an asset."
        actionLabel="Check again"
        onAction={() => void resolveAsset()}
      />
    {:else if routeState === 'not-found'}
      <QrRouteNotice
        tone="error"
        title="Label not found"
        message="This QR label is invalid or no longer exists."
        actionLabel="Try again"
        onAction={() => void resolveAsset()}
      />
    {:else if routeState === 'error'}
      <QrRouteNotice
        tone="error"
        title="Could not load asset"
        message={errorMessage}
        actionLabel="Retry"
        onAction={() => void checkSession()}
      />
    {:else if routeState === 'ready' && asset}
      <QrAssetView {asset} {imageUrl} {categories} {locations} {stockLevels} {events} />
      <nav class="qr-route-actions" aria-label="Asset actions">
        <button type="button" class="secondary" onclick={() => void resolveAsset()}>
          Refresh
        </button>
        <a href={inventoryUrl} class="button-link">Open in inventory</a>
      </nav>
    {/if}
  </section>
</main>
