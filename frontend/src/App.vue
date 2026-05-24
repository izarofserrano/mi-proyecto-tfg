<template>
  <div id="layout">
    <header>
      <nav>
        <RouterLink to="/" class="brand">Fuzhify</RouterLink>
        <span class="tagline">Generación automática de resúmenes sobre series temporales</span>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
  color: #1a1a2e;
  min-height: 100vh;
}

#layout { display: flex; flex-direction: column; min-height: 100vh; }

header {
  background: #1a1a2e;
  color: #fff;
  padding: 0 2rem;
  height: 56px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0,0,0,.25);
}

nav { display: flex; align-items: baseline; gap: 1rem; }

.brand {
  font-size: 1.1rem;
  font-weight: 700;
  color: #7ec8e3;
  text-decoration: none;
  letter-spacing: .02em;
}
.brand:hover { color: #a8ddef; }

.tagline { font-size: .8rem; color: #8a9bb5; }

main { flex: 1; padding: 2rem; max-width: 1200px; margin: 0 auto; width: 100%; }

/* Shared card */
.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,.08);
  padding: 2rem;
}

/* Shared button */
.btn {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  padding: .6rem 1.4rem;
  border-radius: 8px;
  border: none;
  font-size: .95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s, transform .1s;
}
.btn:active { transform: scale(.97); }
.btn-primary  { background: #2563eb; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-primary:disabled { background: #93c5fd; cursor: not-allowed; }
.btn-secondary { background: #e5e7eb; color: #374151; }
.btn-secondary:hover { background: #d1d5db; }
.btn-success   { background: #059669; color: #fff; }
.btn-success:hover { background: #047857; }
</style>
