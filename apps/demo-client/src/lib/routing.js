/** @returns {string} */
export function getRoute() {
  const hash = window.location.hash.replace(/^#/, '');
  return hash || '/';
}

/** @param {(route: string) => void} listener */
export function onRouteChange(listener) {
  const handler = () => listener(getRoute());
  window.addEventListener('hashchange', handler);
  handler();
  return () => window.removeEventListener('hashchange', handler);
}

/** @param {string} path */
export function navigate(path) {
  window.location.hash = path.startsWith('/') ? path : `/${path}`;
}
