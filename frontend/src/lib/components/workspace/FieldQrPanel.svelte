<script lang="ts">
  import type { Asset, QrAssign, QrCode, QrCodeCreate, QrResolve } from '$lib/api';

  let {
    qrCodes,
    trackedAssets,
    resolvedQr,
    busy,
    qrCreateForm = $bindable(),
    qrAssignForm = $bindable(),
    qrResolveToken = $bindable(),
    createQrCode,
    assignQrCode,
    resolveQrCode,
    assetName
  }: {
    qrCodes: QrCode[];
    trackedAssets: Asset[];
    resolvedQr: QrResolve | null;
    busy: boolean;
    qrCreateForm: QrCodeCreate;
    qrAssignForm: QrAssign & { token: string };
    qrResolveToken: string;
    createQrCode: () => void;
    assignQrCode: () => void;
    resolveQrCode: () => void;
    assetName: (id: string) => string;
  } = $props();
</script>

<section class="forms-grid" aria-label="QR controls">
  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      createQrCode();
    }}
  >
    <h2>QR label</h2>
    <label>Label <input bind:value={qrCreateForm.label} placeholder="Label 001" /></label>
    <label>Notes <textarea bind:value={qrCreateForm.notes}></textarea></label>
    <button type="submit" disabled={busy}>Create QR label</button>
  </form>

  <form
    class="panel form-panel wide"
    onsubmit={(event) => {
      event.preventDefault();
      assignQrCode();
    }}
  >
    <h2>Assign QR</h2>
    <div class="split-fields">
      <label>
        Token
        <select bind:value={qrAssignForm.token} required>
          <option value="">Choose QR label</option>
          {#each qrCodes as qrCode}
            <option value={qrCode.token}>
              {qrCode.label ?? qrCode.token.slice(0, 10)} · {qrCode.asset_id
                ? assetName(qrCode.asset_id)
                : 'unassigned'}
            </option>
          {/each}
        </select>
      </label>
      <label>
        Tracked asset
        <select bind:value={qrAssignForm.asset_id} required>
          <option value="">Choose tracked asset</option>
          {#each trackedAssets.filter((asset) => asset.status !== 'lost' && asset.status !== 'retired') as asset}
            <option value={asset.id}>{asset.name}</option>
          {/each}
        </select>
      </label>
    </div>
    <label>Notes <textarea bind:value={qrAssignForm.notes}></textarea></label>
    <button type="submit" disabled={busy}>Assign QR label</button>
  </form>

  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      resolveQrCode();
    }}
  >
    <h2>Scan / resolve QR</h2>
    <label>Token <input bind:value={qrResolveToken} required /></label>
    {#if resolvedQr}
      <div class:availability-ok={resolvedQr.assigned} class="availability-result">
        <strong>{resolvedQr.assigned ? resolvedQr.asset?.name : 'Unassigned label'}</strong>
        {#if resolvedQr.asset}
          <span>{resolvedQr.asset.status} · {resolvedQr.asset.condition}</span>
        {/if}
      </div>
    {/if}
    <button type="submit" disabled={busy}>Resolve QR</button>
  </form>
</section>

<section class="data-grid" aria-label="QR lists">
  <article class="panel list-panel">
    <h2>QR labels</h2>
    {#each qrCodes as qrCode}
      <div class="row-card">
        <strong>{qrCode.label ?? qrCode.token.slice(0, 14)}</strong>
        <span>{qrCode.asset_id ? assetName(qrCode.asset_id) : 'unassigned'}</span>
      </div>
    {:else}
      <p class="empty">No QR labels yet.</p>
    {/each}
  </article>
</section>
