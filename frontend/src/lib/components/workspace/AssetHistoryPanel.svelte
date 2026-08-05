<script lang="ts">
  import type { ItemEvent } from '$lib/api';

  let {
    events,
    formatDateTime,
    userLabel,
    locationName
  }: {
    events: ItemEvent[];
    formatDateTime: (value: string) => string;
    userLabel: (id: string | null) => string;
    locationName: (id: string | null) => string;
  } = $props();
</script>

<div class="detail-tab-panel history-panel">
  <div class="timeline">
    <h3>History</h3>
    {#each events as event}
      <article class="timeline-entry">
        <div>
          <strong>{event.event_type.replaceAll('_', ' ')}</strong>
          <span>{formatDateTime(event.created_at)} - {userLabel(event.actor_user_id)}</span>
        </div>
        <p>
          {#if event.from_location_id || event.to_location_id}
            {locationName(event.from_location_id)} -> {locationName(event.to_location_id)}
          {:else}
            {event.notes ?? 'No notes'}
          {/if}
        </p>
      </article>
    {:else}
      <p class="empty">No history recorded for this asset yet.</p>
    {/each}
  </div>
</div>
