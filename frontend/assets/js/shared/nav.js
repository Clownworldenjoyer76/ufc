(() => {
  const el = document.getElementById("nav-placeholder");
  if (!el) return;

  // Shared league selector used by Stats pages.
  // The component watches #league-controls, so it can load before the
  // page-specific renderer creates its league pills.
  const currentPage = (
    location.pathname.split('/').pop() || ''
  ).replace('.html', '').toLowerCase();

  if (['teams', 'players', 'standings'].includes(currentPage)) {
    const sharedLeagueNav = document.createElement('script');
    sharedLeagueNav.src = 'assets/js/shared/league_nav.js';
    sharedLeagueNav.defer = true;
    document.head.appendChild(sharedLeagueNav);
  }

  fetch("nav.html")
    .then(r => {
      if (!r.ok) throw new Error("nav.html not found");
      return r.text();
    })
    .then(html => {
      el.innerHTML = html;

      // Active state
      const page = location.pathname.split('/').pop().replace('.html', '') || 'index';
      el.querySelectorAll('a[data-page]').forEach(a => {
        if (a.dataset.page === page) {
          a.classList.add('active');
          const parent = a.closest('.nav-dropdown');
          if (parent) parent.querySelector('.nav-dropdown-toggle').classList.add('active');
        }
      });

      // Clock
      const tzSel   = document.getElementById('tz-select');
      const clockEl = document.getElementById('live-clock');
      tzSel.value = localStorage.getItem('edgelytics_tz') || 'America/New_York';

      function tick() {
        const tz    = tzSel.value;
        const label = tzSel.options[tzSel.selectedIndex].text;
        const now   = new Date();
        const t = now.toLocaleTimeString('en-US', { timeZone: tz, hour12: true });
        const d = now.toLocaleDateString('en-US', { timeZone: tz, weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
        clockEl.textContent = `${label}  ${t}   ${d}`;
      }

      tzSel.addEventListener('change', () => {
        localStorage.setItem('edgelytics_tz', tzSel.value);
        tick();
      });

      tick();
      setInterval(tick, 1000);

      // Ticker
      initTicker();
    })
    .catch(() => { el.innerHTML = ""; });

  // ── TICKER ──────────────────────────────────────────────────────────────

  const CACHE_TTL = 5 * 60 * 1000;

  function cacheGet(key) {
    try {
      var raw = sessionStorage.getItem(key);
      if (!raw) return null;
      var obj = JSON.parse(raw);
      if (Date.now() - obj.ts > CACHE_TTL) { sessionStorage.removeItem(key); return null; }
      return obj.data;
    } catch(e) { return null; }
  }

  function cacheSet(key, data) {
    try { sessionStorage.setItem(key, JSON.stringify({ ts: Date.now(), data: data })); } catch(e) {}
  }

  async function fetchCached(key, url) {
    var cached = cacheGet(key);
    if (cached) return cached;
    try {
      var r = await fetch(url);
      if (!r.ok) return null;
      var data = await r.json();
      cacheSet(key, data);
      return data;
    } catch(e) { return null; }
  }

  function padTwo(n) { return n < 10 ? '0' + n : '' + n; }

  function todayESPN() {
    var d = new Date();
    return '' + d.getFullYear() + padTwo(d.getMonth() + 1) + padTwo(d.getDate());
  }

  var LEAGUES = [
    { key: 'NHL', sport: 'hockey',     league: 'nhl' },
    { key: 'NBA', sport: 'basketball', league: 'nba' },
    { key: 'MLB', sport: 'baseball',   league: 'mlb' }
  ];

  async function fetchGames() {
    var items = [];
    await Promise.all(LEAGUES.map(async function(cfg) {
      var url  = 'https://site.api.espn.com/apis/site/v2/sports/' + cfg.sport + '/' + cfg.league + '/scoreboard?dates=' + todayESPN();
      var data = await fetchCached('ticker_games_' + cfg.key, url);
      if (!data || !data.events) return;
      data.events.forEach(function(ev) {
        var comps = ev.competitions && ev.competitions[0];
        if (!comps) return;
        var competitors = comps.competitors || [];
        var home = competitors.find(function(c) { return c.homeAway === 'home'; });
        var away = competitors.find(function(c) { return c.homeAway === 'away'; });
        if (!home || !away) return;
        var status   = ev.status && ev.status.type ? ev.status.type.shortDetail || ev.status.type.description : '';
        var homeAbbr = home.team ? (home.team.abbreviation || home.team.shortDisplayName || '') : '';
        var awayAbbr = away.team ? (away.team.abbreviation || away.team.shortDisplayName || '') : '';
        var score    = (ev.status && ev.status.type && ev.status.type.completed)
          ? away.score + '-' + home.score
          : status;
        items.push('[' + cfg.key + '] ' + awayAbbr + ' @ ' + homeAbbr + '  ' + score);
      });
    }));
    return items;
  }

  async function fetchInjuries() {
    var items = [];
    await Promise.all(LEAGUES.map(async function(cfg) {
      var url  = 'https://site.api.espn.com/apis/site/v2/sports/' + cfg.sport + '/' + cfg.league + '/injuries';
      var data = await fetchCached('ticker_injuries_' + cfg.key, url);
      if (!data || !data.injuries) return;
      data.injuries.forEach(function(group) {
        var team = group.displayName || '';
        (group.injuries || []).forEach(function(inj) {
          var player = inj.athlete ? (inj.athlete.displayName || '') : '';
          var status = inj.status || '';
          if (player && (status.toLowerCase() === 'out' || status.toLowerCase() === 'doubtful')) {
            items.push('[INJ] ' + team + ' — ' + player + ' (' + status + ')');
          }
        });
      });
    }));
    return items;
  }

  async function fetchTransactions() {
    var items = [];
    await Promise.all(LEAGUES.map(async function(cfg) {
      var url  = 'https://site.api.espn.com/apis/site/v2/sports/' + cfg.sport + '/' + cfg.league + '/transactions';
      var data = await fetchCached('ticker_txns_' + cfg.key, url);
      if (!data || !data.transactions) return;
      data.transactions.slice(0, 5).forEach(function(t) {
        var team = t.team ? (t.team.abbreviation || t.team.displayName || '') : '';
        var desc = t.description || '';
        if (desc) items.push('[TXN] ' + (team ? team + ': ' : '') + desc);
      });
    }));
    return items;
  }

  function injectTickerStyle() {
    if (document.getElementById('ticker-style')) return;
    var s = document.createElement('style');
    s.id = 'ticker-style';
    s.textContent = [
      '.ticker-wrap{overflow:hidden;border-bottom:1px solid #222;background:#0d0d0d;height:28px;display:flex;align-items:center;}',
      '.ticker-label{font-family:"Barlow Condensed",sans-serif;font-size:11px;font-weight:900;letter-spacing:0.12em;color:#0a0a0a;background:#00ff84;padding:0 10px;height:100%;display:flex;align-items:center;white-space:nowrap;flex-shrink:0;}',
      '.ticker-track{display:flex;align-items:center;overflow:hidden;flex:1;}',
      '.ticker-inner{display:flex;align-items:center;white-space:nowrap;animation:ticker-scroll 850s linear infinite;}',
      '.ticker-inner:hover{animation-play-state:paused;}',
      '.ticker-item{font-family:"IBM Plex Mono",monospace;font-size:11px;color:#888;padding:0 32px;border-right:1px solid #222;}',
      '.ti-tag{font-family:"Barlow Condensed",sans-serif;font-weight:700;letter-spacing:0.08em;margin-right:6px;}',
      '.ti-tag-game{color:#00bfff;}',
      '.ti-tag-inj{color:#ff4444;}',
      '.ti-tag-txn{color:#facc15;}',
      '.ti-body{color:#aaa;}',
      '@keyframes ticker-scroll{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}'
    ].join('');
    document.head.appendChild(s);
  }

  function buildTickerItem(raw) {
    var match = raw.match(/^\[([^\]]+)\]\s*(.*)/);
    if (!match) return '<span class="ticker-item"><span class="ti-body">' + raw + '</span></span>';
    var tag  = match[1];
    var body = match[2];
    var tagClass = tag === 'INJ' ? 'ti-tag-inj' : tag === 'TXN' ? 'ti-tag-txn' : 'ti-tag-game';
    return '<span class="ticker-item"><span class="ti-tag ' + tagClass + '">' + tag + '</span><span class="ti-body">' + body + '</span></span>';
  }

  function renderTicker(items) {
    var existing = document.getElementById('site-ticker');
    if (existing) existing.remove();

    injectTickerStyle();

    var wrap = document.createElement('div');
    wrap.id = 'site-ticker';
    wrap.className = 'ticker-wrap';

    var label = document.createElement('div');
    label.className = 'ticker-label';
    label.textContent = 'LIVE';

    var track = document.createElement('div');
    track.className = 'ticker-track';

    var inner = document.createElement('div');
    inner.className = 'ticker-inner';
    var html = items.map(buildTickerItem).join('');
    inner.innerHTML = html + html; // duplicate for seamless loop

    track.appendChild(inner);
    wrap.appendChild(label);
    wrap.appendChild(track);

    var navEl = document.getElementById('nav-placeholder');
    if (navEl) navEl.insertAdjacentElement('afterend', wrap);
  }

  async function initTicker() {
    var [games, injuries, txns] = await Promise.all([
      fetchGames(),
      fetchInjuries(),
      fetchTransactions()
    ]);

    var items = games.concat(injuries).concat(txns);
    if (items.length === 0) items = ['No data available'];
    renderTicker(items);
  }

})();
