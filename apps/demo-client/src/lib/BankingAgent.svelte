<script>
  import { createClient, getStoredToken, notifyGameReward } from './api.js';

  let { apiBase } = $props();

  let token = $state(getStoredToken());
  let client = $derived(createClient(apiBase, token || undefined));
  /** @type {Array<{ role: 'user' | 'banker', text: string }>} */
  let messages = $state([
    {
      role: 'banker',
      text: 'Welcome to Starfall Galactic Bank. Ask for your balance, deposit wallet credits, withdraw to your wallet, or transfer to another trader.',
    },
  ]);
  /** @type {string[]} */
  let suggestions = $state(['balance', 'deposit 500', 'withdraw 200', 'help']);
  /** @type {{ account_number?: string, bank_balance?: number, wallet_credits?: number } | null} */
  let accountMeta = $state(null);
  let input = $state('');
  let loading = $state(false);
  let error = $state(null);

  async function loadAccount() {
    if (!token) return;
    try {
      const data = await client.bankingAccount();
      accountMeta = data.account;
    } catch {
      accountMeta = null;
    }
  }

  async function sendInstruction(text = input) {
    const instruction = text.trim();
    if (!instruction || loading) return;

    messages = [...messages, { role: 'user', text: instruction }];
    input = '';
    loading = true;
    error = null;

    try {
      const result = await client.bankingChat({ instruction });
      messages = [...messages, { role: 'banker', text: result.message }];
      suggestions = result.suggestions ?? [];
      if (result.data?.account) {
        accountMeta = result.data.account;
      }
      if (result.game_result) {
        notifyGameReward(result.game_result);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      messages = [
        ...messages,
        {
          role: 'banker',
          text: `Sorry — ${error}. Sign in via Marketplace if you have not already.`,
        },
      ];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    token = getStoredToken();
    const onAuth = () => {
      token = getStoredToken();
      void loadAccount();
    };
    const onReward = () => {
      void loadAccount();
    };
    window.addEventListener('starfall-auth-changed', onAuth);
    window.addEventListener('starfall-game-reward', onReward);
    if (token) void loadAccount();
    return () => {
      window.removeEventListener('starfall-auth-changed', onAuth);
      window.removeEventListener('starfall-game-reward', onReward);
    };
  });
</script>

<section class="banking-agent">
  {#if accountMeta?.account_number}
    <p class="balance-pill">
      {accountMeta.account_number} · bank {accountMeta.bank_balance ?? 0} cr · wallet{' '}
      {accountMeta.wallet_credits ?? 0} cr
    </p>
  {/if}

  {#if !token}
    <p class="muted">Sign in via Marketplace to use your bank account.</p>
  {/if}

  {#if error}
    <div class="error-box">{error}</div>
  {/if}

  <div class="chat-log">
    {#each messages as msg, index (index)}
      <article class="bubble {msg.role}">
        <span class="who">{msg.role === 'banker' ? 'Banker' : 'You'}</span>
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
      placeholder={token ? 'Ask the banker…' : 'Sign in to chat with the banker'}
      disabled={loading || !token}
    />
    <button type="submit" class="primary" disabled={loading || !token || !input.trim()}>
      {loading ? 'Processing…' : 'Send'}
    </button>
  </form>
</section>

<style>
  .banking-agent {
    margin-top: 0.5rem;
    padding: 1rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--panel);
  }

  .balance-pill {
    display: inline-block;
    margin: 0 0 0.75rem;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    background: rgba(120, 200, 120, 0.15);
    font-size: 0.85rem;
  }

  .muted {
    opacity: 0.7;
    font-size: 0.9rem;
  }

  .error-box {
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.75rem;
    border-radius: 6px;
    background: rgba(255, 80, 80, 0.12);
    color: #ffb4b4;
    font-size: 0.9rem;
  }

  .chat-log {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    max-height: 260px;
    overflow-y: auto;
    margin: 0.75rem 0;
    padding: 0.25rem;
  }

  .bubble {
    padding: 0.6rem 0.75rem;
    border-radius: 8px;
    max-width: 95%;
  }

  .bubble.user {
    align-self: flex-end;
    background: rgba(80, 180, 120, 0.18);
  }

  .bubble.banker {
    align-self: flex-start;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
  }

  .who {
    display: block;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    opacity: 0.6;
    margin-bottom: 0.25rem;
  }

  .bubble p {
    margin: 0;
    white-space: pre-wrap;
    font-size: 0.92rem;
    line-height: 1.45;
  }

  .suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.75rem;
  }

  .suggestions button {
    font-size: 0.78rem;
    padding: 0.35rem 0.55rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: transparent;
    cursor: pointer;
    color: inherit;
  }

  .suggestions button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .chat-input {
    display: flex;
    gap: 0.5rem;
  }

  .chat-input input {
    flex: 1;
    padding: 0.5rem 0.65rem;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: inherit;
  }

  .chat-input .primary {
    padding: 0.5rem 0.9rem;
    border-radius: 6px;
    border: none;
    background: #3a9e5f;
    color: #fff;
    cursor: pointer;
  }

  .chat-input .primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
