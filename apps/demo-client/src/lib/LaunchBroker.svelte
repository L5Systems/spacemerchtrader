<script>
  import { createClient, getStoredToken, notifyGameReward } from './api.js';

  let { apiBase } = $props();

  let token = $state(getStoredToken());
  let client = $derived(createClient(apiBase, token || undefined));
  /** @type {Array<{ role: 'user' | 'broker', text: string }>} */
  let messages = $state([
    {
      role: 'broker',
      text: 'I am your Launch Broker for Starship239 LEO manifests. Ask me to find a September 2032 slot, book it, add or list packages, query the manifest registry, advertise capacity, or validate packages.',
    },
  ]);
  /** @type {string[]} */
  let suggestions = $state([
    'How many packages are booked for Starship239 on 22 Sept 2032?',
    'show manifest registry for Starship239',
    'find a LEO slot for September 2032 on Starship239',
    'help',
  ]);
  let input = $state('');
  let loading = $state(false);
  let error = $state(null);

  async function sendInstruction(text = input) {
    const instruction = text.trim();
    if (!instruction || loading) return;

    messages = [...messages, { role: 'user', text: instruction }];
    input = '';
    loading = true;
    error = null;

    try {
      const result = await client.launchBrokerChat({ instruction });
      messages = [...messages, { role: 'broker', text: result.message }];
      suggestions = result.suggestions ?? [];
      if (result.game_result) {
        notifyGameReward(result.game_result);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      messages = [
        ...messages,
        { role: 'broker', text: `Sorry — ${error}. Sign in via Marketplace if you have not already.` },
      ];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    token = getStoredToken();
    const onAuth = () => {
      token = getStoredToken();
    };
    window.addEventListener('starfall-auth-changed', onAuth);
    return () => window.removeEventListener('starfall-auth-changed', onAuth);
  });
</script>

<section class="launch-broker">
  <header>
    <p class="eyebrow">Launch Broker</p>
    <h3>Starship239 LEO manifest assistant</h3>
    <p class="meta">
      Book a factory berth, add packages to your booked container, list cargo, browse the starship manifest registry, advertise outbound/return slots, and validate customer packages.
    </p>
  </header>

  {#if !token}
    <p class="muted">Sign in via Marketplace to book slots and track mission progress.</p>
  {/if}

  {#if error}
    <div class="error-box">{error}</div>
  {/if}

  <div class="chat-log">
    {#each messages as msg, index (index)}
      <article class="bubble {msg.role}">
        <span class="who">{msg.role === 'broker' ? 'Broker' : 'You'}</span>
        <p>{msg.text}</p>
      </article>
    {/each}
  </div>

  {#if suggestions.length}
    <div class="suggestions">
      {#each suggestions as suggestion}
        <button type="button" onclick={() => sendInstruction(suggestion)} disabled={loading || !token}>
          {suggestion}
        </button>
      {/each}
    </div>
  {/if}

  <form
    class="chat-input"
    onsubmit={(e) => {
      e.preventDefault();
      sendInstruction();
    }}
  >
    <input
      bind:value={input}
      placeholder={token ? 'Ask the broker…' : 'Sign in to chat with the broker'}
      disabled={loading || !token}
    />
    <button type="submit" class="primary" disabled={loading || !token || !input.trim()}>
      {loading ? 'Thinking…' : 'Send'}
    </button>
  </form>
</section>

<style>
  .launch-broker {
    margin-top: 1rem;
    padding: 1rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--bg-panel);
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }

  header h3 {
    margin: 0.15rem 0 0;
  }

  .eyebrow {
    margin: 0;
    color: var(--gold);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  .meta {
    margin: 0.25rem 0 0;
    color: var(--text-muted);
    font-size: 0.88rem;
  }

  .chat-log {
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    max-height: 320px;
    overflow: auto;
    padding: 0.5rem;
    background: var(--bg-deep);
    border: 1px solid var(--border);
    border-radius: 10px;
  }

  .bubble {
    padding: 0.65rem 0.75rem;
    border-radius: 10px;
    border: 1px solid var(--border);
  }

  .bubble.broker {
    background: rgba(20, 40, 56, 0.8);
  }

  .bubble.user {
    background: rgba(40, 32, 16, 0.5);
    align-self: flex-end;
    max-width: 85%;
  }

  .who {
    display: block;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin-bottom: 0.2rem;
  }

  .bubble p {
    margin: 0;
    white-space: pre-wrap;
    font-size: 0.9rem;
  }

  .suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .suggestions button {
    font-size: 0.82rem;
    padding: 0.35rem 0.65rem;
  }

  .chat-input {
    display: flex;
    gap: 0.5rem;
  }

  .chat-input input {
    flex: 1;
  }

  .muted {
    color: var(--text-muted);
  }
</style>
