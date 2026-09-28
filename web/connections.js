// Provider keys are posted once, never put in localStorage or project documents.
export function connectionsPanel({api,showDialog,toast,esc,refresh}) {
  let settings;
  const kinds=['text','image','video','voice','music','captions'];
  const labels={text:'Scene assistant',image:'Images',video:'Videos',voice:'Voiceovers',music:'Music',captions:'Captions',edit:'Video edit',avatar:'Speaking avatar',stock:'Stock media'};
  async function open(){
    settings=await api('/api/providers');
    showDialog('Connections',`<p class="panel-note">Use your own accounts. Keys are encrypted on this server and belong to this browser workspace. Editing, the six examples, and local exports work without a key.</p>
    <section class="connection-defaults"><h3>Choose a provider for each task</h3><div class="fields">${kinds.map(kind=>`<label>${labels[kind]}<select id="default-${kind}"><option value="">Auto select</option>${settings.providers.filter(p=>p.configured&&p.models[kind]).map(p=>`<option value="${p.id}" ${settings.defaults[kind]===p.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label>`).join('')}</div><button class="pill primary" data-action="connections-defaults">Save defaults</button></section>
    <div class="connection-list">${settings.providers.map(p=>`<details class="connection"><summary><strong>${esc(p.name)}</strong><span class="chip">${p.configured?'Connected '+esc(p.key_hint):'Add key'}</span></summary><p class="panel-note">${p.capabilities.map(c=>labels[c]||c).join(' · ')}</p><form id="connection-${p.id}" autocomplete="off" onsubmit="return false">
    <label>API key<input type="password" name="key" autocomplete="new-password" placeholder="${p.configured?'Leave blank to keep current key':'Paste your API key'}" maxlength="2000"></label>
    ${p.id==='compatible'?`<label>Base URL<input type="url" name="base_url" value="${esc(p.base_url)}" placeholder="https://your-provider.example/v1"></label><label class="inline"><input type="checkbox" name="keyless" ${p.keyless?'checked':''}>Keyless endpoint</label><p class="panel-note">Requires the OpenAI REST API format. Private network endpoints require OPENVID_ALLOW_LOCAL_PROVIDERS=true on your server.</p>`:''}
    <div class="fields">${Object.entries(p.models).map(([kind,model])=>`<label>${labels[kind]} model<input name="model-${kind}" value="${esc(model)}" placeholder="${p.id==='replicate'?'owner/model':'Model or endpoint ID'}" maxlength="200"></label>`).join('')}</div>
    ${['fal','replicate'].includes(p.id)?`<label>Advanced model inputs (JSON)<textarea name="inputs" rows="4" spellcheck="false">${esc(JSON.stringify(p.inputs,null,2))}</textarea></label><p class="panel-note">Per-task settings, for example {"video":{"resolution":"720p"}}. Model-specific fields must match the endpoint schema.</p>`:''}
    <div class="row"><button class="pill primary" data-action="connections-save" data-provider="${p.id}">Save connection</button><button class="pill" data-action="connections-test" data-provider="${p.id}">Test saved key</button>${p.configured?`<button class="pill danger" data-action="connections-remove" data-provider="${p.id}">Disconnect</button>`:''}</div><p class="connection-status panel-note" role="status"></p></form></details>`).join('')}</div><p class="panel-note">Generation is billed directly by your providers. A connection test does not generate media. Back up your server’s data volume, including its encryption key, to retain connections and projects.</p>`,true);
  }
  async function action(a,b){
    if(!a.startsWith('connections-'))return false;
    b.disabled=true;
    const name=b.dataset.provider, form=name?document.querySelector('#connection-'+name):null;
    try{
      if(a==='connections-defaults'){
        await api('/api/provider-defaults',{method:'PUT',body:JSON.stringify(Object.fromEntries(kinds.map(k=>[k,document.querySelector('#default-'+k).value])))});
        await refresh();toast('Default providers saved');
      }
      if(a==='connections-save'){
        const p=settings.providers.find(p=>p.id===name),data=new FormData(form),key=data.get('key').trim();
        const body={models:Object.fromEntries(Object.keys(p.models).map(k=>[k,data.get('model-'+k).trim()])),inputs:data.has('inputs')?JSON.parse(data.get('inputs')||'{}'):{}};
        if(key)body.key=key;
        if(name==='compatible'){body.base_url=data.get('base_url');body.keyless=data.get('keyless')==='on'}
        await api('/api/providers/'+name,{method:'PUT',body:JSON.stringify(body)});
        form.elements.key.value='';await refresh();await open();toast('Connection saved');
      }
      if(a==='connections-test'){
        const result=await api('/api/providers/'+name+'/test',{method:'POST',body:'{}'});form.querySelector('.connection-status').textContent=result.message;
      }
      if(a==='connections-remove'){
        await api('/api/providers/'+name,{method:'DELETE'});await refresh();await open();toast('Connection removed');
      }
    }catch(e){if(form)form.querySelector('.connection-status').textContent=e.message;else toast(e.message)}finally{b.disabled=false}
    return true;
  }
  return {open,action};
}
