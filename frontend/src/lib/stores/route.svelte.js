const PAGES = [
  'chat',
  'models',
  'pull',
  'storage',
  'diagnostic',
  'roadmap',
  'system',
  'design',
  'about',
  'settings'
];

function read() {
  const hash = location.hash.replace(/^#\/?/, '').split('/')[0];
  return PAGES.includes(hash) ? hash : 'chat';
}

export const route = $state({ page: read() });

export function go(page) {
  if (!PAGES.includes(page)) page = 'chat';
  route.page = page;
  location.hash = '#/' + page;
}

if (typeof window !== 'undefined') {
  window.addEventListener('hashchange', () => {
    route.page = read();
  });
}
