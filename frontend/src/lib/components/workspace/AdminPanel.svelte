<script lang="ts">
  import type {
    Category,
    CategoryCreate,
    CategoryUpdate,
    User,
    UserCreate,
    UserRole
  } from '$lib/api';

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
    updateUser,
    selectCategoryForEdit,
    selectUserForEdit
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
    selectCategoryForEdit: (event: Event) => void;
    selectUserForEdit: (event: Event) => void;
  } = $props();
</script>

<section class="forms-grid" aria-label="Admin controls">
  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      createCategory();
    }}
  >
    <h2>Category</h2>
    <label>Name <input bind:value={categoryForm.name} required /></label>
    <label>Description <textarea bind:value={categoryForm.description}></textarea></label>
    <button type="submit" disabled={busy}>Create category</button>
  </form>

  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      updateCategory();
    }}
  >
    <h2>Edit category</h2>
    <label>
      Category
      <select value={categoryUpdateForm.category_id} onchange={selectCategoryForEdit} required>
        <option value="">Choose category</option>
        {#each categories as category}
          <option value={category.id}>{category.name}</option>
        {/each}
      </select>
    </label>
    <label>Name <input bind:value={categoryUpdateForm.name} required /></label>
    <label>Description <textarea bind:value={categoryUpdateForm.description}></textarea></label>
    <button type="submit" disabled={busy}>Update category</button>
  </form>

  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      createUser();
    }}
  >
    <h2>Create user</h2>
    <label>Email <input bind:value={userCreateForm.email} type="email" required /></label>
    <label>Name <input bind:value={userCreateForm.display_name} required /></label>
    <label>
      Role
      <select bind:value={userCreateForm.role}>
        <option value="user">user</option>
        <option value="admin">admin</option>
      </select>
    </label>
    <label>Password <input bind:value={userCreateForm.password} type="password" required /></label>
    <label class="checkbox-label">
      <input bind:checked={userCreateForm.is_active} type="checkbox" />
      Active
    </label>
    <button type="submit" disabled={busy}>Create user</button>
  </form>

  <form
    class="panel form-panel"
    onsubmit={(event) => {
      event.preventDefault();
      updateUser();
    }}
  >
    <h2>Edit user</h2>
    <label>
      User
      <select value={userUpdateForm.user_id} onchange={selectUserForEdit} required>
        <option value="">Choose user</option>
        {#each users as user}
          <option value={user.id}>{user.display_name} � {user.email}</option>
        {/each}
      </select>
    </label>
    <label>Name <input bind:value={userUpdateForm.display_name} required /></label>
    <label>
      Role
      <select bind:value={userUpdateForm.role}>
        <option value="user">user</option>
        <option value="admin">admin</option>
      </select>
    </label>
    <label>New password <input bind:value={userUpdateForm.password} type="password" /></label>
    <label class="checkbox-label">
      <input bind:checked={userUpdateForm.is_active} type="checkbox" />
      Active
    </label>
    <button type="submit" disabled={busy}>Update user</button>
  </form>
</section>

<section class="data-grid" aria-label="Admin lists">
  <article class="panel list-panel">
    <h2>Users</h2>
    {#each users as user}
      <div class="row-card">
        <strong>{user.display_name}</strong>
        <span>{user.email} � {user.role} � {user.is_active ? 'active' : 'disabled'}</span>
      </div>
    {:else}
      <p class="empty">No users visible.</p>
    {/each}
  </article>

  <article class="panel list-panel">
    <h2>Categories</h2>
    {#each categories as category}
      <div class="row-card">
        <strong>{category.name}</strong>
        <span>{category.description ?? 'No description'}</span>
      </div>
    {:else}
      <p class="empty">No categories yet.</p>
    {/each}
  </article>
</section>
