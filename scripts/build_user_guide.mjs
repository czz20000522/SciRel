// Documentation only: never imports the scientific runtime or computes examples.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const { marked } = await import(pathToFileURL(require.resolve('marked')).href);
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = path.join(repo, 'docs/user-guide');
const out = path.resolve(process.argv[2] || path.join(repo, 'build/user-guide'));
const read = name => fs.readFileSync(path.join(source, name), 'utf8');
const site = JSON.parse(read('site.json'));
const snapshot = JSON.parse(read('api-snapshot.json'));
const binding = JSON.parse(read('binding.json'));
const digest = value => crypto.createHash('sha256').update(value).digest('hex');
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const inline = value => String(typeof value === 'object' ? JSON.stringify(value) : value ?? '').replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
const apis = snapshot.apis;
if (out === source || out.startsWith(source + path.sep)) throw new Error('Choose a separate generated output directory');
if (binding.wheel_sha256 !== snapshot.binding.wheel_sha256 || apis.length !== binding.public_entries) throw new Error('API snapshot/version mismatch');
if (new Set(apis.map(x => x.id)).size !== apis.length) throw new Error('Duplicate API identity');

let reference = '# 公共调用参考\n\n先按物理功能选择接口，再查本页。以下签名由本版 wheel 的声明静态抽取；不 import 整个科学库。\n\n' +
  `函数和配置类共 ${apis.length} 个公共入口。${binding.detailed_contracts} 个入口附有既有 canonical 合同的生成投影；其余是有限兼容参考。声明中的符号默认值按来源保留，不能假定是已求值常量。类字段的源码默认值也不补造单位或科学保证。\n\n`;
for (const p of site.pages.filter(p => p.questions)) {
  const entries = apis.filter(a => a.topic_id === p.id);
  if (!entries.length) throw new Error(`Empty physical topic ${p.id}`);
  reference += `## ${p.title}\n\n物理说明：[${p.title}](${p.file})。\n\n`;
  for (const a of entries) {
    reference += `<a id="api-${a.id}"></a>\n\n### ${a.symbol}\n\n${a.title}。\n\n\`from ${a.module} import ${a.symbol}\`\n\n`;
    if (a.kind === 'class') {
      reference += '构造字段按下面的声明传入；未写默认值的字段必须提供。\n\n<details><summary>展开字段、类型与源码默认值</summary>\n\n| 字段 | 类型声明 | 源码默认值 |\n| --- | --- | --- |\n';
      for (const f of a.fields) reference += `| \`${f.name}\` | \`${inline(f.annotation)}\` | ${f.default_source == null ? '必填' : '`'+inline(f.default_source)+'`'} |\n`;
      reference += '\n</details>\n\n';
      if (a.methods.length) reference += a.methods.map(m => '`'+m.signature+'`').join('；')+'。\n\n';
    } else reference += `\`\`\`python\n${a.signature}\n\`\`\`\n\n`;
    const d = a.contract_projection;
    if (!d) {
      reference += '**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。\n\n';
      continue;
    }
    reference += `**已有详细合同**：\`${d.asset_id}\`。以下内容由本版 canonical 记录投影，完整机器可读版本见 Agent 的对应 API 文件。\n\n`;
    for (const [label, ports] of [['输入', d.inputs], ['输出',d.outputs]]) {
      reference += `#### ${label}\n\n| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |\n| --- | --- | --- | --- | --- |\n`;
      for (const f of ports) reference += `| \`${f.name}\` | ${inline(f.description)} | ${inline(f.units)} | ${inline(f.shape)} / ${inline(f.dtype)} | ${inline(f.constraints)}${f.default !== undefined ? '; default='+inline(f.default) : ''} |\n`;
      reference += '\n';
    }
    reference += `关系：${d.identity.definition}\n\n`;
    reference += `适用前提：${d.applicability.preconditions.join('；')}\n\n`;
    reference += `无效输入：${d.failure_semantics.invalid_input}\n\n`;
    reference += `运行失败：${d.failure_semantics.runtime_failure}\n\n`;
    reference += `证据上限：${d.verification.evidence_ceiling}\n\n`;
  }
}
fs.writeFileSync(path.join(source, 'api-reference.md'), reference);
const pages = site.pages.map(p => ({...p, markdown:read(p.file)}));
const sourceHashes = Object.fromEntries(['binding.json','site.json','api-snapshot.json',...pages.map(p=>p.file)].map(n => [n,digest(read(n))]));
const documentDigest = digest(JSON.stringify(sourceHashes));
const version = {...binding, document_sha256:documentDigest, source_hashes:sourceHashes};
fs.mkdirSync(out, {recursive:true});
const writeJSON = (name, data) => {
  const target = path.join(out,name); fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.writeFileSync(target,JSON.stringify(data,null,2)+'\n');
};
const modules = new Set(apis.map(a=>a.module));
if (modules.size !== binding.public_modules || apis.filter(a=>a.contract_projection).length !== binding.detailed_contracts) throw new Error('Documented API count mismatch');

for (const p of pages) {
  const dest = path.join(out,'markdown',p.file);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,p.markdown);
}
writeJSON('version.json',version);
writeJSON('agent/route.json',{
  schema:'scirel.physical-topic-route.v1',package_version:binding.package_version,wheel_sha256:binding.wheel_sha256,document_sha256:documentDigest,
  read_order:['Select a physical topic here.','Read only its topic JSON.','Follow only required API records and contract projections.'],
  purpose:'Physical usage orientation; executable scientific selection belongs to the bound canonical catalog.',
  catalog_binding:{...binding.catalog,release_version:binding.package_version,release_sha256:binding.catalog_sha256,location:'Supplied separately by the evaluation/runtime; consult its material manifest.'},
  installation:'../markdown/version-and-installation.md',examples:'../markdown/examples.md',
  topics:pages.filter(p=>p.questions).map(p=>({id:p.id,domain:'magnetic-confinement-fusion',title:p.title,summary:p.summary,questions:p.questions,record:`topics/${p.id}.json`}))
});
for (const p of pages.filter(p=>p.questions)) writeJSON(`agent/topics/${p.id}.json`,{
  schema:'scirel.physical-topic.v1',id:p.id,package_version:binding.package_version,document_sha256:documentDigest,
  title:p.title,summary:p.summary,content_markdown:p.markdown,
  apis:apis.filter(a=>a.topic_id===p.id).map(a=>({id:a.id,title:a.title,status:a.status,record:`../apis/${a.id}.json`}))
});
for (const a of apis) writeJSON(`agent/apis/${a.id}.json`,{schema:'scirel.public-api-guide.v1',package_version:binding.package_version,wheel_sha256:binding.wheel_sha256,document_sha256:documentDigest,...a});
fs.writeFileSync(path.join(out,'agent/README.md'),
  '# Agent 阅读入口\n\n先读 route.json 按物理问题选题，再读 topics/<id>.json，仅在需要调用时读取 apis/<id>.json。\n\n'+
  '所有路径相对当前文件；可通过普通文件读取或静态 HTTP GET 查询，不需要专用 MCP 服务或全量 import。\n'+
  '这是使用指南入口；实际选用科学能力须从同版本 canonical catalog 渐进发现并读取 exact record，不能将 32 个兼容入口都选入计划。出库方法由独立 skills 提供。\n'+
  '主题提供物理含义、单位、边界和例子；API 提供 exact 签名及已有合同的投影。兼容参考不拥有未证实的科学资格。\n'+
  `版本 ${binding.package_version}；文档 SHA-256 ${documentDigest}。发现新 wheel 时先核版本绑定。\n`);

const pageByFile = new Map(pages.map(p=>[p.file,p]));
function render(p) {
  let html=marked.parse(p.markdown,{gfm:true});let heading=0;
  html=html.replace(/<h([1-6])>([\s\S]*?)<\/h\1>/g,(_,n,text)=>`<h${n} id="${p.id}-heading-${++heading}">${text}</h${n}>`);
  html=html.replace(/href="([^"#]+\.md)(#[^"]*)?"/g,(match,href)=>{
    const relative=path.posix.normalize(path.posix.join(path.posix.dirname(p.file),href));
    const dest=pageByFile.get(relative);if(!dest)throw new Error(`Unresolved Markdown link ${p.file} -> ${href}`);
    return `href="#${dest.id}"`;
  });
  return `<article class="chapter" id="${p.id}" data-topic="${p.id}" aria-label="${escape(p.title)}"><div class="eyebrow">${escape(p.group)}</div>${html}</article>`;
}
const searchEntries=[...pages.map(p=>({title:p.title,detail:p.summary,url:'#'+p.id,search:p.title+' '+p.summary+' '+(p.questions||[]).join(' ')})),...apis.map(a=>({title:a.title,detail:a.id,url:'#api-'+a.id,search:a.title+' '+a.id}))];
const searchJSON=JSON.stringify(searchEntries).replace(/</g,'\\u003c');
let group='';let nav='';
for(const p of pages){if(group!==p.group){group=p.group;nav+=`<div class="nav-group">${escape(group)}</div>`;}nav+=`<a href="#${p.id}">${escape(p.title)}</a>`;}
const css=`:root{--ink:#142b35;--muted:#526772;--accent:#006b65;--line:#d9e3e4;--paper:#fff;--bg:#f5f8f8}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;color:var(--ink);background:var(--bg);font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;font-size:16px;line-height:1.8}a{color:var(--accent);text-underline-offset:3px}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #c78b28;outline-offset:3px}.layout{display:grid;grid-template-columns:280px minmax(0,1fr);max-width:1500px;margin:auto}.sidebar{position:sticky;top:0;height:100vh;padding:32px 22px;overflow:auto;border-right:1px solid var(--line);background:#eff5f4}.brand{font-size:26px;font-weight:750;letter-spacing:-1px}.brand small{display:block;font-size:13px;letter-spacing:0;font-weight:500;color:var(--muted)}.search-label{display:block;margin-top:26px;font-size:13px;color:var(--muted)}input{width:100%;padding:10px 12px;margin:5px 0 10px;font:inherit;font-size:14px;border:1px solid #afc5c6;border-radius:7px;background:white}#results{margin:0;padding:0;list-style:none;max-height:340px;overflow:auto;font-size:13px}#results a{display:block;padding:8px;background:#fff;border-bottom:1px solid var(--line);text-decoration:none}#results small{display:block;color:var(--muted);overflow-wrap:anywhere}.nav-group{font-size:11px;font-weight:750;color:var(--muted);letter-spacing:1px;margin:22px 0 7px}.sidebar nav>a{display:block;padding:6px 8px;font-size:14px;border-radius:5px;text-decoration:none}.sidebar nav>a:hover{background:#dcebe8}.sidebar summary{font-size:14px;cursor:pointer}.small-note{font-size:12px;color:var(--muted);margin-top:26px}.main{padding:38px clamp(24px,5vw,72px) 60px;min-width:0}.masthead{border-bottom:1px solid var(--line);padding-bottom:28px;margin-bottom:30px}.masthead h1{font-size:38px;line-height:1.3;margin:10px 0}.masthead p{color:var(--muted);margin:8px 0}.badge{display:inline-block;color:var(--accent);border:1px solid #b4ceca;border-radius:6px;padding:4px 9px;font-size:12px}.chapter{background:var(--paper);padding:26px clamp(18px,3vw,38px);border:1px solid var(--line);border-radius:12px;margin:0 0 28px;overflow-wrap:anywhere}.eyebrow{color:var(--accent);font-size:11px;font-weight:750;letter-spacing:1px}.chapter h1{font-size:28px;line-height:1.4;margin:10px 0 22px}.chapter h2{font-size:22px;margin:28px 0 10px}.chapter h3{font-size:19px;margin:30px 0 10px}.chapter h4{font-size:16px;margin:18px 0 8px}p{margin:12px 0}table{display:block;width:100%;overflow:auto;border-collapse:collapse;font-size:14px;margin:18px 0}th,td{padding:10px 12px;border:1px solid var(--line);vertical-align:top;min-width:80px}th{background:#edf4f3;text-align:left}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.87em;background:#f0f4f5;padding:2px 4px;border-radius:4px}pre{background:#102a35;color:#d9eaf0;padding:18px;border-radius:8px;overflow:auto;line-height:1.65;white-space:pre}pre code{background:none;color:inherit;padding:0}details{border:1px solid var(--line);border-radius:6px;padding:10px 14px;margin:14px 0}summary{cursor:pointer;color:var(--accent)}.footer{font-size:12px;color:var(--muted);overflow-wrap:anywhere}@media(max-width:850px){.layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:20px}.main{padding:24px 14px}.masthead h1{font-size:30px}.chapter{padding:22px 16px}.brand small{display:inline;margin-left:12px}.search-label{margin-top:15px}.sidebar nav{columns:2}.nav-group{break-after:avoid}.sidebar nav>a{break-inside:avoid}}@media print{.sidebar{display:none}.layout{display:block}.main{padding:0}.chapter{break-inside:auto;border:0;padding:12px 0}pre{white-space:pre-wrap;color:black;background:#f3f3f3}details{display:block}summary{display:none}}`;
const js=`const entries=${searchJSON};const input=document.getElementById('search');const results=document.getElementById('results');input.addEventListener('input',()=>{results.replaceChildren();const q=input.value.trim().toLocaleLowerCase();if(!q)return;const hits=entries.filter(e=>e.search.toLocaleLowerCase().includes(q)).slice(0,12);if(!hits.length){const li=document.createElement('li');li.textContent='未找到匹配主题或接口';results.append(li);}for(const e of hits){const li=document.createElement('li');const a=document.createElement('a');a.href=e.url;a.textContent=e.title;const s=document.createElement('small');s.textContent=e.detail;a.append(s);li.append(a);results.append(li);}});document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();input.focus();}if(e.key==='Escape'){input.value='';results.replaceChildren();input.blur();}});if(innerWidth<851)document.getElementById('nav').open=false;`;
const html=`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(site.title)} · ${escape(binding.package_version)}</title><style>${css}</style></head><body><div class="layout"><aside class="sidebar"><div class="brand">SciRel<small>科学使用指南</small></div><label class="search-label" for="search">查找物理问题或接口 · /</label><input id="search" type="search" placeholder="例如：温度剖面、输运、radial_gradient" aria-controls="results" autocomplete="off"><ul id="results" aria-live="polite"></ul><details id="nav" open><summary>物理功能导航</summary><nav aria-label="指南导航">${nav}</nav></details><p class="small-note">先理解物理功能，再选择调用入口。<br>当前内容绑定开发版 wheel。<br>Agent 从 agent/route.json 开始。</p></aside><main class="main"><header class="masthead"><span class="badge">MAGNETIC CONFINEMENT FUSION</span><h1>从物理问题，到可复用计算</h1><p>理解物理含义、输入约定和适用边界，再调用 SciRel。</p><span class="badge">${escape(binding.package_version)}</span></header>${pages.map(render).join('')}<footer class="footer">文档 SHA-256：${documentDigest}<br>wheel SHA-256：${binding.wheel_sha256}<br>本页面可离线浏览；网页、Markdown 与 Agent 查询文件来自同一文档版本。</footer></main></div><script>${js}</script></body></html>`;
fs.writeFileSync(path.join(out,'SciRel-使用指南.html'),html);
function inventory(dir,prefix=''){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(d=>{const n=prefix+d.name;return d.isDirectory()?inventory(path.join(dir,d.name),n+'/'):[n];});}
const names=inventory(out).filter(n=>n!=='manifest.json');
writeJSON('manifest.json',{schema:'scirel.user-guide-export.v1',package_version:binding.package_version,wheel_sha256:binding.wheel_sha256,document_sha256:documentDigest,files:names.sort().map(n=>({path:n,sha256:digest(fs.readFileSync(path.join(out,n))),bytes:fs.statSync(path.join(out,n)).size}))});
console.log(JSON.stringify({output:out,pages:pages.length,apis:apis.length,physical_topics:pages.filter(p=>p.questions).length,document_sha256:documentDigest,html_bytes:Buffer.byteLength(html)}));
