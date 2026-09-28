import test from 'node:test';
import assert from 'node:assert/strict';
import {blank,scene,layer,compile,parseSRT,captionLayers,toSRT,total} from '../web/vids-core.js';
test('render escapes text and retains actual media trim, speed, gain and fades',()=>{
  const d=blank();d.scenes=[scene({duration:6,layers:[layer('text',{text:'<script>alert("x")</script>'}),layer('video',{url:'/media/clip.mp4',trim:2,speed:.8,volume:.5,fadeOut:2,duration:6})]})];
  const html=compile(d);assert.ok(html.includes('&lt;script&gt;'));assert.ok(!html.includes('<script>alert'));
  for(const attr of ['data-media-start="2"','data-playback-rate="0.8"','data-volume="0.5"','data-fade-out="2"'])assert.ok(html.includes(attr));
});
test('scene layers clip at scene boundaries; shared music spans the full video',()=>{
  const d=blank();d.scenes=[scene({duration:3,layers:[layer('text',{id:'hello',start:2,duration:8})]}),scene({duration:4})];d.audio=[layer('audio',{id:'score',url:'/media/score.mp3',duration:7,fadeOut:3})];const html=compile(d);
  assert.match(html,/id="lhello" data-start="2" data-duration="1"/);assert.match(html,/id="lscore" data-start="0" data-duration="7"/);assert.equal(total(d),7);
});
test('SRT import/export preserves cue timing and text',()=>{
  const text='1\n00:00:01,250 --> 00:00:02,500\nHello world\n';const cues=parseSRT(text);assert.deepEqual(cues,[{start:1.25,end:2.5,text:'Hello world'}]);const d=blank();d.scenes[0].layers=captionLayers(cues,5);assert.equal(toSRT(d).trim(),text.trim());
});
test('hidden layers and disabled captions stay out of exported frames',()=>{
  const d=blank();d.captions=false;d.scenes[0].layers=[layer('text',{text:'hidden',hidden:true}),layer('text',{text:'caption',caption:true})];assert.ok(!compile(d).includes('>hidden<'));assert.ok(!compile(d).includes('>caption<'));
});

test('splitting scenes preserves source time for trimmed, slowed media and avoids duplicate fades',async()=>{
  const {splitScene}=await import('../web/vids-core.js');
  const original=scene({duration:10,layers:[layer('video',{start:1,duration:8,trim:4,speed:.5,fadeIn:1,fadeOut:2}),layer('text',{start:6,duration:4,text:'Later'})]});
  const [a,b]=splitScene(original,5);
  assert.equal(a.duration+b.duration,10);assert.equal(a.layers[0].trim,4);assert.equal(a.layers[0].duration,4);assert.equal(a.layers[0].fadeOut,0);
  assert.equal(b.layers[0].trim,6);assert.equal(b.layers[0].start,0);assert.equal(b.layers[0].duration,4);assert.equal(b.layers[0].fadeIn,0);assert.equal(b.layers[1].start,1);
  assert.notEqual(a.layers[0].id,b.layers[0].id);assert.throws(()=>splitScene(original,0));
});
