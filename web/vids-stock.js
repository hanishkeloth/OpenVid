export function createStockPanel({state, $, esc, icon, api, post, insertAsset, toast}) {
  const names = {pexels:'Pexels', pixabay:'Pixabay', commons:'Wikimedia Commons'};
  const links = {pexels:'https://www.pexels.com/', pixabay:'https://pixabay.com/', commons:'https://commons.wikimedia.org/'};
  let provider='pexels', kind='image', query='', page=1, results=null, message='', searching=false, requestToken=0;
  const importing=new Set();
  const key=item=>`${item.provider}:${item.kind}:${item.id}`;

  function cards() {
    if (!results) return `<p class="panel-note">${esc(message||'Find a photo or clip for your next scene.')}</p>`;
    return results.items.map((x,i)=>`<article class="asset stock-card">
      <button data-action="stock-insert" data-index="${i}" aria-label="Add ${esc(x.title)}" ${importing.has(key(x))?'disabled':''}>
        ${x.thumb&&x.kind!=='audio'?`<img loading="lazy" src="${esc(x.thumb)}" alt="${esc(x.title)}">`:`<div class="audio-art">${icon(x.kind==='video'?'video':x.kind==='audio'?'music':'image')}</div>`}
        <small>${importing.has(key(x))?'Importing…':esc(x.title)}</small>
        ${x.kind==='video'?`<span class="stock-duration">${x.duration?Math.round(x.duration)+'s':''}${x.width&&x.height?' · '+x.width+'×'+x.height:''}</span>`:''}
      </button>
      <small><a href="${esc(x.source)}" target="_blank" rel="noopener noreferrer">${esc(x.artist||names[x.provider])} · ${names[x.provider]}</a></small>
      <small>${x.license_url?`<a href="${esc(x.license_url)}" target="_blank" rel="noopener noreferrer">${esc(x.license)}</a>`:esc(x.license)}</small>
    </article>`).join('') || '<p class="panel-note">No results. Try another search.</p>';
  }
  function pagination() {
    if (!results || (!results.has_more && page===1)) return '';
    return `<div class="row stock-pages"><button class="pill" data-action="stock-prev" ${page===1||searching?'disabled':''}>Previous</button><span>Page ${page}</span><button class="pill" data-action="stock-next" ${!results.has_more||searching?'disabled':''}>Next</button></div>`;
  }
  function html() {
    const available=state.config.stock||{};
    return `<p class="panel-note">${kind==='audio'?'Audio':'Images and videos'} from <a href="${links[provider]}" target="_blank" rel="noopener noreferrer">${names[provider]}</a>. Add a result to your scene; creator credits stay with your video.</p>
      <label>Stock provider<select id="stock-provider">${Object.entries(names).map(([id,name])=>`<option value="${id}" ${provider===id?'selected':''} ${available[id]===false?'disabled':''}>${name}${available[id]===false?' · not configured':''}</option>`).join('')}</select></label>
      <label>Media type<select id="stock-kind">${[['image','Images'],['video','Videos'],['audio','Audio · Wikimedia Commons']].map(([id,name])=>`<option value="${id}" ${kind===id?'selected':''}>${name}</option>`).join('')}</select></label>
      <input id="stock-query" maxlength="100" value="${esc(query)}" placeholder="Mountains, city, nature…" aria-label="Stock search">
      <button class="full-button pill" data-action="stock-search" ${searching?'disabled':''}>${icon('search')}${searching?'Searching…':'Search stock'}</button>
      <div id="stock-results" class="asset-grid" aria-live="polite" aria-busy="${searching}">${cards()}</div><div id="stock-pages">${pagination()}</div>`;
  }
  function refresh() {
    if(state.panel==='stock' && $('#side-panel .panel-body')) $('#side-panel .panel-body').innerHTML=html();
  }
  async function search(targetPage=1) {
    query=($('#stock-query')?.value||query).trim();
    if(query.length<2) {toast('Enter at least two characters');return;}
    const token=++requestToken, searchProvider=provider, searchKind=kind;
    searching=true;results=null;message='Searching…';refresh();
    try {
      const data=await api('/api/vids-stock?'+new URLSearchParams({query,kind:searchKind,provider:searchProvider,page:targetPage,paginated:true}));
      if(token!==requestToken)return;
      results=data;page=data.page;message='';
    } catch(e) {
      if(token===requestToken)message=e.message;
      throw e;
    } finally {
      if(token===requestToken){searching=false;refresh();}
    }
  }
  async function action(name, button) {
    if(name==='stock-search')return search();
    if(name==='stock-next')return search(page+1);
    if(name==='stock-prev')return search(Math.max(1,page-1));
    const item=results?.items[+button.dataset.index];
    if(!item||importing.has(key(item)))return;
    const documentId=state.record.id, projectId=state.record.project_id, sceneId=state.doc.scenes[state.index].id;
    importing.add(key(item));refresh();toast('Importing stock media…');
    try {
      const asset=await post(`/api/vids-stock/${projectId}/import`, {page_id:item.id,provider:item.provider,kind:item.kind});
      if(state.record?.id!==documentId){toast('Stock media saved to the original video’s library');return;}
      state.assets.unshift(asset);
      if(state.doc.scenes.some(s=>s.id===sceneId))insertAsset(asset,{scene_id:sceneId});
      else toast('Stock media saved to Uploads');
    } finally {importing.delete(key(item));refresh();}
  }
  document.addEventListener('input',e=>{if(e.target.id==='stock-query')query=e.target.value;});
  document.addEventListener('change',e=>{
    if(!['stock-provider','stock-kind'].includes(e.target.id))return;
    query=$('#stock-query').value;
    if(e.target.id==='stock-provider'){provider=e.target.value;if(provider!=='commons'&&kind==='audio')kind='image';}
    else {kind=e.target.value;if(kind==='audio')provider='commons';}
    requestToken++;searching=false;results=null;message='';page=1;refresh();
  });
  document.addEventListener('keydown',e=>{if(e.target.id==='stock-query'&&e.key==='Enter'){e.preventDefault();if(!searching)search().catch(e=>toast(e.message));}});
  return {html, action};
}
