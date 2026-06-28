<script>
  import App from './App.svelte';
  import BankingPage from './BankingPage.svelte';
  import { getRoute, onRouteChange } from './lib/routing.js';

  let route = $state(getRoute());

  $effect(() => onRouteChange((next) => {
    route = next;
  }));
</script>

{#if route === '/banking'}
  <BankingPage />
{:else}
  <App />
{/if}
