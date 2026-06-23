<script>
  import { createClient, getStoredToken } from './api.js';

  let { apiBase } = $props();

  let token = $state(getStoredToken());
  let client = $derived(createClient(apiBase, token || undefined));
  let world = $state(null);
  let player = $state(null);
  let leaderboard = $state([]);
  let lastReward = $state(null);
  let error = $state(null);
  let loading = $state(false);

  async function refresh() {
    loading = true;
    error = null;
    try {
      world = await client.gameWorld();
      leaderboard = await client.gameLeaderboard();
      if (token) {
        player = await client.gameMe();
      } else {
        player = null;
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    token = getStoredToken();
    refresh();
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  });

  window.addEventListener('starfall-auth-changed', () => {
    token = getStoredToken();
    refresh();
  });

  window.addEventListener('starfall-game-reward', (event) => {
    lastReward = event.detail;
    refresh();
  });
</script>

<section class="game-hud">
  <header class="hud-header">
    <div>
      <p class="eyebrow">Online game</p>
      <h2>Starfall Trader League</h2>
      <p class="tagline">Trade, assemble cargo, complete missions, and climb the galactic leaderboard.</p>
    </div>
    {#if world}
      <div class="world-strip">
        <span class="badge info">Cycle {world.market_cycle}</span>
        <span class="muted">{world.online_players} traders online</span>
      </div>
    {/if}
  </header>

  {#if world?.event_message}
    <div class="event-banner">{world.event_message}</div>
  {/if}

  {#if error}
    <div class="error-box">{error}</div>
  {/if}

  {#if lastReward}
    <div class="reward-banner">
      Earned {lastReward.credits_earned ?? 0} cr · +{lastReward.xp_gained ?? 0} XP
      {#if lastReward.mission_rewards?.length}
        · Mission complete: {lastReward.mission_rewards.map((m) => m.title).join(', ')}
      {/if}
    </div>
  {/if}

  <div class="hud-grid">
    <div class="hud-panel">
      <h3>Your captain</h3>
      {#if !token}
        <p class="muted">Sign in via Marketplace to earn credits, XP, and mission rewards.</p>
      {:else if player}
        <div class="stats">
          <div><span class="label">Name</span><strong>{player.player.display_name}</strong></div>
          <div><span class="label">Credits</span><strong class="gold">{player.player.credits} cr</strong></div>
          <div><span class="label">Level</span><strong>{player.player.level}</strong></div>
          <div><span class="label">XP</span><strong>{player.player.xp}</strong></div>
          <div><span class="label">Reputation</span><strong>{player.player.reputation}</strong></div>
          <div><span class="label">Orders</span><strong>{player.player.orders_completed}</strong></div>
        </div>
        <div class="xp-bar">
          <div
            class="xp-fill"
            style={`width: ${100 - (player.player.xp_to_next_level / 500) * 100}%`}
          ></div>
        </div>
        <p class="meta">{player.player.xp_to_next_level} XP to next level</p>
      {:else if loading}
        <p class="muted">Loading profile…</p>
      {/if}
    </div>

    <div class="hud-panel">
      <h3>Missions</h3>
      {#if !token}
        <p class="muted">Missions unlock after sign-in.</p>
      {:else if player?.missions?.length}
        <ul class="mission-list">
          {#each player.missions as mission}
            <li class:done={mission.completed}>
              <div class="mission-top">
                <strong>{mission.title}</strong>
                {#if mission.completed}
                  <span class="badge ok">Done</span>
                {:else}
                  <span class="badge warn">{mission.progress}/{mission.target_quantity}</span>
                {/if}
              </div>
              <p>{mission.description}</p>
              <p class="meta">Reward: {mission.reward_credits} cr · {mission.reward_xp} XP</p>
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    <div class="hud-panel">
      <h3>Leaderboard</h3>
      {#if leaderboard.length === 0}
        <p class="muted">No rankings yet.</p>
      {:else}
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Trader</th>
              <th>Lvl</th>
              <th>Rep</th>
              <th>Credits</th>
            </tr>
          </thead>
          <tbody>
            {#each leaderboard as row}
              <tr>
                <td>{row.rank}</td>
                <td>{row.display_name}</td>
                <td>{row.level}</td>
                <td>{row.reputation}</td>
                <td>{row.credits}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  </div>
</section>

<style>
  .game-hud {
    grid-area: game;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: linear-gradient(135deg, #101828 0%, #0c1424 100%);
    padding: 1.25rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .hud-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .eyebrow {
    margin: 0;
    color: var(--gold);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 600;
  }

  h2 {
    margin: 0.15rem 0 0;
    font-size: 1.5rem;
  }

  .tagline {
    margin: 0.35rem 0 0;
    color: var(--text-muted);
    max-width: 60ch;
  }

  .world-strip {
    display: flex;
    gap: 0.65rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .event-banner {
    padding: 0.65rem 0.85rem;
    border-radius: 10px;
    background: rgba(240, 192, 96, 0.08);
    border: 1px solid rgba(240, 192, 96, 0.25);
    color: var(--gold);
    font-size: 0.9rem;
  }

  .reward-banner {
    padding: 0.65rem 0.85rem;
    border-radius: 10px;
    background: rgba(94, 230, 154, 0.08);
    border: 1px solid rgba(94, 230, 154, 0.25);
    color: var(--success);
    font-size: 0.9rem;
  }

  .hud-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1rem;
  }

  .hud-panel {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
  }

  .hud-panel h3 {
    margin: 0 0 0.75rem;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.65rem;
  }

  .label {
    display: block;
    font-size: 0.72rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .gold {
    color: var(--gold);
  }

  .xp-bar {
    margin-top: 0.85rem;
    height: 8px;
    background: var(--bg-deep);
    border-radius: 999px;
    overflow: hidden;
  }

  .xp-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-dim), var(--accent));
  }

  .meta {
    margin: 0.35rem 0 0;
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .mission-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .mission-list li {
    padding: 0.65rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--bg-deep);
  }

  .mission-list li.done {
    opacity: 0.75;
  }

  .mission-top {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.25rem;
  }

  .mission-list p {
    margin: 0.15rem 0 0;
    font-size: 0.85rem;
  }

  .muted {
    color: var(--text-muted);
  }
</style>
