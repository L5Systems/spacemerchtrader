<script>
  import { createClient, SYSTEMS } from './lib/api.js';
  import Panel from './lib/Panel.svelte';
  import ResultView from './lib/ResultView.svelte';

  let apiBase = $state('/api');
  let client = $derived(createClient(apiBase));

  let health = $state(null);
  let healthError = $state(null);
  let healthLoading = $state(false);

  let marketSystem = $state('sol');
  let marketData = $state(null);
  let marketError = $state(null);
  let marketLoading = $state(false);

  let routeOrigin = $state('sol');
  let routeDest = $state('vega');
  let routeQty = $state(10);
  let routeData = $state(null);
  let routeError = $state(null);
  let routeLoading = $state(false);

  let warehouseId = $state('wh-sol-dock');
  let stockData = $state(null);
  let stockError = $state(null);
  let stockLoading = $state(false);

  let orderForm = $state({
    client_id: 'trader-aurora-7',
    order_type: 'sell',
    product_id: 'alloy',
    quantity: 10,
    origin_system_id: 'sol',
    destination_system_id: 'vega',
  });
  let orderData = $state(null);
  let orderError = $state(null);
  let orderLoading = $state(false);
  let shipmentData = $state(null);
  let shipmentError = $state(null);

  let lookupOrderId = $state('');
  let lookupOrder = $state(null);
  let lookupError = $state(null);
  let lookupLoading = $state(false);

  let agents = $state(null);
  let agentsError = $state(null);
  let agentsLoading = $state(false);
  let agentRun = $state(null);
  let agentRunError = $state(null);
  let selectedAgent = $state('pricing');
  let agentOrderId = $state('');

  let activity = $state([]);

  /** @param {string} label @param {() => Promise<any>} fn */
  async function run(label, fn) {
    const entry = { label, time: new Date().toLocaleTimeString(), ok: true, msg: '' };
    try {
      const result = await fn();
      entry.msg = 'OK';
      activity = [entry, ...activity].slice(0, 12);
      return result;
    } catch (err) {
      entry.ok = false;
      entry.msg = err instanceof Error ? err.message : String(err);
      activity = [entry, ...activity].slice(0, 12);
      throw err;
    }
  }

  async function checkHealth() {
    healthLoading = true;
    healthError = null;
    try {
      health = await run('GET /health', () => client.health());
    } catch (e) {
      healthError = e.message;
      health = null;
    } finally {
      healthLoading = false;
    }
  }

  async function fetchMarket() {
    marketLoading = true;
    marketError = null;
    try {
      marketData = await run(`GET /markets/${marketSystem}/prices`, () =>
        client.marketPrices(marketSystem),
      );
    } catch (e) {
      marketError = e.message;
      marketData = null;
    } finally {
      marketLoading = false;
    }
  }

  async function fetchRoute() {
    routeLoading = true;
    routeError = null;
    try {
      routeData = await run('GET /routes/quote', () =>
        client.routeQuote(routeOrigin, routeDest, routeQty),
      );
    } catch (e) {
      routeError = e.message;
      routeData = null;
    } finally {
      routeLoading = false;
    }
  }

  async function fetchStock() {
    stockLoading = true;
    stockError = null;
    try {
      stockData = await run(`GET /warehouses/${warehouseId}/stock`, () =>
        client.warehouseStock(warehouseId),
      );
    } catch (e) {
      stockError = e.message;
      stockData = null;
    } finally {
      stockLoading = false;
    }
  }

  async function submitOrder() {
    orderLoading = true;
    orderError = null;
    shipmentData = null;
    shipmentError = null;
    try {
      orderData = await run('POST /orders', () => client.placeOrder(orderForm));
      lookupOrderId = orderData.id;
      try {
        shipmentData = await run('GET /orders/.../shipment', () =>
          client.getShipment(orderData.id),
        );
      } catch (e) {
        shipmentError = e.message;
      }
    } catch (e) {
      orderError = e.message;
      orderData = null;
    } finally {
      orderLoading = false;
    }
  }

  async function lookupOrderById() {
    if (!lookupOrderId.trim()) return;
    lookupLoading = true;
    lookupError = null;
    lookupOrder = null;
    shipmentData = null;
    shipmentError = null;
    try {
      lookupOrder = await run(`GET /orders/${lookupOrderId}`, () =>
        client.getOrder(lookupOrderId.trim()),
      );
      try {
        shipmentData = await run('GET /orders/.../shipment', () =>
          client.getShipment(lookupOrderId.trim()),
        );
      } catch (e) {
        shipmentError = e.message;
      }
    } catch (e) {
      lookupError = e.message;
    } finally {
      lookupLoading = false;
    }
  }

  async function fetchAgents() {
    agentsLoading = true;
    agentsError = null;
    try {
      agents = await run('GET /agents', () => client.listAgents());
      if (agents?.length && !agents.includes(selectedAgent)) {
        selectedAgent = agents[0];
      }
    } catch (e) {
      agentsError = e.message;
      agents = null;
    } finally {
      agentsLoading = false;
    }
  }

  async function triggerAgent() {
    agentRunError = null;
    const payload = agentOrderId.trim() ? { order_id: agentOrderId.trim() } : {};
    try {
      agentRun = await run(`POST /agents/${selectedAgent}/run`, () =>
        client.runAgent(selectedAgent, 'manual', payload),
      );
    } catch (e) {
      agentRunError = e.message;
      agentRun = null;
    }
  }

  async function exerciseAll() {
    await checkHealth();
    await fetchMarket();
    await fetchRoute();
    await fetchStock();
    await fetchAgents();
    await submitOrder();
  }

  $effect(() => {
    checkHealth();
    fetchMarket();
    fetchAgents();
  });
</script>

<div class="app">
  <header class="hero">
    <div class="hero-text">
      <p class="eyebrow">Starfall Space Merchandise Handling Co.</p>
      <h1>Demo Client</h1>
      <p class="tagline">Svelte 5 console for exercising the Starfall API and handling agents.</p>
    </div>
    <div class="hero-controls">
      <div class="field api-field">
        <label for="api-base">API base URL</label>
        <input id="api-base" bind:value={apiBase} placeholder="/api" />
      </div>
      <button class="primary" onclick={exerciseAll}>Run full demo</button>
    </div>
    {#if health}
      <div class="health-strip">
        <span class="badge ok">{health.status}</span>
        <span>{health.company}</span>
      </div>
    {:else if healthError}
      <div class="error-box">{healthError}</div>
    {/if}
  </header>

  <main class="grid">
    <Panel title="Market Prices" subtitle="GET /markets/{system}/prices">
      {#snippet actions()}
        <button onclick={fetchMarket} disabled={marketLoading}>Refresh</button>
      {/snippet}
      {#snippet children()}
        <div class="row">
          <div class="field">
            <label for="market-system">System</label>
            <select id="market-system" bind:value={marketSystem}>
              {#each SYSTEMS as sys}
                <option value={sys.id}>{sys.name}</option>
              {/each}
            </select>
          </div>
        </div>
        {#if marketData}
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Buy</th>
                <th>Sell</th>
              </tr>
            </thead>
            <tbody>
              {#each marketData as row}
                <tr>
                  <td>{row.product_name}</td>
                  <td class="mono">{row.sku}</td>
                  <td>{row.buy_price} cr</td>
                  <td>{row.sell_price} cr</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <ResultView data={marketData} error={marketError} loading={marketLoading} />
        {/if}
      {/snippet}
    </Panel>

    <Panel title="Route Quote" subtitle="GET /routes/quote">
      {#snippet actions()}
        <button onclick={fetchRoute} disabled={routeLoading}>Quote</button>
      {/snippet}
      {#snippet children()}
        <div class="row three">
          <div class="field">
            <label for="route-origin">Origin</label>
            <select id="route-origin" bind:value={routeOrigin}>
              {#each SYSTEMS as sys}
                <option value={sys.id}>{sys.id}</option>
              {/each}
            </select>
          </div>
          <div class="field">
            <label for="route-dest">Destination</label>
            <select id="route-dest" bind:value={routeDest}>
              {#each SYSTEMS as sys}
                <option value={sys.id}>{sys.id}</option>
              {/each}
            </select>
          </div>
          <div class="field">
            <label for="route-qty">Quantity</label>
            <input id="route-qty" type="number" min="1" bind:value={routeQty} />
          </div>
        </div>
        <ResultView data={routeData} error={routeError} loading={routeLoading} />
      {/snippet}
    </Panel>

    <Panel title="Warehouse Stock" subtitle="GET /warehouses/{id}/stock">
      {#snippet actions()}
        <button onclick={fetchStock} disabled={stockLoading}>Load</button>
      {/snippet}
      {#snippet children()}
        <div class="field">
          <label for="warehouse">Warehouse</label>
          <select id="warehouse" bind:value={warehouseId}>
            <option value="wh-sol-dock">wh-sol-dock — Sol Orbital Dock</option>
            <option value="wh-vega-hub">wh-vega-hub — Vega Trade Hub</option>
            <option value="wh-kepler-yard">wh-kepler-yard — Kepler Rim Yard</option>
          </select>
        </div>
        {#if stockData?.items}
          <p class="meta">{stockData.warehouse_name} · {stockData.station}</p>
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Qty</th>
                <th>Reserved</th>
                <th>Available</th>
              </tr>
            </thead>
            <tbody>
              {#each stockData.items as item}
                <tr>
                  <td>{item.product_name}</td>
                  <td>{item.quantity}</td>
                  <td>{item.reserved}</td>
                  <td>{item.available}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <ResultView data={stockData} error={stockError} loading={stockLoading} />
        {/if}
      {/snippet}
    </Panel>

    <Panel title="Place Order" subtitle="POST /orders — triggers pricing → inventory → routing">
      {#snippet actions()}
        <button class="primary" onclick={submitOrder} disabled={orderLoading}>Submit</button>
      {/snippet}
      {#snippet children()}
        <div class="row two">
          <div class="field">
            <label for="client-id">Client ID</label>
            <input id="client-id" bind:value={orderForm.client_id} />
          </div>
          <div class="field">
            <label for="order-type">Type</label>
            <select id="order-type" bind:value={orderForm.order_type}>
              <option value="sell">sell</option>
              <option value="buy">buy</option>
            </select>
          </div>
        </div>
        <div class="row three">
          <div class="field">
            <label for="product">Product</label>
            <select id="product" bind:value={orderForm.product_id}>
              <option value="hydro">hydro</option>
              <option value="alloy">alloy</option>
              <option value="spice">spice</option>
            </select>
          </div>
          <div class="field">
            <label for="qty">Quantity</label>
            <input id="qty" type="number" min="1" bind:value={orderForm.quantity} />
          </div>
          <div class="field">
            <label for="origin">Origin system</label>
            <select id="origin" bind:value={orderForm.origin_system_id}>
              {#each SYSTEMS as sys}
                <option value={sys.id}>{sys.id}</option>
              {/each}
            </select>
          </div>
        </div>
        <div class="field">
          <label for="dest">Destination system</label>
          <select id="dest" bind:value={orderForm.destination_system_id}>
            {#each SYSTEMS as sys}
              <option value={sys.id}>{sys.id}</option>
            {/each}
          </select>
        </div>
        {#if orderData}
          <div class="summary">
            <span class="badge info">{orderData.status}</span>
            <span class="mono">{orderData.id}</span>
            {#if orderData.total_credits}
              <strong>{orderData.total_credits} credits</strong>
            {/if}
          </div>
        {/if}
        <ResultView data={orderData} error={orderError} loading={orderLoading} />
        {#if shipmentData}
          <p class="meta">Shipment</p>
          <ResultView data={shipmentData} error={shipmentError} />
        {:else if shipmentError}
          <ResultView data={null} error={shipmentError} />
        {/if}
      {/snippet}
    </Panel>

    <Panel title="Order Lookup" subtitle="GET /orders/{id} and /shipment">
      {#snippet actions()}
        <button onclick={lookupOrderById} disabled={lookupLoading}>Lookup</button>
      {/snippet}
      {#snippet children()}
        <div class="field">
          <label for="lookup-id">Order ID</label>
          <input id="lookup-id" bind:value={lookupOrderId} placeholder="uuid from placed order" />
        </div>
        <ResultView data={lookupOrder} error={lookupError} loading={lookupLoading} />
        {#if shipmentData && lookupOrder}
          <p class="meta">Shipment</p>
          <ResultView data={shipmentData} error={shipmentError} />
        {/if}
      {/snippet}
    </Panel>

    <Panel title="Handling Agents" subtitle="GET /agents · POST /agents/{id}/run">
      {#snippet actions()}
        <button onclick={fetchAgents} disabled={agentsLoading}>List</button>
        <button class="primary" onclick={triggerAgent}>Run agent</button>
      {/snippet}
      {#snippet children()}
        <div class="row two">
          <div class="field">
            <label for="agent">Agent</label>
            <select id="agent" bind:value={selectedAgent}>
              {#if agents}
                {#each agents as agent}
                  <option value={agent}>{agent}</option>
                {/each}
              {:else}
                <option value="pricing">pricing</option>
                <option value="inventory">inventory</option>
                <option value="routing">routing</option>
              {/if}
            </select>
          </div>
          <div class="field">
            <label for="agent-order">Order ID (optional)</label>
            <input id="agent-order" bind:value={agentOrderId} placeholder="for manual re-run" />
          </div>
        </div>
        {#if agents}
          <p class="meta">Available: {agents.join(', ')}</p>
        {/if}
        <ResultView data={agentRun} error={agentRunError || agentsError} loading={agentsLoading} />
      {/snippet}
    </Panel>
  </main>

  <aside class="activity">
    <h3>Activity log</h3>
    {#if activity.length === 0}
      <p class="muted">Requests will appear here.</p>
    {:else}
      <ul>
        {#each activity as item}
          <li class:fail={!item.ok}>
            <span class="time">{item.time}</span>
            <span class="label">{item.label}</span>
            <span class="msg">{item.msg}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </aside>
</div>

<style>
  .app {
    max-width: 1400px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 2rem;
    display: grid;
    gap: 1.25rem;
    grid-template-columns: 1fr 260px;
    grid-template-areas:
      'hero hero'
      'main activity';
  }

  .hero {
    grid-area: hero;
    padding: 1.25rem 1.5rem;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: linear-gradient(135deg, #0c1424 0%, #101a2e 100%);
    display: grid;
    gap: 1rem;
  }

  .eyebrow {
    margin: 0;
    color: var(--accent);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 600;
  }

  h1 {
    margin: 0.15rem 0 0;
    font-size: 1.75rem;
    font-weight: 700;
  }

  .tagline {
    margin: 0.35rem 0 0;
    color: var(--text-muted);
    max-width: 52ch;
  }

  .hero-controls {
    display: flex;
    gap: 0.75rem;
    align-items: flex-end;
    flex-wrap: wrap;
  }

  .api-field {
    min-width: 220px;
    flex: 1;
    max-width: 360px;
  }

  .health-strip {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .grid {
    grid-area: main;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 1rem;
    align-content: start;
  }

  .row {
    display: grid;
    gap: 0.65rem;
  }

  .row.two {
    grid-template-columns: 1fr 1fr;
  }

  .row.three {
    grid-template-columns: 1fr 1fr 100px;
  }

  .meta {
    margin: 0;
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .summary {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    font-size: 0.9rem;
  }

  .activity {
    grid-area: activity;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem;
    align-self: start;
    position: sticky;
    top: 1rem;
    max-height: calc(100vh - 2rem);
    overflow: auto;
  }

  .activity h3 {
    margin: 0 0 0.75rem;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .activity ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .activity li {
    font-size: 0.78rem;
    padding: 0.45rem 0.5rem;
    border-radius: 6px;
    background: var(--bg-deep);
    border: 1px solid var(--border);
    display: grid;
    gap: 0.1rem;
  }

  .activity li.fail {
    border-color: #5a2030;
    background: #1a0e12;
  }

  .time {
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.72rem;
  }

  .label {
    font-weight: 500;
  }

  .msg {
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.72rem;
  }

  .muted {
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  @media (max-width: 1100px) {
    .app {
      grid-template-columns: 1fr;
      grid-template-areas: 'hero' 'main' 'activity';
    }

    .activity {
      position: static;
      max-height: none;
    }
  }
</style>
