<script>
  /** @type {string | null} */
  let { data = null, error = null, loading = false } = $props();
</script>

{#if loading}
  <p class="status">Loading…</p>
{:else if error}
  <div class="error-box">{error}</div>
{:else if data !== null}
  <pre class="json-box">{JSON.stringify(data, null, 2)}</pre>
{:else}
  <p class="status muted">No data yet — run a request above.</p>
{/if}

<style>
  .status {
    margin: 0;
    font-size: 0.9rem;
  }

  .muted {
    color: var(--text-muted);
  }
</style>
