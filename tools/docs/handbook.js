'use strict';
(() => {
  const $ = s => document.querySelector(s), main = $('#chapter');
  const add = (parent, tag, text, cls) => {
    const n = document.createElement(tag); if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls; parent.append(n); return n;
  };
  const link = (parent, text, href) => {const n = add(parent, 'a', text); n.href = href; return n;};
  const api = async url => {const r = await fetch(url), body = await r.json(); if (!r.ok) throw Error(body.error || '读取失败'); return body;};
  let book, snapshot, generation = 0;
  function frame(title, intro, discipline) {
    main.replaceChildren();
    document.title = title + ' · SciRel 科学关系手册';
    if (discipline) add(main, 'div', discipline.join(' / '), 'crumb');
    add(main, 'h1', title); if (intro) add(main, 'p', intro, 'lead');
  }
  function boundary() {
    add(main, 'p', '函数参考保留每项能力的版本、适用条件与限制；本目录汇集多个开发版本，不是某一个安装包的完整功能清单。', 'small');
  }
  function footer() {
    const f = add(main, 'footer');
    add(f, 'p', snapshot.asset_count + ' 条正式记录 · 文档快照 ' + snapshot.snapshot_sha256.slice(0,16));
    link(f, '读取同一手册的 Agent JSON', '/api/handbook');
  }
  function topics(parent, chapter) {
    const list = add(parent, 'ol', undefined, 'chapter-menu');
    for (const t of chapter.topics) {
      const li = add(list, 'li'); link(li, t.title, '/#topic/' + t.id);
      add(li, 'p', t.introduction, 'small');
    }
  }
  function assets(parent, records) {
    const ul = add(parent, 'ul', undefined, 'asset-list');
    for (const record of records) {
      const li = add(ul, 'li'), heading = add(li, 'h3');
      link(heading, record.title.zh, '/reference#' + record.asset_id);
      add(li, 'p', record.summary);
      add(li, 'code', record.public_api.python.module + '.' + record.public_api.python.symbol);
      add(li, 'p', (record.kind === 'task_graph' ? '复合入口' : '科学关系') + ' · ' + record.version.implementation_version, 'metadata');
    }
  }
  async function render() {
    const gen = ++generation;
    try {
      const raw = location.hash.slice(1);
      if (raw.startsWith('scirel.')) {location.replace('/reference#' + raw); return;}
      if (['single','pair','rectangle','checks','limits','reference'].includes(raw)) {location.replace('/tutorials/magnetostatics#' + raw); return;}
      const [type, id] = raw.split('/').map(decodeURIComponent);
      const chapter = book.chapters.find(c => c.id === id);
      const parent = book.chapters.find(c => c.topics.some(t => t.id === id));
      const topic = parent?.topics.find(t => t.id === id);
      if (type === 'topic' && topic) {
        const items = []; let offset = 0;
        do {
          const r = await api('/api/search?topic=' + encodeURIComponent(id) + '&limit=100&offset=' + offset);
          items.push(...r.items); offset = r.next_offset;
        } while (offset !== null);
        if (gen !== generation) return;
        frame(topic.title, topic.introduction, [...parent.discipline, parent.title]); boundary();
        link(main, '返回本章导读', '/#chapter/' + parent.id);
        if (topic.tutorial_id) {
          add(main, 'h2', '案例与结果').style.marginTop = '30px';
          link(main, '轴对称线圈磁场：从单圆环到线圈组', '/tutorials/' + topic.tutorial_id).className = 'tutorial-link';
          add(main, 'p', '包含实际运行的代码、数值结果、图表与解释。');
        } else add(main, 'p', '本节先提供导读与函数参考；完整的运行案例正在逐步补充。', 'small');
        add(main, 'h2', '可用关系与调用入口').style.marginTop = '30px'; assets(main, items);
        await ScirelNavigation.mount($('.tree'), {book, topicId:id, chapterId:parent.id});
      } else if (type === 'chapter' && chapter) {
        frame(chapter.title, chapter.introduction, chapter.discipline); boundary(); topics(main, chapter);
        await ScirelNavigation.mount($('.tree'), {book, chapterId:id});
      } else if (type === 'search') {
        const q = id || ''; $('#q').value = q;
        const records = await api('/api/search?q=' + encodeURIComponent(q) + '&limit=20');
        if (gen !== generation) return;
        frame('搜索手册', q ? '关键词：' + q : '请输入想解决的问题或 API 名称。');
        if (q) {
          const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
          const matches = book.chapters.flatMap(c => c.topics.map(t => ({...t, chapter:c.title}))).filter(t => terms.every(term => (t.chapter+' '+t.title+' '+t.introduction).toLowerCase().includes(term)));
          add(main, 'h2', '章节与问题');
          const list = add(main, 'ul'); matches.forEach(t => link(add(list, 'li'), t.chapter + ' / ' + t.title, '/#topic/' + t.id));
          if (!matches.length) add(main, 'p', '没有匹配的章节主题。');
          add(main, 'h2', '函数参考'); add(main, 'p', records.total + ' 条匹配；显示前 20 条。'); assets(main, records.items);
          link(main, '在函数参考中继续筛选和翻页', '/reference?q=' + encodeURIComponent(q));
        }
        await ScirelNavigation.mount($('.tree'), {book});
      } else if (!raw) {
        frame(book.title, book.introduction); boundary();
        add(main, 'h2', '阅读路径');
        add(main, 'p', '从领域目录进入要解决的问题，查看可调用的科学关系；需要完整实践时阅读案例，核对模型假设、输入单位、计算结果及限制。复杂问题通过复合入口串联已有关系。');
        link(main, '从已运行的线圈磁场案例开始', '/tutorials/magnetostatics').className = 'tutorial-link';
        const list = add(main, 'ol', undefined, 'chapter-list');
        for (const c of book.chapters) {const li=add(list,'li');link(add(li,'h2'),c.title,'/#chapter/'+c.id);add(li,'p',c.introduction);topics(li,c);}
        await ScirelNavigation.mount($('.tree'), {book});
      } else {frame('未找到此章节', '目录可能已调整，请从左侧目录或搜索继续。');await ScirelNavigation.mount($('.tree'), {book});}
      if (gen !== generation) return;
      footer(); ScirelPresentation.enhance(main); window.scrollTo(0,0);
    } catch(e) {if (gen===generation) frame('手册读取失败', e.message);}
  }
  $('#search').onsubmit = e => {e.preventDefault();location.hash = 'search/' + encodeURIComponent($('#q').value.trim());};
  window.addEventListener('hashchange', () => {if(book) render();});
  Promise.all([api('/api/handbook'),api('/api/manifest')]).then(([h,m])=>{book=h.document;snapshot=m;render();}).catch(e=>frame('手册读取失败',e.message));
})();
