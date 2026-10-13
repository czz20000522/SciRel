/* Shared documentation presentation; scientific records remain unchanged. */
'use strict';
window.ScirelPresentation = {
  enhance(root = document) {
    root.querySelectorAll('pre').forEach(pre => {
      if (pre.parentElement.classList.contains('code-block')) return;
      const text = pre.textContent, wrap = document.createElement('div');
      wrap.className = 'code-block'; pre.replaceWith(wrap); wrap.append(pre);
      const code = document.createElement('code'); code.textContent = text;
      pre.replaceChildren(code);
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'copy-code';
      button.textContent = '复制'; button.setAttribute('aria-label', '复制代码块');
      const status = document.createElement('span'); status.className = 'copy-status';
      status.setAttribute('role', 'status'); wrap.append(button, status);
      button.onclick = async () => {
        try {
          await navigator.clipboard.writeText(text);
          status.textContent = '已复制';
        } catch (_) {
          const selection = getSelection(), range = document.createRange();
          range.selectNodeContents(code); selection.removeAllRanges(); selection.addRange(range);
          status.textContent = '无法访问剪贴板，已选中代码，请手动复制';
        }
      };
    });
  },
  formula(parent, markup, fallback) {
    const parsed = new DOMParser().parseFromString(markup, 'application/xml');
    const allowed = new Set(['math','mrow','mi','mn','mo','mfrac','msup','msub','mtext']);
    const nodes = [...parsed.querySelectorAll('*')];
    if (parsed.documentElement.localName !== 'math' || nodes.some(n =>
      n.namespaceURI !== 'http://www.w3.org/1998/Math/MathML' || !allowed.has(n.localName) ||
      [...n.attributes].some(a => !['xmlns','display'].includes(a.name)))) {
      parent.textContent = fallback; return;
    }
    const math = document.importNode(parsed.documentElement, true);
    math.setAttribute('aria-label', fallback); parent.append(math);
  }
};
