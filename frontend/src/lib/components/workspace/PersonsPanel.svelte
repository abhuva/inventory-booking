<script lang="ts">
  import type {
    Booking,
    Location,
    Person,
    PersonCreate,
    PersonType,
    PersonUpdate,
    User
  } from '$lib/api';

  let showAddPerson = $state(false);

  let {
    persons,
    bookings,
    locations,
    users,
    selectedPersonId,
    busy,
    personForm = $bindable(),
    personEditForm = $bindable(),
    createPerson,
    updateSelectedPerson,
    deleteSelectedPerson,
    selectPersonDetail,
    closePersonDetail,
    selectedPerson,
    userLabel
  }: {
    persons: Person[];
    bookings: Booking[];
    locations: Location[];
    users: User[];
    selectedPersonId: string;
    busy: boolean;
    personForm: PersonCreate;
    personEditForm: PersonUpdate;
    createPerson: () => void;
    updateSelectedPerson: () => void;
    deleteSelectedPerson: () => Promise<boolean>;
    selectPersonDetail: (personId: string) => void;
    closePersonDetail: () => void;
    selectedPerson: () => Person | undefined;
    userLabel: (id: string | null) => string;
  } = $props();

  const personTypes: PersonType[] = ['admin', 'user', 'team', 'external'];

  function submitNewPerson(): void {
    createPerson();
    showAddPerson = false;
  }

  function personTypeLabel(type: PersonType | null | undefined): string {
    return type ? type.replaceAll('_', ' ') : 'user';
  }

  async function confirmDeletePerson(): Promise<void> {
    const person = selectedPerson();
    if (!person) {
      return;
    }
    const bookingCount = bookings.filter((booking) => booking.person_id === person.id).length;
    const locationCount = locations.filter(
      (location) => location.responsible_person_id === person.id
    ).length;
    const confirmed = window.confirm(
      [
        `Delete person "${person.display_name}"?`,
        '',
        `${bookingCount} bookings and ${locationCount} responsible-location references will be cleared.`,
        'Existing bookings will keep their other data but will no longer point to this person.',
        '',
        'This cannot be undone.'
      ].join('\n')
    );
    if (confirmed) {
      await deleteSelectedPerson();
    }
  }
</script>

<section class="inventory-workspace" aria-label="Persons workspace">
  <section class="panel inventory-table-panel">
    <div class="inventory-toolbar">
      <div>
        <h2>Persons</h2>
        <p>{persons.length} total</p>
      </div>
      <button type="button" class="compact" onclick={() => (showAddPerson = true)}>+ Add</button>
    </div>

    <div class="asset-table-wrap">
      <table class="asset-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Contact</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {#each persons as person}
            <tr
              class:selected-row={person.id === selectedPersonId}
              onclick={() => selectPersonDetail(person.id)}
            >
              <td>
                <strong>{person.display_name}</strong>
                <span
                  >{person.user_id ? `Linked: ${userLabel(person.user_id)}` : 'No login link'}</span
                >
              </td>
              <td>{personTypeLabel(person.person_type)}</td>
              <td>
                <strong>{person.email ?? 'No email'}</strong>
                <span>{person.phone ?? 'No phone'}</span>
              </td>
              <td>{person.is_active ? 'active' : 'inactive'}</td>
            </tr>
          {:else}
            <tr>
              <td colspan="4" class="empty">No persons yet.</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <aside class="panel inventory-detail-panel" aria-label="Selected person details">
    {#if selectedPerson()}
      <div class="detail-header asset-detail-header">
        <div>
          <p class="eyebrow">Person detail</p>
          <h2>{selectedPerson()?.display_name}</h2>
        </div>
        <div class="button-row compact-button-row">
          <button
            type="button"
            class="danger micro-button"
            disabled={busy}
            onclick={() => void confirmDeletePerson()}
          >
            Delete
          </button>
          <button type="button" class="secondary micro-button" onclick={closePersonDetail}>
            Close
          </button>
        </div>
      </div>

      <form
        class="asset-edit-form detail-tab-panel"
        onsubmit={(event) => {
          event.preventDefault();
          updateSelectedPerson();
        }}
      >
        <label class="compact-field-row">
          Name <input bind:value={personEditForm.display_name} required />
        </label>
        <label class="compact-field-row">
          Type
          <select bind:value={personEditForm.person_type}>
            {#each personTypes as type}
              <option value={type}>{personTypeLabel(type)}</option>
            {/each}
          </select>
        </label>
        <label class="compact-field-row">
          Email <input bind:value={personEditForm.email} type="email" />
        </label>
        <label class="compact-field-row">
          Phone <input bind:value={personEditForm.phone} />
        </label>
        <label class="compact-field-row">
          Linked user
          <select bind:value={personEditForm.user_id}>
            <option value={null}>No linked login user</option>
            {#each users as user}
              <option value={user.id}>{user.display_name} · {user.email}</option>
            {/each}
          </select>
        </label>
        <label class="description-field" aria-label="Person notes">
          <textarea bind:value={personEditForm.notes} placeholder="Notes about this person"
          ></textarea>
        </label>
        <label class="checkbox-label">
          <input bind:checked={personEditForm.is_active} type="checkbox" />
          Active
        </label>

        <div class="button-row compact-button-row">
          <button type="submit" class="compact" disabled={busy}>Update person</button>
          <button type="button" class="secondary compact" onclick={closePersonDetail}>Close</button>
        </div>
      </form>
    {:else}
      <div class="empty-detail">
        <h2>Select a person</h2>
        <p>Click a row in the table to view and edit person information.</p>
      </div>
    {/if}
  </aside>
</section>

{#if showAddPerson}
  <div class="modal-backdrop" role="presentation">
    <form
      class="panel modal-panel"
      aria-label="Add person"
      onsubmit={(event) => {
        event.preventDefault();
        submitNewPerson();
      }}
    >
      <div class="detail-header">
        <div>
          <p class="eyebrow">New person</p>
          <h2>Add person</h2>
        </div>
        <button type="button" class="secondary compact" onclick={() => (showAddPerson = false)}>
          Cancel
        </button>
      </div>
      <label>Name <input bind:value={personForm.display_name} required /></label>
      <label>
        Type
        <select bind:value={personForm.person_type}>
          {#each personTypes as type}
            <option value={type}>{personTypeLabel(type)}</option>
          {/each}
        </select>
      </label>
      <label>Email <input bind:value={personForm.email} type="email" /></label>
      <label>Phone <input bind:value={personForm.phone} /></label>
      <label>
        Linked user
        <select bind:value={personForm.user_id}>
          <option value={null}>No linked login user</option>
          {#each users as user}
            <option value={user.id}>{user.display_name} · {user.email}</option>
          {/each}
        </select>
      </label>
      <label>Notes <textarea bind:value={personForm.notes}></textarea></label>
      <label class="checkbox-label">
        <input bind:checked={personForm.is_active} type="checkbox" />
        Active
      </label>
      <div class="button-row">
        <button type="button" class="secondary" onclick={() => (showAddPerson = false)}>
          Cancel
        </button>
        <button type="submit" disabled={busy}>Save person</button>
      </div>
    </form>
  </div>
{/if}
