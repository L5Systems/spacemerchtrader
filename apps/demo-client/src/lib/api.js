const DEFAULT_BASE = '/api';

/** @param {string} baseUrl */
export function createClient(baseUrl = DEFAULT_BASE) {
  const base = baseUrl.replace(/\/$/, '');

  /** @param {string} path @param {RequestInit} [init] */
  async function request(path, init = {}) {
    const res = await fetch(`${base}${path}`, {
      headers: { 'Content-Type': 'application/json', ...init.headers },
      ...init,
    });
    const text = await res.text();
    let body = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = text;
      }
    }
    if (!res.ok) {
      const detail = typeof body === 'object' && body?.detail ? body.detail : res.statusText;
      throw new Error(`${res.status}: ${detail}`);
    }
    return body;
  }

  return {
    health: () => request('/health'),
    marketPrices: (systemId) => request(`/markets/${systemId}/prices`),
    routeQuote: (origin, dest, qty = 1) =>
      request(`/routes/quote?origin=${origin}&dest=${dest}&qty=${qty}`),
    warehouseStock: (warehouseId) => request(`/warehouses/${warehouseId}/stock`),
    placeOrder: (order) =>
      request('/orders', { method: 'POST', body: JSON.stringify(order) }),
    getOrder: (orderId) => request(`/orders/${orderId}`),
    getShipment: (orderId) => request(`/orders/${orderId}/shipment`),
    listAgents: () => request('/agents'),
    runAgent: (agentId, trigger = 'manual', payload = {}) =>
      request(`/agents/${agentId}/run`, {
        method: 'POST',
        body: JSON.stringify({ trigger, payload }),
      }),
    getAgentRun: (runId) => request(`/agents/runs/${runId}`),
  };
}

export const api = createClient();

export const SYSTEMS = [
  { id: 'sol', name: 'Sol Expanse' },
  { id: 'vega', name: 'Vega Reach' },
  { id: 'kepler', name: 'Kepler Rim' },
];

export const PRODUCTS = [
  { id: 'hydro', name: 'Purified Ice Blocks' },
  { id: 'alloy', name: 'Titanium Alloy Ingots' },
  { id: 'spice', name: 'Nebula Spice Crates' },
];

export const WAREHOUSES = [
  { id: 'wh-sol-dock', name: 'Sol Orbital Dock', system: 'sol' },
  { id: 'wh-vega-hub', name: 'Vega Trade Hub', system: 'vega' },
  { id: 'wh-kepler-yard', name: 'Kepler Rim Yard', system: 'kepler' },
];
