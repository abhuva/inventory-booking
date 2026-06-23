<script lang="ts">
  import type {
    Category,
    CategoryCreate,
    CategoryUpdate,
    User,
    UserCreate,
    UserRole
  } from '$lib/api';

  type AdminTab = 'users' | 'categories';

  let {
    categories,
    users,
    busy,
    categoryForm = $bindable(),
    categoryUpdateForm = $bindable(),
    userCreateForm = $bindable(),
    userUpdateForm = $bindable(),
    createCategory,
    updateCategory,
    createUser,
    updateUser
  }: {
    categories: Category[];
    users: User[];
    busy: boolean;
    categoryForm: CategoryCreate;
    categoryUpdateForm: CategoryUpdate & { category_id: string };
    userCreateForm: UserCreate;
    userUpdateForm: {
      user_id: string;
      display_name: string;
      role: UserRole;
      is_active: boolean;
      password: string;
    };
    createCategory: () => void;
    updateCategory: () => void;
    createUser: () => void;
    updateUser: () => void;
  } = $props();

  let activeAdminTab = $state<AdminTab>('users');

  function startCreateUser(): void {
    userCreateForm = {
      email: '',
      display_name: '',
      password: '',
      role: 'user',
      is_active: true
    };
    userUpdateForm = {
      user_id: '',
      display_name: '',
      role: 'user',
      is_active: true,
      password: ''
    };
  }

  function selectUser(user: User): void {
    userUpdateForm = {
      user_id: user.id,
      display_name: user.display_name,
      role: user.role,
      is_active: user.is_active,
      password: ''
    };
  }

  function selectedUser(): User | undefined {
    return users.find((user) => user.id === userUpdateForm.user_id);
  }

  function startCreateCategory(): void {
    categoryForm = { name: '', description: '' };
    categoryUpdateForm = { category_id: '', name: '', description: '' };
  }

  function selectCategory(category: Category): void {
    categoryUpdateForm = {
      category_id: category.id,
      name: category.name,
      description: category.description ?? ''
    };
  }

  function selectedCategory(): Category | undefined {
    return categories.find((category) => category.id === categoryUpdateForm.category_id);
  }
</script>

<section class="admin-workspace" aria-label="Admin workspace">
  <div class="detail-tab-bar admin-tab-bar" role="tablist" aria-label="Admin sections">
    <button
      type="button"
      class:active-detail-tab={activeAdminTab === 'users'}
      onclick={() => (activeAdminTab = 'users')}
    >
      Users
    </button>
    <button
      type="button"
      class:active-detail-tab={activeAdminTab === 'categories'}
      onclick={() => (activeAdminTab = 'categories')}
    >
      Categories
    </button>
  </div>

  {#if activeAdminTab === 'users'}
    <div class="admin-split-workspace">
      <section class="panel inventory-table-panel admin-table-panel">
        <div class="inventory-toolbar">
          <div>
            <h2>Users</h2>
            <p>{users.length} visible</p>
          </div>
          <button type="button" class="compact" onclick={startCreateUser}>Add</button>
        </div>

        <div class="asset-table-wrap">
          <table class="asset-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {#each users as user}
                <tr
                  class:selected-row={userUpdateForm.user_id === user.id}
                  onclick={() => selectUser(user)}
                >
                  <td><strong>{user.display_name}</strong></td>
                  <td>{user.email}</td>
                  <td>{user.role}</td>
                  <td>{user.is_active ? 'active' : 'disabled'}</td>
                </tr>
              {:else}
                <tr>
                  <td colspan="4">No users visible.</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel inventory-detail-panel admin-detail-panel">
        {#if userUpdateForm.user_id && selectedUser()}
          <div class="detail-header asset-detail-header">
            <div>
              <h2>{selectedUser()?.display_name}</h2>
              <p>{selectedUser()?.email}</p>
            </div>
          </div>

          <form
            class="admin-detail-form"
            onsubmit={(event) => {
              event.preventDefault();
              updateUser();
            }}
          >
            <label>Name <input bind:value={userUpdateForm.display_name} required /></label>
            <div class="split-fields">
              <label>
                Role
                <select bind:value={userUpdateForm.role}>
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                </select>
              </label>
              <label
                >New password <input bind:value={userUpdateForm.password} type="password" /></label
              >
            </div>
            <label class="checkbox-label">
              <input bind:checked={userUpdateForm.is_active} type="checkbox" />
              Active
            </label>
            <div class="button-row compact-button-row">
              <button type="submit" class="compact" disabled={busy}>Update user</button>
              <button type="button" class="secondary compact" onclick={startCreateUser}
                >New user</button
              >
            </div>
          </form>
        {:else}
          <div class="detail-header asset-detail-header">
            <div>
              <h2>Create user</h2>
              <p>Add a local account for this tool.</p>
            </div>
          </div>

          <form
            class="admin-detail-form"
            onsubmit={(event) => {
              event.preventDefault();
              createUser();
            }}
          >
            <label>Email <input bind:value={userCreateForm.email} type="email" required /></label>
            <label>Name <input bind:value={userCreateForm.display_name} required /></label>
            <div class="split-fields">
              <label>
                Role
                <select bind:value={userCreateForm.role}>
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                </select>
              </label>
              <label
                >Password <input
                  bind:value={userCreateForm.password}
                  type="password"
                  required
                /></label
              >
            </div>
            <label class="checkbox-label">
              <input bind:checked={userCreateForm.is_active} type="checkbox" />
              Active
            </label>
            <button type="submit" class="compact" disabled={busy}>Create user</button>
          </form>
        {/if}
      </section>
    </div>
  {/if}

  {#if activeAdminTab === 'categories'}
    <div class="admin-split-workspace">
      <section class="panel inventory-table-panel admin-table-panel">
        <div class="inventory-toolbar">
          <div>
            <h2>Categories</h2>
            <p>{categories.length} visible</p>
          </div>
          <button type="button" class="compact" onclick={startCreateCategory}>Add</button>
        </div>

        <div class="asset-table-wrap">
          <table class="asset-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {#each categories as category}
                <tr
                  class:selected-row={categoryUpdateForm.category_id === category.id}
                  onclick={() => selectCategory(category)}
                >
                  <td><strong>{category.name}</strong></td>
                  <td>{category.description ?? 'No description'}</td>
                </tr>
              {:else}
                <tr>
                  <td colspan="2">No categories yet.</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel inventory-detail-panel admin-detail-panel">
        {#if categoryUpdateForm.category_id && selectedCategory()}
          <div class="detail-header asset-detail-header">
            <div>
              <h2>{selectedCategory()?.name}</h2>
              <p>{selectedCategory()?.description ?? 'No description'}</p>
            </div>
          </div>

          <form
            class="admin-detail-form"
            onsubmit={(event) => {
              event.preventDefault();
              updateCategory();
            }}
          >
            <label>Name <input bind:value={categoryUpdateForm.name} required /></label>
            <label
              >Description <textarea bind:value={categoryUpdateForm.description}></textarea></label
            >
            <div class="button-row compact-button-row">
              <button type="submit" class="compact" disabled={busy}>Update category</button>
              <button type="button" class="secondary compact" onclick={startCreateCategory}>
                New category
              </button>
            </div>
          </form>
        {:else}
          <div class="detail-header asset-detail-header">
            <div>
              <h2>Create category</h2>
              <p>Group assets into practical inventory sections.</p>
            </div>
          </div>

          <form
            class="admin-detail-form"
            onsubmit={(event) => {
              event.preventDefault();
              createCategory();
            }}
          >
            <label>Name <input bind:value={categoryForm.name} required /></label>
            <label>Description <textarea bind:value={categoryForm.description}></textarea></label>
            <button type="submit" class="compact" disabled={busy}>Create category</button>
          </form>
        {/if}
      </section>
    </div>
  {/if}
</section>
