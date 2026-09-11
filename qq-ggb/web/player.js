(() => {
  'use strict';
  // Construction coordinates and branches have already been checked in Sage.
  // Number arithmetic below is exclusively screen projection and animation.
  const offlineSource = '<!doctype html>\n' + document.documentElement.outerHTML;
  const data = JSON.parse(document.getElementById('geometry-data').textContent);
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const colors = {gold:'#FFC857',fg:'#E8F0F7',circle:'#56B4D3',line:'#8AC6D9',target:'#5DE2A5',alert:'#FF7A90'};
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const points = Object.fromEntries(Object.entries(data.points).map(([id,p]) => [id,{...p,xy:p.xy.map(Number)}]));
  const steps = data.steps.map(s => ({...s,frame:s.frame.map(Number),ends:s.ends?.map(p=>p.map(Number))}));
  const state = {step:0,progress:1,playing:false,animating:false,hold:0,speed:1,labels:true,helpers:true,focus:false,autoCamera:true};
  let width=1,height=1,camera={x:0,y:0,scale:100},tween=null,raf=0,lastTime=0;
  const pointNodes={},paths=[];

  function svg(tag,attributes={},parent) {
    const node=document.createElementNS(NS,tag);
    for(const [k,v] of Object.entries(attributes)) node.setAttribute(k,String(v));
    if(parent) parent.append(node);
    return node;
  }
  const ease=t=>t*t*(3-2*t);
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const label=id=>points[id].label;
  const project=p=>[(p[0]-camera.x)*camera.scale+width/2,(p[1]-camera.y)*camera.scale+height/2];
  const unproject=p=>[(p[0]-width/2)/camera.scale+camera.x,(p[1]-height/2)/camera.scale+camera.y];

  $('unit-circle').setAttribute('d',data.initial.path);
  for(const s of steps) paths.push(svg('path',{'class':'construction','data-step':s.e,'data-op':s.op,'pathLength':1},$('drawables')));
  for(const [id,p] of Object.entries(points)) {
    const g=svg('g',{'data-point':id},$('points'));
    const target=data.verified.targets.includes(id);
    const dot=svg('circle',{r:target?4.7:3.2,fill:target?colors.target:colors.fg},g);
    const text=svg('text',{'class':'point-label'+(target?' target-label':'')},g);
    text.textContent=p.label;
    pointNodes[id]={g,dot,text};
  }
  const guide=svg('path',{'class':'radius-guide'},$('reference-guide'));
  const markers=[0,1].map(()=>{
    const g=svg('g',{},$('references'));
    return {g,ring:svg('circle',{r:11,fill:'none','stroke-width':1.8},g),dot:svg('circle',{r:3.7},g)};
  });
  const target=points.ggb_Q.xy;
  svg('path',{d:`M 0 0 L 1 0 M 0 0 L ${target[0]} ${target[1]}`,'class':'result-ray'},$('result-world'));
  svg('path',{d:data.anglePath,'class':'result-arc'},$('result-world'));
  for(let i=0;i<=12;i++) {
    const b=document.createElement('button'); b.className='tick'; b.textContent=String(i).padStart(2,'0');
    b.setAttribute('aria-label',i===0?'初始条件':`跳到第 ${i} E`);
    b.addEventListener('click',()=>jump(i)); $('ticks').append(b);
  }

  function frameForStep() {
    return state.focus?data.resultFrame.map(Number):state.step===0?data.initial.frame.map(Number):steps[state.step-1].frame;
  }
  function fitted(frame) {
    const [x0,y0,x1,y1]=frame;
    return {x:(x0+x1)/2,y:(y0+y1)/2,scale:Math.min(Math.max(80,width-80)/(x1-x0),Math.max(60,height-72)/(y1-y0))};
  }
  function fit(animate=true) {
    state.autoCamera=true;
    const to=fitted(frameForStep());
    if(animate&&!reducedMotion) tween={from:{...camera},to,started:performance.now()};
    else {camera=to;tween=null;}
    requestFrame();
  }
  // Clip the already known line to the display viewport. This creates no
  // construction point and never participates in an incidence or target test.
  function linePath(ends) {
    const p=project(ends[0]),q=project(ends[1]);
    const dx=q[0]-p[0],dy=q[1]-p[1]; let low=0,high=1;
    for(const [a,b] of [[-dx,p[0]+8],[dx,width+8-p[0]],[-dy,p[1]+8],[dy,height+8-p[1]]]) {
      if(a===0) {if(b<0)return '';continue;}
      const t=b/a;
      if(a<0) low=Math.max(low,t);else high=Math.min(high,t);
      if(low>high) return '';
    }
    const a=unproject([p[0]+low*dx,p[1]+low*dy]),b=unproject([p[0]+high*dx,p[1]+high*dy]);
    return `M ${a[0]} ${a[1]} L ${b[0]} ${b[1]}`;
  }

  function render() {
    $('scene').setAttribute('viewBox',`0 0 ${width} ${height}`);
    $('world').setAttribute('transform',`translate(${width/2} ${height/2}) scale(${camera.scale}) translate(${-camera.x} ${-camera.y})`);
    const current=steps[state.step-1],progress=state.progress;
    const drawProgress=ease(clamp((progress-.16)/.66,0,1));
    for(let i=0;i<paths.length;i++) {
      const path=paths[i],s=steps[i],active=s.e===state.step;
      path.style.display=s.e<=state.step?'':'none';
      path.classList.toggle('current',active);
      if(s.e>state.step) continue;
      path.setAttribute('d',s.op==='circle'?s.path:linePath(s.ends));
      // Keep dash lengths in the path's coordinate system. Combining
      // pathLength=1 with non-scaling-stroke makes Chromium repeat tiny dashes.
      path.style.vectorEffect='none';
      path.style.strokeWidth=String((active?2.7:1.35)/camera.scale);
      path.style.stroke=active?colors.gold:s.op==='circle'?colors.circle:colors.line;
      path.style.opacity=active ? (state.focus ? .36 : 1) : state.helpers ? (state.step===12 ? .14 : .36) : 0;
      path.style.strokeDasharray=active&&progress<1?'1 1':'none';
      path.style.strokeDashoffset=active&&progress<1?String(1-drawProgress):'0';
    }
    const newAlpha=progress>=1?1:ease(clamp((progress-.82)/.18,0,1));
    const refs=current?.refs||[];
    const visibleLabels=[];
    for(const [id,p] of Object.entries(points)) {
      const node=pointNodes[id],isTarget=data.verified.targets.includes(id),base=id==='O'||id==='A';
      const born=p.birth<=state.step;
      const useful=base||isTarget||refs.includes(id)||p.birth===state.step;
      const visible=born&&(!state.focus||base||isTarget)&&(state.helpers||useful);
      const alpha=p.birth===state.step&&state.step!==0?newAlpha:1;
      node.g.style.display=visible?'':'none';node.g.style.opacity=String(alpha);
      if(!visible)continue;
      const [x,y]=project(p.xy);node.dot.setAttribute('cx',x);node.dot.setAttribute('cy',y);
      node.dot.style.opacity=useful?1:.6;
      const showLabel=state.labels&&(useful||(p.birth>=state.step-1&&p.lastUse>=state.step));
      node.text.style.display=showLabel?'':'none';
      if(showLabel&&alpha>0) visibleLabels.push({id,p,node,x,y,priority:base||isTarget?0:refs.includes(id)?1:2});
    }
    // Layout only: separate labels in screen pixels without moving any point.
    const boxes=[];
    visibleLabels.sort((a,b)=>a.priority-b.priority);
    for(const r of visibleLabels) {
      const {p,node,x,y}=r,font=width<650?13:15,textWidth=p.label.length*font*.73;
      const [ox,oy]=p.offset;
      const options=[[ox,oy],[-ox,oy],[ox,-oy],[-ox,-oy],[ox,oy+18],[-ox,oy-18]];
      let chosen=null,best=Infinity;
      for(const [dx,dy] of options) {
        const tx=clamp(x+dx,8,width-textWidth-8),ty=clamp(y+dy,18,height-8);
        const box={x:tx-3,y:ty-font-2,w:textWidth+6,h:font+6};
        let cost=boxes.filter(b=>box.x<b.x+b.w&&box.x+box.w>b.x&&box.y<b.y+b.h&&box.y+box.h>b.y).length*100;
        cost+=Math.abs(tx-x-dx)+Math.abs(ty-y-dy);
        if(cost<best){best=cost;chosen={tx,ty,box};}
      }
      node.text.setAttribute('x',chosen.tx);node.text.setAttribute('y',chosen.ty);boxes.push(chosen.box);
    }
    let referenceAlpha=state.focus?0:progress<1?clamp(progress/.12,0,1):state.playing?Math.max(0,1-state.hold/400):.8;
    $('references').style.opacity=String(referenceAlpha);
    $('reference-guide').style.opacity=String(referenceAlpha);
    for(let i=0;i<2;i++) {
      const m=markers[i],id=refs[i];m.g.style.display=id?'':'none';if(!id)continue;
      const [x,y]=project(points[id].xy);m.g.setAttribute('transform',`translate(${x} ${y})`);
      const color=current.op==='circle'&&i===0?colors.alert:colors.gold;
      m.ring.setAttribute('stroke',color);m.dot.setAttribute('fill',color);
    }
    guide.style.display=current?.op==='circle'?'':'none';
    if(current?.op==='circle') {
      const a=points[refs[0]].xy,b=points[refs[1]].xy;
      guide.setAttribute('d',`M ${a[0]} ${a[1]} L ${b[0]} ${b[1]}`);
    }
    const done=state.step===12&&progress>=1;
    $('result-world').style.display=done?'':'none';
    $('result-note').hidden=!done;
    $('start-note').hidden=state.step!==0;
    $('scene').dataset.step=String(state.step);
    $('scene').dataset.complete=String(progress>=1);
  }

  function updateUI() {
    $('step-count').textContent=String(state.step).padStart(2,'0');
    $('timeline').value=state.step;$('timeline').style.setProperty('--progress',`${state.step/12*100}%`);
    $('timeline').setAttribute('aria-valuetext',`${state.step} E，共 12 E`);
    const s=steps[state.step-1];
    $('line-count').textContent=s?s.counts.lines:0;$('circle-count').textContent=s?s.counts.circles:0;
    $('previous').disabled=state.step===0;$('next').disabled=state.step===12;
    $('focus-result').disabled=state.step!==12||state.progress<1;
    $('focus-result').setAttribute('aria-pressed',state.focus);
    $('play').setAttribute('aria-label',state.playing?'暂停':state.step===12?'重新播放':'播放');
    $('play-icon').innerHTML=state.playing?'<path d="M7 5h3v14H7zM15 5h3v14h-3z"/>':'<path d="m9 5 11 7-11 7z"/>';
    for(const [i,tick] of [...$('ticks').children].entries()) {tick.classList.toggle('active',i===state.step);if(i===state.step)tick.setAttribute('aria-current','step');else tick.removeAttribute('aria-current');}
    const note=!s?'每画一条直线或一个圆，记 1 E':s.op==='line'?`直线 · ${label(s.refs[0])} — ${label(s.refs[1])}`:`圆 · 圆心 ${label(s.refs[0])} · 经过 ${label(s.refs[1])}`;
    $('step-note').textContent=note;
    $('scene-description').textContent=`第 ${state.step} E，共 12 E。${note}。${state.step===12?'完成后得到相邻顶点 B₊ 和 B₋。':''}`;
  }
  function requestFrame() {if(!raf)raf=requestAnimationFrame(tick);}
  function tick(now) {
    raf=0;const dt=lastTime?Math.min(now-lastTime,60):0;lastTime=now;
    if(tween) {
      const t=clamp((now-tween.started)/550,0,1),v=ease(t);
      for(const k of ['x','y','scale'])camera[k]=tween.from[k]+(tween.to[k]-tween.from[k])*v;
      if(t===1)tween=null;
    }
    if(state.animating||state.playing) {
      if(state.progress<1) {
        state.progress=clamp(state.progress+dt*state.speed/(reducedMotion?250:1650),0,1);
        if(state.progress===1) {state.animating=false;updateUI();}
      } else if(state.playing) {
        state.hold+=dt*state.speed;
        if(state.hold>650) {
          if(state.step===12) {state.playing=false;updateUI();}
          else setStep(state.step+1,true);
        }
      }
    }
    render();
    if(state.playing||state.animating||tween)requestFrame();else lastTime=0;
  }
  function setStep(n,animate=false) {
    state.step=clamp(n,0,12);state.progress=animate?0:1;state.animating=animate;state.hold=0;state.focus=false;
    fit(animate);updateUI();requestFrame();
    try{history.replaceState(null,'',`#e=${state.step}`);}catch{}
  }
  function jump(n,animate=false) {state.playing=false;setStep(n,animate);}
  function pause() {state.playing=false;state.animating=false;updateUI();requestFrame();}
  function togglePlay() {
    if(state.playing){pause();return;}
    state.playing=true;
    if(state.step===12&&state.progress===1)setStep(0,false);
    if(state.progress===1)setStep(state.step+1,true);
    updateUI();requestFrame();
  }
  $('play').addEventListener('click',togglePlay);
  $('previous').addEventListener('click',()=>jump(state.step-1));
  $('next').addEventListener('click',()=>jump(state.step+1,true));
  $('restart').addEventListener('click',()=>jump(0));
  $('timeline').addEventListener('input',e=>jump(Number(e.target.value)));
  $('speed').addEventListener('change',e=>state.speed=Number(e.target.value));
  for(const key of ['labels','helpers']) $(key).addEventListener('click',()=>{state[key]=!state[key];$(key).setAttribute('aria-pressed',state[key]);requestFrame();});
  $('focus-result').addEventListener('click',()=>{pause();state.focus=!state.focus;fit();updateUI();});
  $('fit').addEventListener('click',()=>{state.focus=false;fit();updateUI();});
  function zoom(factor,pixel=[width/2,height/2]) {
    const anchor=unproject(pixel),base=fitted(frameForStep()).scale;
    camera.scale=clamp(camera.scale*factor,base*.5,base*8);
    camera.x=anchor[0]-(pixel[0]-width/2)/camera.scale;camera.y=anchor[1]-(pixel[1]-height/2)/camera.scale;
    state.autoCamera=false;tween=null;requestFrame();
  }
  $('zoom-in').addEventListener('click',()=>zoom(1.25));$('zoom-out').addEventListener('click',()=>zoom(.8));
  $('stage').addEventListener('wheel',e=>{e.preventDefault();const r=$('stage').getBoundingClientRect();zoom(Math.exp(-clamp(e.deltaY,-100,100)*.003),[e.clientX-r.left,e.clientY-r.top]);},{passive:false});
  let drag=null;
  $('stage').addEventListener('pointerdown',e=>{
    if(e.target.closest('button')||e.button>0)return;
    drag={id:e.pointerId,x:e.clientX,y:e.clientY,camera:{...camera}};tween=null;state.autoCamera=false;
    $('stage').setPointerCapture(e.pointerId);$('stage').classList.add('dragging');
  });
  $('stage').addEventListener('pointermove',e=>{
    if(!drag||drag.id!==e.pointerId)return;
    camera.x=drag.camera.x-(e.clientX-drag.x)/camera.scale;camera.y=drag.camera.y-(e.clientY-drag.y)/camera.scale;requestFrame();
  });
  const endDrag=()=>{drag=null;$('stage').classList.remove('dragging');};
  $('stage').addEventListener('pointerup',endDrag);$('stage').addEventListener('pointercancel',endDrag);$('stage').addEventListener('lostpointercapture',endDrag);
  $('stage').addEventListener('dblclick',()=>fit());
  const about=$('about');if(about.open)about.close();
  $('info').addEventListener('click',()=>{pause();about.showModal();});
  $('close-info').addEventListener('click',()=>about.close());
  about.addEventListener('click',e=>{const r=about.getBoundingClientRect();if(e.target===about&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))about.close();});
  function download(name,type,content) {
    const url=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');
    a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);
  }
  $('download-certificate').addEventListener('click',()=>download('regular-17-12e-certificate.json','application/json',JSON.stringify(data.certificate,null,2)+'\n'));
  $('download-page').addEventListener('click',()=>download('regular-17-12e.html','text/html;charset=utf-8',offlineSource));
  $('fullscreen').hidden=!document.fullscreenEnabled;
  $('fullscreen').addEventListener('click',async()=>{
    try {if(document.fullscreenElement)await document.exitFullscreen();else await $('player').requestFullscreen();}
    catch {$('step-note').textContent='当前浏览器未开放全屏，可使用浏览器全屏功能。';}
  });
  document.addEventListener('fullscreenchange',()=>{$('fullscreen').setAttribute('aria-label',document.fullscreenElement?'退出全屏':'全屏');});
  document.addEventListener('keydown',e=>{
    if(about.open||e.target.closest('input,select,button'))return;
    const actions={' ':togglePlay,ArrowLeft:()=>jump(state.step-1),ArrowRight:()=>jump(state.step+1,true),Home:()=>jump(0),End:()=>jump(12)};
    if(actions[e.key]){e.preventDefault();actions[e.key]();}
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
  new ResizeObserver(()=>{width=$('stage').clientWidth;height=$('stage').clientHeight;if(state.autoCamera)fit(false);requestFrame();}).observe($('stage'));
  width=$('stage').clientWidth;height=$('stage').clientHeight;
  const initial=Number(new URLSearchParams(location.hash.slice(1)).get('e')||0);
  setStep(Number.isInteger(initial)?clamp(initial,0,12):0,false);
})();
