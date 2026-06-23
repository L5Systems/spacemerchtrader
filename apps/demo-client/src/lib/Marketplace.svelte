<script>
  import { createClient, getStoredToken, storeToken } from './api.js';
  import CategoryWorkspace from './CategoryWorkspace.svelte';

  let { apiBase } = $props();

  let token = $state(getStoredToken());
  let client = $derived(createClient(apiBase, token || undefined));

  let mode = $state('login');
  let email = $state('trader@starfall.corp');
  let password = $state('starfall123');
  let displayName = $state('');
  let role = $state('trader');
  let session = $state(null);
  let menu = $state(null);
  let categories = $state([]);
  let selectedCategory = $state('');
  let error = $state(null);
  let loading = $state(false);

  async function loadPublicCategories() {
    try {
      categories = await client.marketplaceCategories();
    } catch {
      categories = [];
    }
  }

  async function persistSession(result) {
    token = result.access_token;
    storeToken(token);
    session = result;
    await loadMenu();
  }

  async function loadMenu() {
    if (!token) return;
    loading = true;
    error = null;
    try {
      menu = await client.marketplaceMenu();
      session = await client.marketplaceMe();
      if (!selectedCategory && menu.categories?.length) {
        selectedCategory = menu.categories[0].id;
      }
    } catch (e) {
      error = e.message;
      logout(false);
    } finally {
      loading = false;
    }
  }

  async function signup() {
    loading = true;
    error = null;
    try {
      const result = await client.marketplaceSignup({
        email,
        password,
        display_name: displayName,
        role,
      });
      await persistSession(result);
      mode = 'browse';
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function login() {
    loading = true;
    error = null;
    try {
      const result = await client.marketplaceLogin({ email, password });
      await persistSession(result);
      mode = 'browse';
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function logout(clearError = true) {
    token = '';
    storeToken('');
    session = null;
    menu = null;
    mode = 'login';
    if (clearError) error = null;
  }

  $effect(() => {
    loadPublicCategories();
    if (token) {
      loadMenu();
    }
  });

  let visibleProviders = $derived(
    menu?.providers_by_category?.[selectedCategory] ?? [],
  );
</script>

<section class="marketplace">
  <header class="mp-header">
    <div>
      <p class="eyebrow">Marketplace</p>
      <h2>Service Provider Console</h2>
      <p class="tagline">Sign up, manage access, and browse logistics providers by service category.</p>
    </div>
    {#if session}
      <div class="session">
        <span class="badge info">{session.role}</span>
        <strong>{session.display_name}</strong>
        <span class="muted">{session.email}</span>
        <button onclick={() => logout()}>Sign out</button>
      </div>
    {/if}
  </header>

  <div class="mp-tabs">
    <button class:active={mode === 'login'} onclick={() => (mode = 'login')}>Sign in</button>
    <button class:active={mode === 'signup'} onclick={() => (mode = 'signup')}>Sign up</button>
    <button class:active={mode === 'browse'} disabled={!session} onclick={() => (mode = 'browse')}>
      Provider menu
    </button>
    <button class:active={mode === 'workspace'} disabled={!session} onclick={() => (mode = 'workspace')}>
      Service workspace
    </button>
    <button class:active={mode === 'access'} disabled={!session} onclick={() => (mode = 'access')}>
      My access
    </button>
  </div>

  {#if error}
    <div class="error-box">{error}</div>
  {/if}

  {#if mode === 'login'}
    <div class="mp-panel">
      <div class="field">
        <label for="login-email">Email</label>
        <input id="login-email" type="email" bind:value={email} />
      </div>
      <div class="field">
        <label for="login-password">Password</label>
        <input id="login-password" type="password" bind:value={password} />
      </div>
      <p class="hint">Demo account: trader@starfall.corp / starfall123</p>
      <button class="primary" onclick={login} disabled={loading}>Sign in</button>
    </div>
  {:else if mode === 'signup'}
    <div class="mp-panel">
      <div class="field">
        <label for="signup-name">Display name</label>
        <input id="signup-name" bind:value={displayName} placeholder="Your trading handle" />
      </div>
      <div class="field">
        <label for="signup-email">Email</label>
        <input id="signup-email" type="email" bind:value={email} />
      </div>
      <div class="field">
        <label for="signup-password">Password</label>
        <input id="signup-password" type="password" bind:value={password} />
      </div>
      <div class="field">
        <label for="signup-role">Client role</label>
        <select id="signup-role" bind:value={role}>
          <option value="trader">Trader</option>
          <option value="logistics">Logistics operator</option>
        </select>
      </div>
      <button class="primary" onclick={signup} disabled={loading}>Create account</button>
    </div>
  {:else if mode === 'browse' && menu}
    <div class="mp-panel browse">
      <div class="field">
        <label for="category">Service category</label>
        <select id="category" bind:value={selectedCategory}>
          {#each menu.categories as cat}
            <option value={cat.id}>{cat.label}</option>
          {/each}
        </select>
      </div>

      {#if selectedCategory}
        {@const catInfo = menu.categories.find((c) => c.id === selectedCategory)}
        {#if catInfo}
          <p class="meta">{catInfo.description}</p>
        {/if}
      {/if}

      {#if visibleProviders.length === 0}
        <p class="muted">No providers available for this category with your current access.</p>
      {:else}
        <div class="provider-grid">
          {#each visibleProviders as item}
            <article class="provider-card">
              <header>
                <strong>{item.provider_name}</strong>
                {#if item.verified}
                  <span class="badge ok">Verified</span>
                {/if}
              </header>
              <p class="meta">{item.system_id} · ★ {item.rating} · {item.base_rate} cr/{item.unit}</p>
              <p>{item.description}</p>
              <p class="mono capacity">Capacity: {item.capacity} {item.unit}s</p>
            </article>
          {/each}
        </div>
      {/if}
    </div>
  {:else if mode === 'workspace' && menu}
    <div class="mp-panel browse">
      <div class="field">
        <label for="ws-category">Service category</label>
        <select id="ws-category" bind:value={selectedCategory}>
          {#each menu.categories as cat}
            <option value={cat.id}>{cat.label}</option>
          {/each}
        </select>
      </div>
      {#if selectedCategory}
        {@const catInfo = menu.categories.find((c) => c.id === selectedCategory)}
        {#if catInfo}
          <p class="meta">{catInfo.description}</p>
        {/if}
        <CategoryWorkspace
          {client}
          category={selectedCategory}
          categoryLabel={catInfo?.label ?? selectedCategory}
        />
      {/if}
    </div>
  {:else if mode === 'access' && menu}
    <div class="mp-panel">
      <p class="meta">Categories enabled for your account:</p>
      <ul class="access-list">
        {#each menu.access as accessId}
          {@const cat = categories.find((c) => c.id === accessId) ?? menu.categories.find((c) => c.id === accessId)}
          <li>
            <span class="badge info">{accessId}</span>
            {cat?.label ?? accessId}
          </li>
        {/each}
      </ul>
      <p class="hint">
        Trader accounts get assembly, porter, and offworld delivery. Logistics and admin roles unlock all
        categories. Admins can manage access via PUT /marketplace/clients/{'{id}'}/access.
      </p>
    </div>
  {:else if loading}
    <p class="muted">Loading marketplace…</p>
  {/if}
</section>

<style>
  .marketplace {
    grid-area: marketplace;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: linear-gradient(135deg, #0a1220 0%, #101828 100%);
    padding: 1.25rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .mp-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .eyebrow {
    margin: 0;
    color: var(--accent);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 600;
  }

  .mp-header h2 {
    margin: 0.15rem 0 0;
    font-size: 1.35rem;
  }

  .tagline {
    margin: 0.35rem 0 0;
    color: var(--text-muted);
    max-width: 60ch;
  }

  .session {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
  }

  .muted {
    color: var(--text-muted);
  }

  .mp-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .mp-tabs button.active {
    border-color: var(--accent);
    color: var(--accent);
  }

  .mp-panel {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    max-width: 720px;
  }

  .mp-panel.browse {
    max-width: none;
  }

  .hint {
    margin: 0;
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .meta {
    margin: 0;
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .provider-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.85rem;
  }

  .provider-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .provider-card header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .provider-card p {
    margin: 0;
    font-size: 0.88rem;
  }

  .capacity {
    color: var(--gold);
  }

  .access-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .access-list li {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
</style>
