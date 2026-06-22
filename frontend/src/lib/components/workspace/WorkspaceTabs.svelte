<script lang="ts">
  import type { WorkspaceTab, WorkspaceTabDefinition } from './types';

  let {
    tabs,
    activeTab,
    onSwitch
  }: {
    tabs: WorkspaceTabDefinition[];
    activeTab: WorkspaceTab;
    onSwitch: (tab: WorkspaceTab) => void;
  } = $props();
</script>

<nav class="tab-bar" aria-label="Workspace sections">
  {#each tabs as tab}
    <button type="button" class:active-tab={activeTab === tab.id} onclick={() => onSwitch(tab.id)}>
      <span>{tab.label}</span>
      <small>{tab.description}</small>
    </button>
  {/each}
</nav>
