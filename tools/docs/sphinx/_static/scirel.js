/* Preserve links saved from the previous single-page handbook. */
document.addEventListener('DOMContentLoaded', () => {
  document.documentElement.dataset.theme = 'light';
  if (!['/', '/reference'].includes(location.pathname)) return;
  const key = location.hash.slice(1);
  let target;
  if (key.startsWith('scirel.')) target = '/reference/generated/' + key + '.html';
  else if (key.startsWith('chapter/')) target = '/user-guide/' + key.slice(8) + '.html';
  else if (key.startsWith('topic/')) target = '/user-guide/topics/' + key.slice(6) + '.html';
  else if (key.startsWith('search/')) target = '/search.html?q=' + key.slice(7);
  else if (location.pathname === '/' && ['single','pair','rectangle','checks','limits','reference'].includes(key))
    target = '/tutorials/magnetostatics.html#' + key;
  if (target && /^\/[a-zA-Z0-9_./%?=+&#-]+$/.test(target)) location.replace(target);
});
