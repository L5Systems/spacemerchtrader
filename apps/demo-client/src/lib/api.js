const DEFAULT_BASE = '/api';
const TOKEN_KEY = 'starfall_marketplace_token';

/** @param {string} baseUrl @param {string} [token] */
export function createClient(baseUrl = DEFAULT_BASE, token) {
  const base = baseUrl.replace(/\/$/, '');

  /** @param {string} path @param {RequestInit} [init] */
  async function request(path, init = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    };
    const res = await fetch(`${base}${path}`, {
      ...init,
      headers,
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
    request,
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
    marketplaceCategories: () => request('/marketplace/categories'),
    marketplaceProviders: (category, systemId) => {
      const params = new URLSearchParams();
      if (category) params.set('category', category);
      if (systemId) params.set('system_id', systemId);
      const q = params.toString();
      return request(`/marketplace/providers${q ? `?${q}` : ''}`);
    },
    marketplaceSignup: (body) =>
      request('/marketplace/signup', { method: 'POST', body: JSON.stringify(body) }),
    marketplaceLogin: (body) =>
      request('/marketplace/login', { method: 'POST', body: JSON.stringify(body) }),
    marketplaceMe: () => request('/marketplace/me'),
    marketplaceMenu: () => request('/marketplace/menu'),
  };
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) ?? '';
}

export function storeToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export const TOKEN_STORAGE_KEY = TOKEN_KEY;

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
