<script>
  /** @typedef {{ id: number, title: string, message: string, detail?: string, variant?: string }} Toast */

  let toasts = $state(/** @type {Toast[]} */ ([]));
  let nextId = 0;

  /** @param {CustomEvent} event */
  function onFeedback(event) {
    const detail = event.detail;
    if (!detail?.message && !detail?.title) return;

    const id = ++nextId;
    toasts = [
      {
        id,
        title: detail.title ?? 'Update',
        message: detail.message ?? '',
        detail: detail.detail,
        variant: detail.variant ?? 'info',
      },
      ...toasts,
    ].slice(0, 5);

    setTimeout(() => {
      toasts = toasts.filter((t) => t.id !== id);
    }, 9000);
  }

  $effect(() => {
    window.addEventListener('starfall-game-feedback', onFeedback);
    return () => window.removeEventListener('starfall-game-feedback', onFeedback);
  });
</script>

{#if toasts.length}
  <div class="feedback-stack" aria-live="polite">
    {#each toasts as toast (toast.id)}
      <article class="toast {toast.variant}">
        <strong>{toast.title}</strong>
        <p>{toast.message}</p>
        {#if toast.detail}
          <p class="detail">{toast.detail}</p>
        {/if}
      </article>
    {/each}
  </div>
{/if}

<style>
  .feedback-stack {
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    width: min(360px, calc(100vw - 2rem));
    pointer-events: none;
  }

  .toast {
    pointer-events: auto;
    padding: 0.85rem 1rem;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: rgba(12, 20, 36, 0.96);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
    animation: slide-in 0.25s ease-out;
  }

  .toast p {
    margin: 0.25rem 0 0;
    font-size: 0.88rem;
    color: var(--text);
  }

  .toast strong {
    font-size: 0.92rem;
  }

  .detail {
    margin-top: 0.35rem !important;
    font-size: 0.8rem !important;
    color: var(--text-muted) !important;
  }

  .toast.success {
    border-color: rgba(94, 230, 154, 0.35);
    background: linear-gradient(135deg, rgba(16, 40, 32, 0.98), rgba(12, 20, 36, 0.98));
  }

  .toast.success strong {
    color: var(--success);
  }

  .toast.warning {
    border-color: rgba(240, 192, 96, 0.35);
    background: linear-gradient(135deg, rgba(40, 32, 16, 0.98), rgba(12, 20, 36, 0.98));
  }

  .toast.warning strong {
    color: var(--gold);
  }

  .toast.danger {
    border-color: rgba(255, 107, 129, 0.35);
  }

  .toast.danger strong {
    color: var(--danger);
  }

  .toast.info strong {
    color: var(--accent);
  }

  @keyframes slide-in {
    from {
      opacity: 0;
      transform: translateX(12px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }
</style>
