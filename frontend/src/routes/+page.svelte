<script lang="ts">
  const workflows = [
    'Item database',
    'QR assignment',
    'Availability checks',
    'Checkout and return',
    'Event history'
  ];
</script>

<svelte:head>
  <title>Inventory Booking</title>
  <meta
    name="description"
    content="Internal inventory and equipment booking system for QR-based checkout workflows."
  />
</svelte:head>

<main class="shell">
  <section class="hero" aria-labelledby="page-title">
    <p class="eyebrow">Operational inventory system</p>
    <h1 id="page-title">Know where every item is before the next booking starts.</h1>
    <p class="intro">
      This app will manage items, locations, QR labels, reservations, checkouts, returns,
      maintenance, and audit history from a PostgreSQL-backed source of truth.
    </p>
    <div class="actions">
      <a href="http://127.0.0.1:8000/health">Check API health</a>
    </div>
  </section>

  <section class="panel" aria-labelledby="workflow-title">
    <h2 id="workflow-title">Initial workflow scope</h2>
    <ul>
      {#each workflows as workflow}
        <li>{workflow}</li>
      {/each}
    </ul>
  </section>
</main>

<style>
  .shell {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(18rem, 0.6fr);
    gap: clamp(1rem, 4vw, 3rem);
    width: min(1120px, calc(100% - 2rem));
    margin: 0 auto;
    padding: clamp(2rem, 8vw, 6rem) 0;
  }

  .hero,
  .panel {
    border: 1px solid rgba(20, 33, 28, 0.12);
    border-radius: 28px;
    background: rgba(255, 252, 242, 0.78);
    box-shadow: 0 24px 80px rgba(42, 68, 51, 0.14);
    backdrop-filter: blur(18px);
  }

  .hero {
    padding: clamp(2rem, 5vw, 4.5rem);
  }

  .panel {
    align-self: start;
    padding: clamp(1.5rem, 4vw, 2.5rem);
  }

  .eyebrow {
    margin: 0 0 1rem;
    color: #5b6f4b;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  h1,
  h2,
  p {
    margin-top: 0;
  }

  h1 {
    max-width: 13ch;
    margin-bottom: 1.25rem;
    color: #14211c;
    font-size: clamp(3rem, 8vw, 6.8rem);
    line-height: 0.88;
    letter-spacing: -0.07em;
  }

  h2 {
    margin-bottom: 1rem;
    font-size: clamp(1.35rem, 3vw, 2rem);
    letter-spacing: -0.04em;
  }

  .intro {
    max-width: 48rem;
    color: #34463e;
    font-size: clamp(1.05rem, 2vw, 1.3rem);
    line-height: 1.55;
  }

  .actions {
    margin-top: 2rem;
  }

  a {
    display: inline-flex;
    align-items: center;
    min-height: 2.75rem;
    padding: 0 1.1rem;
    border-radius: 999px;
    color: #fffaf0;
    background: #254c37;
    font-weight: 700;
    text-decoration: none;
  }

  ul {
    display: grid;
    gap: 0.75rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  li {
    padding: 0.85rem 1rem;
    border-radius: 18px;
    background: rgba(37, 76, 55, 0.08);
    color: #24372f;
    font-weight: 650;
  }

  @media (max-width: 800px) {
    .shell {
      grid-template-columns: 1fr;
    }

    h1 {
      max-width: 11ch;
    }
  }
</style>
