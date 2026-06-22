<script>
  let { title, subtitle = '', children, actions } = $props();
</script>

<section class="panel">
  <header class="panel-header">
    <div>
      <h2>{title}</h2>
      {#if subtitle}
        <p>{subtitle}</p>
      {/if}
    </div>
    {#if actions}
      <div class="actions">{@render actions()}</div>
    {/if}
  </header>
  <div class="panel-body">
    {@render children()}
  </div>
</section>

<style>
  .panel {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    padding: 1rem 1.15rem;
    border-bottom: 1px solid var(--border);
    background: rgba(20, 30, 51, 0.5);
  }

  h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  p {
    margin: 0.2rem 0 0;
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .actions {
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .panel-body {
    padding: 1rem 1.15rem 1.15rem;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    min-height: 0;
  }
</style>
