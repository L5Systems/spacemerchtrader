<script>
  import { SYSTEMS, notifyGameFeedback, notifyGameReward } from './api.js';
  import { emptyForm, getWorkspaceConfig, RECORD_STATUSES } from './serviceCategoryConfig.js';

  let { client, category, categoryLabel = '' } = $props();

  let workspace = $derived(getWorkspaceConfig(category));
  let view = $state('list');
  let records = $state([]);
  let selected = $state(null);
  let form = $state({});
  let packageForm = $state({});
  let contractors = $state([]);
  let error = $state(null);
  let loading = $state(false);
  let editingPackage = $state(null);

  const DISPOSITION_BADGES = {
    reliable: { label: 'Reliable', className: 'ok' },
    crooked: { label: 'Crooked', className: 'warn' },
    accident_prone: { label: 'Accident-prone', className: 'err' },
  };

  const OUTCOME_BADGES = {
    pending: { label: 'Awaiting pickup', className: 'info' },
    picked_up: { label: 'Picked up', className: 'ok' },
    skimmed: { label: 'Skimmed', className: 'warn' },
    incident: { label: 'Incident', className: 'err' },
  };

  function contractorLabel(id) {
    const match = contractors.find((c) => c.id === id);
    if (!match) return id;
    return `${match.name} (${match.disposition_label})`;
  }

  async function loadContractors() {
    if (category !== 'container_collection') {
      contractors = [];
      return;
    }
    try {
      contractors = await client.listCollectionContractors();
    } catch {
      contractors = [];
    }
  }

  function resetForm(record = null) {
    if (!workspace) return;
    form = record
      ? Object.fromEntries(
          workspace.fields.map((f) => [
            f.key,
            f.type === 'number' ? String(record[f.key] ?? 0) : String(record[f.key] ?? ''),
          ]),
        )
      : emptyForm(workspace.fields);
    if (workspace.packages) {
      packageForm = emptyForm(workspace.packages.fields);
      editingPackage = null;
    }
  }

  async function loadRecords() {
    if (!category) return;
    loading = true;
    error = null;
    try {
      records = await client.listServiceRecords(category);
    } catch (e) {
      error = e.message;
      records = [];
    } finally {
      loading = false;
    }
  }

  async function openRecord(record) {
    loading = true;
    error = null;
    try {
      selected = await client.getServiceRecord(category, record.id);
      resetForm(selected);
      view = 'detail';
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function saveRecord() {
    if (!workspace) return;
    loading = true;
    error = null;
    try {
      const payload = { ...form };
      for (const field of workspace.fields) {
        if (field.type === 'number') payload[field.key] = Number(payload[field.key] || 0);
      }
      if (view === 'create') {
        await client.createServiceRecord(category, payload);
        view = 'list';
        await loadRecords();
      } else if (selected) {
        selected = await client.updateServiceRecord(category, selected.id, payload);
        resetForm(selected);
        await loadRecords();
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function deleteRecord() {
    if (!selected) return;
    loading = true;
    error = null;
    try {
      await client.deleteServiceRecord(category, selected.id);
      selected = null;
      view = 'list';
      await loadRecords();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function savePackage() {
    if (!selected || !workspace?.packages) return;
    loading = true;
    error = null;
    try {
      if (editingPackage) {
        await client.updateContainerPackage(editingPackage.id, packageForm);
      } else {
        await client.addContainerPackage(selected.id, packageForm);
      }
      selected = await client.getServiceRecord(category, selected.id);
      packageForm = emptyForm(workspace.packages.fields);
      editingPackage = null;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function editPackage(pkg) {
    editingPackage = pkg;
    packageForm = Object.fromEntries(
      workspace.packages.fields.map((f) => [f.key, String(pkg[f.key] ?? '')]),
    );
  }

  async function removePackage(pkg) {
    if (!selected) return;
    loading = true;
    error = null;
    try {
      await client.deleteContainerPackage(pkg.id);
      selected = await client.getServiceRecord(category, selected.id);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function executePickup() {
    if (!selected || category !== 'container_collection') return;
    loading = true;
    error = null;
    try {
      const result = await client.executeCollectionPickup(selected.id);
      selected = result.job;
      resetForm(selected);
      await loadRecords();

      if (result.game_result) {
        notifyGameReward(result.game_result);
      } else {
        notifyGameFeedback({
          title: 'Pickup attempt failed',
          message: result.job.outcome_detail || 'The contractor reported an incident. Try again.',
          variant: 'warning',
        });
      }
    } catch (e) {
      error = e.message;
      notifyGameFeedback({
        title: 'Pickup failed',
        message: e.message,
        variant: 'danger',
      });
    } finally {
      loading = false;
    }
  }

  function startCreate() {
    selected = null;
    resetForm();
    view = 'create';
  }

  $effect(() => {
    if (category && client) {
      view = 'list';
      selected = null;
      loadContractors();
      loadRecords();
    }
  });
</script>

{#if workspace}
  <section class="workspace">
    <header class="ws-header">
      <div>
        <h3>{workspace.label} workspace</h3>
        <p class="meta">{categoryLabel}</p>
      </div>
      <div class="ws-actions">
        <button class:active={view === 'list'} onclick={() => (view = 'list')}>Read</button>
        <button class:active={view === 'create'} onclick={startCreate}>Create</button>
        {#if selected}
          <button class:active={view === 'detail'} onclick={() => (view = 'detail')}>Update</button>
        {/if}
      </div>
    </header>

    {#if error}
      <div class="error-box">{error}</div>
    {/if}

    {#if view === 'list'}
      {#if loading}
        <p class="muted">Loading records…</p>
      {:else if records.length === 0}
        <p class="muted">No {workspace.recordLabel.toLowerCase()}s yet. Use Create to add one.</p>
      {:else}
        <div class="record-list">
          {#each records as record}
            <button class="record-row" onclick={() => openRecord(record)}>
              <strong>{record[workspace.summaryField]}</strong>
              <span class="badge info">{record.status}</span>
              {#if record.outcome}
                <span class="badge {OUTCOME_BADGES[record.outcome]?.className ?? 'info'}">
                  {OUTCOME_BADGES[record.outcome]?.label ?? record.outcome}
                </span>
              {/if}
              {#if record.package_count != null}
                <span class="muted">{record.package_count} packages</span>
              {/if}
              {#if record.contractor_name}
                <span class="muted">{record.contractor_name}</span>
              {:else}
                <span class="muted mono">{record.owner_name ?? record.system_id ?? ''}</span>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    {:else if view === 'create' || view === 'detail'}
      <div class="form-grid">
        {#each workspace.fields as field}
          <div class="field">
            <label for={`field-${field.key}`}>{field.label}</label>
            {#if field.type === 'textarea'}
              <textarea id={`field-${field.key}`} bind:value={form[field.key]} rows="2"></textarea>
            {:else if field.type === 'system'}
              <select id={`field-${field.key}`} bind:value={form[field.key]}>
                {#each SYSTEMS as sys}
                  <option value={sys.id}>{sys.name}</option>
                {/each}
              </select>
            {:else if field.type === 'status'}
              <select id={`field-${field.key}`} bind:value={form[field.key]}>
                {#each RECORD_STATUSES as status}
                  <option value={status}>{status}</option>
                {/each}
              </select>
            {:else if field.type === 'contractor'}
              <select id={`field-${field.key}`} bind:value={form[field.key]}>
                <option value="">Select contractor…</option>
                {#each contractors as contractor}
                  <option value={contractor.id}>
                    {contractor.name} — {contractor.disposition_label}
                  </option>
                {/each}
              </select>
              {#if form.contractor_id}
                {@const picked = contractors.find((c) => c.id === form.contractor_id)}
                {#if picked}
                  <p class="field-hint">
                    <span class="badge {DISPOSITION_BADGES[picked.disposition]?.className ?? 'info'}">
                      {picked.disposition_label}
                    </span>
                    {picked.description}
                  </p>
                {/if}
              {/if}
            {:else}
              <input
                id={`field-${field.key}`}
                type={field.type === 'number' ? 'number' : 'text'}
                bind:value={form[field.key]}
                placeholder={field.placeholder ?? ''}
              />
            {/if}
          </div>
        {/each}
      </div>

      <div class="form-actions">
        <button class="primary" onclick={saveRecord} disabled={loading}>
          {view === 'create' ? 'Create' : 'Save changes'}
        </button>
        {#if view === 'detail' && workspace.pickupAction && selected?.status !== 'completed'}
          <button class="accent" onclick={executePickup} disabled={loading}>
            Execute offshore pickup
          </button>
        {/if}
        {#if view === 'detail'}
          <button class="danger" onclick={deleteRecord} disabled={loading}>Delete</button>
        {/if}
        <button onclick={() => (view = 'list')}>Cancel</button>
      </div>

      {#if view === 'detail' && selected?.outcome_detail}
        <div class="outcome-box {selected.outcome ?? 'pending'}">
          <strong>{OUTCOME_BADGES[selected.outcome]?.label ?? 'Outcome'}</strong>
          <p>{selected.outcome_detail}</p>
          {#if selected.pickup_attempts}
            <p class="meta">Attempts: {selected.pickup_attempts}</p>
          {/if}
        </div>
      {/if}

      {#if view === 'detail' && workspace.packages && selected}
        <div class="packages">
          <h4>Packages on container</h4>
          {#if selected.packages?.length}
            <table>
              <thead>
                <tr>
                  <th>Package ID</th>
                  <th>Owner</th>
                  <th>Recipient</th>
                  <th>Address</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {#each selected.packages as pkg}
                  <tr>
                    <td class="mono">{pkg.package_id}</td>
                    <td>{pkg.owner_name}</td>
                    <td>{pkg.recipient_name} ({pkg.recipient_id})</td>
                    <td>{pkg.address}</td>
                    <td class="row-actions">
                      <button onclick={() => editPackage(pkg)}>Edit</button>
                      <button onclick={() => removePackage(pkg)}>Remove</button>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {:else}
            <p class="muted">No packages loaded on this container yet.</p>
          {/if}

          <div class="package-form">
            <h4>{editingPackage ? 'Update package' : 'Add package'}</h4>
            <div class="form-grid">
              {#each workspace.packages.fields as field}
                <div class="field">
                  <label for={`pkg-${field.key}`}>{field.label}</label>
                  {#if field.type === 'textarea'}
                    <textarea id={`pkg-${field.key}`} bind:value={packageForm[field.key]} rows="2"></textarea>
                  {:else if field.type === 'leg'}
                    <select id={`pkg-${field.key}`} bind:value={packageForm[field.key]}>
                      <option value="">Select leg…</option>
                      <option value="outbound">Outbound to LEO factory</option>
                      <option value="return">Return to ground</option>
                    </select>
                  {:else}
                    <input
                      id={`pkg-${field.key}`}
                      bind:value={packageForm[field.key]}
                      placeholder={field.placeholder ?? ''}
                    />
                  {/if}
                </div>
              {/each}
            </div>
            <div class="form-actions">
              <button class="primary" onclick={savePackage} disabled={loading}>
                {editingPackage ? 'Save package' : 'Add package'}
              </button>
              {#if editingPackage}
                <button
                  onclick={() => {
                    editingPackage = null;
                    packageForm = emptyForm(workspace.packages.fields);
                  }}
                >
                  Cancel edit
                </button>
              {/if}
            </div>
          </div>
        </div>
      {/if}
    {/if}
  </section>
{/if}

<style>
  .workspace {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .ws-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .ws-header h3 {
    margin: 0;
    font-size: 1.05rem;
  }

  .ws-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .ws-actions button.active {
    border-color: var(--accent);
    color: var(--accent);
  }

  .record-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .record-row {
    display: grid;
    grid-template-columns: 1fr auto auto 1fr;
    gap: 0.75rem;
    align-items: center;
    text-align: left;
    padding: 0.75rem 1rem;
    width: 100%;
  }

  .field-hint {
    margin: 0.35rem 0 0;
    font-size: 0.82rem;
    color: var(--text-muted);
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
  }

  button.accent {
    border-color: var(--gold);
    color: var(--gold);
  }

  .outcome-box {
    padding: 0.85rem 1rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--bg-panel);
  }

  .outcome-box strong {
    display: block;
    margin-bottom: 0.25rem;
  }

  .outcome-box p {
    margin: 0;
    font-size: 0.88rem;
  }

  .outcome-box.picked_up {
    border-color: rgba(94, 230, 154, 0.3);
  }

  .outcome-box.skimmed,
  .outcome-box.incident {
    border-color: rgba(240, 192, 96, 0.3);
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.75rem;
  }

  textarea {
    background: var(--bg-deep);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    width: 100%;
    font: inherit;
    resize: vertical;
  }

  .form-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  button.danger {
    border-color: #5a2030;
    color: var(--danger);
  }

  .packages {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 12px;
  }

  .packages h4 {
    margin: 0;
    font-size: 0.95rem;
  }

  .package-form {
    padding-top: 0.75rem;
    border-top: 1px solid var(--border);
  }

  .row-actions {
    display: flex;
    gap: 0.35rem;
    white-space: nowrap;
  }

  .muted {
    color: var(--text-muted);
  }
</style>
