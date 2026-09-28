// Browser permission prompts remain visible to the person doing the recording.
export async function recordMedia({mode,preview,onSaved,onState,onError}) {
  const streams=[];let audioContext,frame,scrollTimer,recorder;
  const cleanup=()=>{clearInterval(scrollTimer);cancelAnimationFrame(frame);streams.forEach(s=>s.getTracks().forEach(t=>t.stop()));audioContext?.close().catch(()=>{})};
  try {
    let output;
    if(mode==='voice'||mode==='camera'){
      output=await navigator.mediaDevices.getUserMedia({audio:true,video:mode==='camera'});streams.push(output);
    }else{
      const screen=await navigator.mediaDevices.getDisplayMedia({video:true,audio:true});streams.push(screen);
      const mic=await navigator.mediaDevices.getUserMedia({audio:true,video:mode==='both'});streams.push(mic);
      audioContext=new AudioContext();const mix=audioContext.createMediaStreamDestination();
      for(const source of [screen,mic])if(source.getAudioTracks().length)audioContext.createMediaStreamSource(new MediaStream(source.getAudioTracks())).connect(mix);
      let videos=screen.getVideoTracks();
      if(mode==='both'){
        const screenVideo=document.createElement('video'),cameraVideo=document.createElement('video');
        screenVideo.srcObject=screen;cameraVideo.srcObject=mic;screenVideo.muted=cameraVideo.muted=true;
        await Promise.all([screenVideo.play(),cameraVideo.play()]);
        const canvas=document.createElement('canvas');canvas.width=1920;canvas.height=1080;const context=canvas.getContext('2d');
        const draw=()=>{context.drawImage(screenVideo,0,0,1920,1080);context.drawImage(cameraVideo,1460,790,420,236);frame=requestAnimationFrame(draw)};draw();
        const canvasStream=canvas.captureStream(30);streams.push(canvasStream);videos=canvasStream.getVideoTracks();
      }
      output=new MediaStream([...videos,...mix.stream.getAudioTracks()]);streams.push(output);
      screen.getVideoTracks()[0].addEventListener('ended',()=>{if(recorder?.state==='recording')recorder.stop()});
    }
    const candidates=mode==='voice'?['audio/webm;codecs=opus','audio/webm']:['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm'];
    const mimeType=candidates.find(m=>MediaRecorder.isTypeSupported(m));
    recorder=new MediaRecorder(output,mimeType?{mimeType}:{});const chunks=[];
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
    recorder.onerror=e=>{cleanup();onState(false);onError(Error(e.error?.message||'Recording failed'))};
    recorder.onstop=async()=>{cleanup();onState(false);try{await onSaved(new File(chunks,`Recording-${Date.now()}.webm`,{type:recorder.mimeType}))}catch(e){onError(e)}};
    if(preview){preview.hidden=mode==='voice';preview.srcObject=output;await preview.play()}
    recorder.start(1000);onState(true);
    const prompter=document.querySelector('#prompter-stage');
    if(prompter){prompter.hidden=false;prompter.scrollTop=0;scrollTimer=setInterval(()=>{prompter.scrollTop+=(+(document.querySelector('#prompter-speed')?.value||30))/20},50)}
    return {rec:recorder,stop:()=>{if(recorder.state==='recording')recorder.stop()},cleanup};
  }catch(e){cleanup();onState(false);throw e}
}
