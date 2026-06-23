<script>
  import { createClient, getStoredToken, notifyGameReward } from './api.js';

  let { apiBase } = $props();

  let token = $state(getStoredToken());
  let client = $derived(createClient(apiBase, token || undefined));
  /** @type {Array<{ role: 'user' | 'guide', text: string }>} */
  let messages = $state([
    {
      role: 'guide',
      text: 'I am your Mission Guide. I generate company delivery contracts and score you step-by-step through container, packing, manifest, launch, customs, and final delivery. Say generate mission to start.',
    },
  ]);
  /** @type {string[]} */
  let suggestions = $state([
    'generate mission: 100kg mining welding gear to ElonsTown on Mars',
    'mission status',
    'help',
  ]);
  /** @type {{ score?: number, max_score?: number, contract_code?: string } | null} */
  let missionMeta = $state(null);
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
      const result = await client.missionGuideChat({ instruction });
      messages = [...messages, { role: 'guide', text: result.message }];
      suggestions = result.suggestions ?? [];
      if (result.data?.mission) {
        missionMeta = {
          contract_code: result.data.mission.contract_code,
          score: result.data.mission.score,
          max_score: result.data.mission.max_score,
        };
      }
      if (result.game_result) {
        notifyGameReward(result.game_result);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      messages = [
        ...messages,
        {
          role: 'guide',
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
    };
    window.addEventListener('starfall-auth-changed', onAuth);
    return () => window.removeEventListener('starfall-auth-changed', onAuth);
  });
</script>

<section class="mission-guide">
  <header>
    <p class="eyebrow">Mission Guide</p>
    <h3>Guided delivery contracts</h3>
    <p class="meta">
      Receive company requests, report each logistics step, and earn a score — lose points for
      skipped customs forms or vague answers.
    </p>
    {#if missionMeta?.contract_code}
      <p class="score-pill">
        {missionMeta.contract_code} · score {missionMeta.score ?? 0}/{missionMeta.max_score ?? 100}
      </p>
    {/if}
  </header>

  {#if !token}
    <p class="muted">Sign in via Marketplace to play guided missions.</p>
  {/if}

  {#if error}
    <div class="error-box">{error}</div>
  {/if}

  <div class="chat-log">
    {#each messages as msg, index (index)}
      <article class="bubble {msg.role}">
        <span class="who">{msg.role === 'guide' ? 'Guide' : 'You'}</span>
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
      placeholder={token ? 'Report progress or ask for a new contract…' : 'Sign in to chat with the guide'}
      disabled={loading || !token}
    />
    <button type="submit" class="primary" disabled={loading || !token || !input.trim()}>
      {loading ? 'Thinking…' : 'Send'}
    </button>
  </form>
</section>

<style>
  .mission-guide {
    margin-top: 1rem;
    padding: 1rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--panel);
  }

  header .eyebrow {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.7;
    margin: 0;
  }

  header h3 {
    margin: 0.25rem 0;
  }

  .meta {
    margin: 0.25rem 0 0.5rem;
    font-size: 0.9rem;
    opacity: 0.85;
  }

  .score-pill {
    display: inline-block;
    margin: 0;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    background: rgba(100, 180, 255, 0.15);
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
    max-height: 280px;
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
    background: rgba(80, 140, 255, 0.18);
  }

  .bubble.guide {
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
    background: #4a8cff;
    color: #fff;
    cursor: pointer;
  }

  .chat-input .primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
