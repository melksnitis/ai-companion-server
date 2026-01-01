import { DateTime } from 'luxon';

const baseDate = DateTime.fromISO('2025-12-31T08:00:00+02:00');

export const calendarWindow = {
  start: baseDate.toISODate(),
  end: baseDate.plus({ days: 7 }).toISODate(),
  nextEvent: {
    date: '2026-01-20',
    label: 'Vai Nio ir LV?',
    location: 'Rīga · EV meetup lab'
  }
};

export const calendarEvents = [
  {
    id: 'ideation-sprint',
    title: 'AI Companion Ideation Sprint',
    date: baseDate.plus({ days: 1, hours: 3 }).toISO(),
    location: 'Letta Lab · Hybrid',
    tags: ['strategy', 'brainstorm'],
    status: 'tentative',
    brief:
      'Fokuss uz personas-orientētu agentu iespējām. Mērķis: izveidot signālu karti, kas izcelt “must ship” eksperimentos pirms publiskās beta.'
  },
  {
    id: 'calendar-sync',
    title: 'Calendar Sync Debug Session',
    date: baseDate.plus({ days: 2, hours: 5 }).toISO(),
    location: 'Terminal TUI Room',
    tags: ['debug', 'infra'],
    status: 'confirmed',
    brief:
      'Komandas izsaukums, lai imitētu `search-events` un `list-events` rezultātu apvienošanu. Plānots salīdzināt Google Calendar un Todoist datu plūsmas.'
  },
  {
    id: 'worldnews-brief',
    title: 'World News Intelligence Brief',
    date: baseDate.plus({ days: 3, hours: 9 }).toISO(),
    location: 'Ops War Room',
    tags: ['intelligence', 'news'],
    status: 'confirmed',
    brief:
      'Ātrais r/worldnews kopsavilkums ar rezervēm, ja Reddit API nav pieejams. Paredzēts sinhronizēt top 10 globālos riskus ar kalendāra statusiem.'
  },
  {
    id: 'retro',
    title: 'Letta x DeepSeek Retro',
    date: baseDate.plus({ days: 5, hours: 4 }).toISO(),
    location: 'Studio Neon',
    tags: ['retro', 'integration'],
    status: 'tentative',
    brief:
      'Atgriezeniskās saites sesija par Letta + DeepSeek integrāciju. Jāizlemj, vai saglabājam monkey patch taktiku vai pārejam uz jaunu SDK slāni.'
  }
];

export const newsItems = [
  {
    id: 'iran-protests',
    headline: 'Protesti Irānā pieaug',
    summary: 'Valūtas kritums izraisīja trešo protestu vilni 24h laikā.',
    source: 'Reuters',
    signal: 'macro-risk'
  },
  {
    id: 'black-sea-strike',
    headline: 'Krievija bombardē Ukrainas ostas',
    summary: 'Melnās jūras kuģi atkal ir mērķēti, piegādes ķēdes kavējas.',
    source: 'BBC',
    signal: 'supply-chain'
  },
  {
    id: 'laser-shield',
    headline: 'Izraēla aktivizē Iron Beam',
    summary: '100kW sistēma testēta pret droniem.',
    source: 'AP News',
    signal: 'defense-tech'
  },
  {
    id: 'saudi-airstrike',
    headline: 'Saūda Arābija bombardē Jemenu',
    summary: 'Al-Mukalla osta slēgta, iespējami evakuācijas scenāriji.',
    source: 'Washington Post',
    signal: 'humanitarian'
  },
  {
    id: 'sidney-security',
    headline: 'Sidnejā pastiprināta drošība',
    summary: 'Jaungada perimetrs dubultots pēc vakardienas uzbrukuma.',
    source: 'Iran International',
    signal: 'public-safety'
  }
];

export const newsTickerSeeds = [
  'Nav ieplānotu notikumu tuvāko 7 dienu logā',
  'Next milestone: 2026-01-20 — "Vai Nio ir LV?"',
  'Reddit r/worldnews pieeja bloķēta, izmantojam fallback avotus',
  'Monitoring: NATO signāli par ASV garantijām Ukrainai',
  'Reminder: Letta + DeepSeek retro 5 dienās'
];
