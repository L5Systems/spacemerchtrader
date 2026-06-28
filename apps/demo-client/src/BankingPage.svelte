<script>
  import BankingAgent from './lib/BankingAgent.svelte';
  import GameFeedback from './lib/GameFeedback.svelte';
  import { navigate } from './lib/routing.js';

  let apiBase = $state('/api');
</script>

<div class="banking-page">
  <GameFeedback />

  <header class="page-header">
    <button type="button" class="back-link" onclick={() => navigate('/')}>
      ← Back to dashboard
    </button>
    <div>
      <p class="eyebrow">Starfall Galactic Bank</p>
      <h1>Banking agent</h1>
      <p class="tagline">
        Manage your SF account — deposit wallet credits, withdraw cash, and transfer to other
        traders.
      </p>
    </div>
    <div class="field api-field">
      <label for="bank-api-base">API base URL</label>
      <input id="bank-api-base" bind:value={apiBase} placeholder="/api" />
    </div>
  </header>

  <BankingAgent {apiBase} />
</div>

<style>
  .banking-page {
    max-width: 960px;
    margin: 0 auto;
    padding: 1.5rem 1rem 2rem;
  }

  .page-header {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 0.5rem;
  }

  .back-link {
    align-self: flex-start;
    padding: 0.35rem 0.75rem;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: transparent;
    color: inherit;
    cursor: pointer;
    font-size: 0.9rem;
  }

  .back-link:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .eyebrow {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
    margin: 0;
  }

  h1 {
    margin: 0.25rem 0;
    font-size: 1.75rem;
  }

  .tagline {
    margin: 0.25rem 0 0;
    opacity: 0.85;
    max-width: 42rem;
  }

  .api-field {
    max-width: 280px;
  }

  .api-field label {
    display: block;
    font-size: 0.8rem;
    margin-bottom: 0.25rem;
    opacity: 0.8;
  }

  .api-field input {
    width: 100%;
    padding: 0.45rem 0.6rem;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: inherit;
  }
</style>
