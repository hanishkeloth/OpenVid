// The editor and export compiler share geometry, timing, and text escaping.
export const uid = () => crypto.randomUUID().replaceAll('-', '').slice(0, 12);
export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const clone = value => JSON.parse(JSON.stringify(value));
export const total = doc => doc.scenes.reduce((n, s) => n + Number(s.duration), 0);
export const dimensions = (aspect, resolution='1080p') => {
  const h = resolution === '720p' ? 720 : 1080;
  return aspect === '9:16' ? [h, Math.round(h*16/9)] : aspect === '1:1' ? [h,h] : [Math.round(h*16/9),h];
};
export const sceneStart = (doc, index) => doc.scenes.slice(0,index).reduce((n,s)=>n+Number(s.duration),0);
export const layer = (kind='text', values={}) => ({id:uid(),kind,text:kind==='text'?'Add your text':'',url:'',x:8,y:12,w:84,h:25,rotation:0,opacity:1,color:'#202124',fill:'#dce5ff',font:'Arial',fontSize:64,bold:false,italic:false,align:'left',shape:'rectangle',fit:'cover',start:0,duration:5,trim:0,speed:1,volume:1,fadeIn:0,fadeOut:0,animation:'none',locked:false,hidden:false,...values});
export const scene = (values={}) => ({id:uid(),name:'Scene',duration:5,background:'#ffffff',notes:'',transition:'none',layers:[],...values});
export const blank = () => ({name:'Untitled video',aspect:'16:9',scenes:[scene()],audio:[],starred:false,captions:true});
export function layerStyle(l, width=1920, height=1080) {
  let css=`position:absolute;left:${l.x}%;top:${l.y}%;width:${l.w}%;height:${l.h}%;transform:rotate(${l.rotation||0}deg) scale(${l.flipX?-1:1},${l.flipY?-1:1});opacity:${l.opacity??1};box-sizing:border-box;border:${l.borderWidth||0}px solid ${l.borderColor||'#202124'};border-radius:${l.radius||0}%;${l.shadow?'box-shadow:0 10px 25px #0005;':''}`;
  if(l.kind==='text') css+=`color:${l.color};font-family:'${l.font}',sans-serif;font-size:${l.fontSize*height/1080}px;font-weight:${l.bold?700:400};font-style:${l.italic?'italic':'normal'};text-align:${l.align};white-space:pre-wrap;overflow:hidden;line-height:1.2;overflow-wrap:break-word;`;
  if(l.kind==='shape') css+=`background:${l.fill};border-radius:${l.shape==='ellipse'?'50%':'0'};${l.shape==='triangle'?'clip-path:polygon(50% 0,100% 100%,0 100%);':''}${l.shape==='line'?'height:0.5%;':''}`;
  if(['image','video'].includes(l.kind)) css+=`object-fit:${l.fit};object-position:${l.cropX??50}% ${l.cropY??50}%;filter:brightness(${l.brightness??1}) contrast(${l.contrast??1}) saturate(${l.saturation??1});overflow:hidden;`;
  if(l.caption)css+='background:#000b;text-shadow:0 2px 4px #000;border-radius:8px;padding:12px;';
  return css;
}
export function compile(doc, {resolution='1080p',origin=''}={}) {
  const [w,h]=dimensions(doc.aspect,resolution), length=total(doc); let html='', moves=[];
  function draw(l,start,duration,index) {
    if(l.hidden || duration<=0 || (l.caption && !doc.captions)) return;
    const id='l'+l.id, timing=`id="${esc(id)}" data-start="${start}" data-duration="${duration}" data-track-index="${index}"`;
    const style=layerStyle(l,w,h); const url=esc(l.url?.startsWith('/')?origin+l.url:l.url);
    if(l.kind==='text') html+=`<div ${timing} style="${style}">${esc(l.text)}</div>`;
    if(l.kind==='shape') html+=`<div ${timing} style="${style}"></div>`;
    if(l.kind==='image') html+=`<img ${timing} src="${url}" style="${style}">`;
    if(['video','audio'].includes(l.kind)) html+=`<${l.kind} ${timing} src="${url}" ${l.kind==='video'?(l.volume>0?'data-has-audio="true"':'muted'):''} data-media-start="${l.trim||0}" data-playback-rate="${l.speed||1}" data-volume="${l.volume??1}" data-fade-in="${Math.min(l.fadeIn||0,duration)}" data-fade-out="${Math.min(l.fadeOut||0,duration)}" style="${l.kind==='audio'?'display:none':style}" preload="auto"></${l.kind}>`;
    if(l.animation!=='none' && l.kind!=='audio') {
      const rest=`rotate(${l.rotation||0}deg) scale(${l.flipX?-1:1},${l.flipY?-1:1})`;
      const transform=l.animation==='rise'?`translateY(45px) ${rest}`:l.animation==='slide'?`translateX(-70px) ${rest}`:l.animation==='zoom'?`scale(.85) ${rest}`:rest;
      moves.push({id,frames:[{opacity:0,transform},{opacity:l.opacity??1,transform:rest}],start,duration:Math.min(.6,duration/2)});
    }

  }
  let offset=0;
  for(const s of doc.scenes) {
    html+=`<div id="s${esc(s.id)}" data-start="${offset}" data-duration="${s.duration}" data-track-index="0" style="position:absolute;inset:0;background:${s.background}"></div>`;
    s.layers.forEach((l,i)=>draw(l,offset+l.start,Math.min(l.duration,s.duration-l.start),i+1));
    if(s.transition!=='none') {
      const targets=[{id:'s'+s.id,opacity:1,rest:'none'},...s.layers.filter(l=>l.kind!=='audio'&&l.animation==='none'&&!l.hidden).map(l=>({id:'l'+l.id,opacity:l.opacity??1,rest:`rotate(${l.rotation||0}deg) scale(${l.flipX?-1:1},${l.flipY?-1:1})`}))];
      for(const t of targets)moves.push({id:t.id,frames:[{opacity:0,transform:s.transition==='slide'?`translateX(100px) ${t.rest==='none'?'':t.rest}`:t.rest},{opacity:t.opacity,transform:t.rest}],start:offset,duration:Math.min(.4,s.duration/2)});

    }
    offset+=s.duration;
  }
  doc.audio.forEach((l,i)=>draw(l,l.start,Math.min(l.duration,length-l.start),i+101));
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=${w}, height=${h}"><style>*{box-sizing:border-box}body{margin:0;background:#000}#root{position:relative;width:${w}px;height:${h}px;overflow:hidden}</style></head><body><div id="root" data-composition-id="main" data-no-timeline data-start="0" data-duration="${length}" data-width="${w}" data-height="${h}">${html}</div><script>for(const m of ${JSON.stringify(moves).replaceAll('<','\\u003c')}){const el=document.getElementById(m.id);if(!el)continue;const a=el.animate(m.frames,{duration:m.duration*1000,delay:m.start*1000,fill:'both',easing:'cubic-bezier(0.22,1,0.36,1)'});a.pause();a.currentTime=0;}</script></body></html>`;
}
export function parseSRT(text) {
  const seconds=s=>{const p=s.replace(',','.').split(':').map(Number);return p[0]*3600+p[1]*60+p[2]};
  return text.replaceAll('\r','').split(/\n\s*\n/).flatMap(b=>{const lines=b.trim().split('\n');const i=lines.findIndex(l=>l.includes('-->'));if(i<0)return[];const times=lines[i].match(/(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})/);if(!times)return[];return[{start:seconds(times[1]),end:seconds(times[2]),text:lines.slice(i+1).join('\n')}]}).filter(c=>c.end>c.start);
}
export function captionLayers(cues, duration) {return cues.filter(c=>Number.isFinite(c.start)&&Number.isFinite(c.end)&&c.start<duration&&c.end>Math.max(0,c.start)).map(c=>layer('text',{text:c.text,x:8,y:82,w:84,h:14,fontSize:40,align:'center',color:'#ffffff',bold:true,caption:true,start:Math.max(0,c.start),duration:Math.min(c.end,duration)-Math.max(0,c.start)}));}

// Preserve source time when a scene is split, including trimmed/speed-adjusted media.
export function clipLayerRange(l, from, to) {
  const start=Math.max(from,l.start),end=Math.min(to,l.start+l.duration);
  if(end<=start)return null;
  const n={...clone(l),id:uid(),start:start-from,duration:end-start};
  if(['video','audio'].includes(l.kind))n.trim=(l.trim||0)+(start-l.start)*(l.speed||1);
  if(start>l.start){n.fadeIn=0;n.animation='none'}
  if(end<l.start+l.duration)n.fadeOut=0;
  return n;
}
export function splitScene(s, time) {
  if(time<.25||s.duration-time<.25)throw Error('Leave at least 0.25 seconds on each side of the split');
  return [scene({...clone(s),duration:time,layers:s.layers.map(l=>clipLayerRange(l,0,time)).filter(Boolean)}),scene({...clone(s),id:uid(),name:s.name+' · continued',duration:s.duration-time,transition:'none',layers:s.layers.map(l=>clipLayerRange(l,time,s.duration)).filter(Boolean)})];
}
export function toSRT(doc) {
  let n=0; const stamp=v=>{const ms=Math.round(v*1000);return `${String(Math.floor(ms/3600000)).padStart(2,'0')}:${String(Math.floor(ms/60000)%60).padStart(2,'0')}:${String(Math.floor(ms/1000)%60).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`};
  return doc.scenes.flatMap((s,i)=>s.layers.filter(l=>l.caption).map(l=>`${++n}\n${stamp(sceneStart(doc,i)+l.start)} --> ${stamp(sceneStart(doc,i)+Math.min(s.duration,l.start+l.duration))}\n${l.text}\n`)).join('\n');
}
export const templates=[
  {name:'Project update',color:'#d8e9f0',title:'A new chapter.',sub:'Your team. Your progress. Your next big idea.',font:'Georgia'},
  {name:'Product launch',color:'#20283d',title:'Meet what’s next.',sub:'Introduce something extraordinary.',font:'Arial',ink:'#ffffff'},
  {name:'Learning moment',color:'#f5e6ca',title:'Let’s learn something.',sub:'One idea. A fresh perspective.',font:'Trebuchet MS'},
  {name:'Team introduction',color:'#dfe7d9',title:'Good things start here.',sub:'Meet the people behind the work.',font:'Georgia'},
  {name:'Quarterly report',color:'#e2e1f2',title:'The bigger picture.',sub:'A look at the quarter in motion.',font:'Arial'},
  {name:'Social story',color:'#f4dcd7',title:'Make it memorable.',sub:'Small moments. Lasting impressions.',font:'Georgia'}
];
export function applyTemplate(t) {return scene({name:t.name,duration:6,background:t.color,layers:[layer('shape',{x:7,y:12,w:6,h:1,fill:t.ink||'#3b514d',duration:6}),layer('text',{text:t.title,x:7,y:28,w:86,h:35,fontSize:100,font:t.font,color:t.ink||'#253e39',duration:6,animation:'rise'}),layer('text',{text:t.sub,x:7,y:70,w:80,h:12,fontSize:30,color:t.ink||'#465c57',duration:6,animation:'fade'})]});}
