'use strict';
window.ScirelNavigation = (() => {
  const add = (parent, tag, text) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    parent.append(node);
    return node;
  };
  async function mount(tree, {chapterId, topicId, tutorial, toc, book} = {}) {
    const skip = document.querySelector('.skip-link');
    if (skip) skip.onclick = event => {
      event.preventDefault();
      const main = document.querySelector('main');
      main.tabIndex = -1; main.focus(); main.scrollIntoView();
    };
    if (!book) {
      const response = await fetch('/api/handbook');
      if (!response.ok) throw Error('手册目录读取失败');
      book = (await response.json()).document;
    }
    tree.replaceChildren();
    add(tree, 'h2', '目录');
    const home = add(tree, 'a', '手册概览'); home.href = '/';
    if (!chapterId && !topicId && !tutorial) home.setAttribute('aria-current', 'page');
    for (const chapter of book.chapters) {
      const details = add(tree, 'details');
      details.open = chapter.id === chapterId || chapter.topics.some(t => t.id === topicId || (tutorial && t.tutorial_id === tutorial));
      add(details, 'summary', chapter.title);
      const list = add(details, 'ol'); list.className = 'topic-list';
      const overview = add(add(list, 'li'), 'a', '本章导读'); overview.href = '/#chapter/' + chapter.id;
      if (chapter.id === chapterId && !topicId && !tutorial) overview.setAttribute('aria-current', 'page');
      for (const topic of chapter.topics) {
        const li = add(list, 'li'), link = add(li, 'a', topic.title);
        link.href = '/#topic/' + topic.id;
        if (topic.id === topicId) link.setAttribute('aria-current', 'page');
        if (topic.tutorial_id) {
          const example = add(li, 'a', '案例：轴对称线圈磁场');
          example.href = '/tutorials/' + topic.tutorial_id;
          if (topic.tutorial_id === tutorial) {
            example.setAttribute('aria-current', 'page');
            if (toc) li.append(toc);
          }
        }
      }
    }
    return book;
  }
  return {mount};
})();
