/* Gym Tracker service worker.
   Bump CACHE when you change any file, so installed phones pick up the update. */
const CACHE = 'gym-tracker-v57';
const TOWN_MAPS = ['viridian','pewter','cerulean','vermilion','celadon','fuchsia','saffron','cinnabar','indigo'];
const HOENN_TOWN_MAPS = ['littleroot','rustboro','dewford','mauville','lavaridge','petalburg','fortree','mossdeep','sootopolis','evergrande'];
const ARENAS = ['gym','grass','water','cave','pond','ice','sand','poison','teal','psychic'];
/* The full Kanto 151 — every species is catchable (front + shiny + back + back-shiny). */
const MON_IDS = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151];
/* The Hoenn (Emerald) dex additions — the 155 species beyond the Kanto set (v6.0). */
const HOENN_IDS = [169,170,171,172,174,177,178,182,183,184,202,203,214,218,219,222,227,230,231,232,252,253,254,255,256,257,258,259,260,261,262,263,264,265,266,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,289,290,291,292,293,294,295,296,297,298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317,318,319,320,321,322,323,324,325,326,327,328,329,330,331,332,333,334,335,336,337,338,339,340,341,342,343,344,345,346,347,348,349,350,351,352,353,354,355,356,357,358,359,360,361,362,363,364,365,366,367,368,369,370,371,372,373,374,375,376,377,378,379,380,381,382,383,384,385,386];
const BOSS_IDS = [];
const WILD_IDS = [];
const TRAINERS = ['red','leaf','oak','brock','misty','ltsurge','erika','koga','sabrina','blaine','giovanni','lorelei','bruno','agatha','lance','blue',
  'bugcatcher','youngster','lass','hiker','fisherman','picnicker'];
const HOENN_TRAINERS = ['brendan','may','birch','steven','roxanne','brawly','wattson','flannery','norman','winona','tateliza','juan',
  'sidney','phoebe','glacia','drakeh','wallace','aromalady','camper','bugmaniac','blackbelt','birdkeeper','battlegirl','hexmaniac','dragontamer','hfisher','kindler',
  'archie','maxie','tabitha','shelly','matt','aquagrunt','magmagrunt',
  'anabel','tucker','spenser','greta','noland','lucy','brandon'];
const HOENN_BADGES = ['stone','knuckle','dynamo','heat','balance','feather','mind','rain'];
const ITEM_KEYS = ['potion','superpotion','hyperpotion','fullrestore','revive','pokeball','greatball','ultraball','luckyegg','hpup','protein','iron','calcium','zinc','carbos','rarecandy',
  'charcoal','mysticwater','magnet','blackbelt','twistedspoon','sharpbeak','hardstone','scopelens','leftovers','expshare',
  /* v6.4: berries + shoal goods (PokeAPI item sprites) */
  'cheriberry','chestoberry','pechaberry','rawstberry','aspearberry','figyberry','wikiberry','magoberry','aguavberry','iapapaberry',
  'shellbell','shoalsalt','shoalshell'];
const BADGE_TYPES = ['normal','fire','water','electric','grass','psychic','fighting','flying','poison','ground','rock','bug','ghost','ice','dragon','steel'];
const NPCS = ['nurse','lass','boy','oldman','man','youngster','chef','jiggly'];
const GYM_ROOMS = ['pewter','cerulean','vermilion','celadon','fuchsia','saffron','cinnabar','viridian','lorelei','bruno','agatha','lance','champion',
  'rustboro','dewford','mauville','lavaridge','petalburg','fortree','mossdeep','sootopolis','sidney','phoebe','glacia','drakeh','wallace'];
const ROAD_MAPS = ['forest','mtmoon','bridge','route8','hideout','silph','cycling','seafoam','victory',
  'h-woods','h-granite','h-coast','h-jagged','h-desert','h-jungle','h-sea','h-deep','h-victory'];
const POI_MAPS = ['tower','dept','corner','hideout','safari','silph','tower2','lab',
  'h-devon','h-corner','h-trick','h-dept','h-wx','h-pyre','h-magma','h-aqua','h-space','h-origin','h-sky','h-seafloor',
  'h-frontier','bf-tower','bf-dome','bf-palace','bf-arena','bf-factory','bf-pike','bf-pyramid',
  /* v6.4.1: official Gen-3 interiors for the Contest Hall + Shoal Cave */
  'h-hall','h-shoal','h-shoalice'];
/* Cries (sounds/cries/*.mp3) are NOT precached — the fetch handler caches them the first time they play. */
const ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-180.png',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './fonts/press-start-2p.woff2',
  './fonts/vt323.woff2'
]
  .concat(MON_IDS.map((i) => './sprites/' + i + '.png'))
  .concat(MON_IDS.map((i) => './sprites/shiny/' + i + '.png'))
  .concat(MON_IDS.map((i) => './sprites/back/' + i + '.png'))
  .concat(MON_IDS.map((i) => './sprites/back/shiny/' + i + '.png'))
  .concat(HOENN_IDS.map((i) => './sprites/' + i + '.png'))
  .concat(HOENN_IDS.map((i) => './sprites/shiny/' + i + '.png'))
  .concat(HOENN_IDS.map((i) => './sprites/back/' + i + '.png'))
  .concat(HOENN_IDS.map((i) => './sprites/back/shiny/' + i + '.png'))
  /* v6.4: the Gen-3 party menu icons — tiny, and every TEAM/BOX list uses them */
  .concat(MON_IDS.map((i) => './sprites/icons/' + i + '.png'))
  .concat(HOENN_IDS.map((i) => './sprites/icons/' + i + '.png'))
  .concat(HOENN_TRAINERS.map((t) => './sprites/trainers/' + t + '.png'))
  .concat(HOENN_BADGES.map((b) => './sprites/badges/h-' + b + '.png'))
  .concat(HOENN_TOWN_MAPS.map((t) => './map/hoenn/' + t + '.png'))
  .concat(BOSS_IDS.map((i) => './sprites/' + i + '.png'))
  .concat(WILD_IDS.map((i) => './sprites/' + i + '.png'))
  .concat(WILD_IDS.map((i) => './sprites/shiny/' + i + '.png'))
  .concat(TRAINERS.map((t) => './sprites/trainers/' + t + '.png'))
  .concat(ITEM_KEYS.map((k) => './sprites/items/' + k + '.png'))
  .concat(TOWN_MAPS.map((t) => './map/' + t + '.png'))
  .concat(ARENAS.map((a) => './sprites/arenas/' + a + '.png'))
  .concat(BADGE_TYPES.map((t) => './sprites/badges/' + t + '.png'))
  .concat(NPCS.map((n) => './sprites/npc/' + n + '.png'))
  .concat(GYM_ROOMS.map((g) => './map/gym/' + g + '.png'))
  .concat(ROAD_MAPS.map((r) => './map/road/' + r + '.png'))
  .concat(POI_MAPS.map((p) => './map/poi/' + p + '.png'))
  .concat(['./map/center.png', './map/mart.png', './map/kanto.png', './map/hoenn.png']);
/* Sugimori artwork (sprites/art/*.png) is NOT precached — the fetch handler caches each on first view. */

self.addEventListener('install', (e) => {
  // Add each asset individually so one missing file can't abort the whole install.
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => Promise.all(ASSETS.map((u) => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  // Pages: try network first (so updates arrive), fall back to cache when offline.
  // Only the app itself: other pages on the site (play.html) must not be cached as index.html.
  if (req.mode === 'navigate') {
    const path = new URL(req.url).pathname;
    if (!path.endsWith('/') && !path.endsWith('/index.html')) return;
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put('./index.html', copy));
          return res;
        })
        .catch(() => caches.match('./index.html'))
    );
    return;
  }

  // Everything else: cache first, then network.
  e.respondWith(
    caches.match(req).then(
      (hit) =>
        hit ||
        fetch(req).then((res) => {
          if (res.ok && new URL(req.url).origin === location.origin) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
    )
  );
});
