/* Build and reopen a native GGB using the locally installed GeoGebra engine.
 * GeoGebra uses numerical geometry. The exact proof is export_geometry.py;
 * the tolerance below checks application compatibility, never minimality or
 * mathematical correctness. No user's browser or GeoGebra window is opened.
 */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const {parseArgs} = require('node:util');
const {values: args} = parseArgs({options: {
  assets: {type: 'string', default: '/Applications/GeoGebra Classic 6.app/Contents/Resources/app/html'},
  deploy: {type: 'string', default: path.join(__dirname, 'deployggb.js')},
  playwright: {type: 'string', default: 'playwright'},
}});
const {chromium} = require(args.playwright);
const specBytes = fs.readFileSync(path.join(__dirname, 'geometry.json'));
const spec = JSON.parse(specBytes);
const output = path.join(__dirname, '正十七边形-12E.ggb');
const assetRoot = path.resolve(args.assets);
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const html = `<!doctype html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#07101f}</style><script src="/deployggb.js"></script>
</head><body><div id="ggb"></div><script>
const app = new GGBApplet({id:'ggbApplet',appName:'classic',width:1400,height:900,
showToolBar:false,showMenuBar:false,showAlgebraInput:false,perspective:'G',language:'zh',
enable3d:false,enableCAS:false,appletOnLoad:function(api){window.api=api;window.ready=true;}},true);
app.setHTML5Codebase('/assets/web3d/');app.inject('ggb');
</script></body></html>`;

async function main() {
  const deploy = fs.readFileSync(args.deploy);
  if (!fs.existsSync(path.join(assetRoot, 'web3d/web3d.nocache.js'))) throw Error('GeoGebra assets missing');
  const server = http.createServer((req, res) => {
    if (req.url === '/') {res.setHeader('Content-Type','text/html');res.end(html);return;}
    if (req.url === '/deployggb.js') {res.setHeader('Content-Type','application/javascript');res.end(deploy);return;}
    const relative = decodeURIComponent(req.url.split('?')[0]);
    if (!relative.startsWith('/assets/')) {res.writeHead(404);res.end();return;}
    const file = path.resolve(assetRoot, '.' + relative.slice('/assets'.length));
    if (!file.startsWith(assetRoot + path.sep)) {res.writeHead(404);res.end();return;}
    res.setHeader('Content-Type', {'.js':'application/javascript','.css':'text/css',
      '.html':'text/html','.png':'image/png','.svg':'image/svg+xml',
      '.woff2':'font/woff2'}[path.extname(file)] || 'application/octet-stream');
    fs.createReadStream(file).on('error', () => {res.writeHead(404);res.end();}).pipe(res);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({headless:true});
    const page = await browser.newPage({viewport:{width:1400,height:900}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    // The app and its test inputs stay on loopback; remote requests are blocked.
    const origin = 'http://127.0.0.1:' + server.address().port;
    await page.route('**/*', route => route.request().url().startsWith(origin + '/')
      ? route.continue() : route.abort());
    await page.goto(origin);
    await page.waitForFunction(() => window.ready && window.api, {}, {timeout:45000});
    const built = await page.evaluate(spec => {
      const api = window.api;
      const run = command => {if (!api.evalCommand(command)) throw Error('Command failed: ' + command);};
      const patch = (name, fields) => {
        // Free objects may include an <expression> sibling before <element>.
        const xml = new DOMParser().parseFromString('<root>'+api.getXML(name)+'</root>', 'application/xml');
        const element = xml.querySelector('element');
        if(!element)throw Error('Missing element XML: '+name);
        for (const [tag, attrs] of Object.entries(fields)) {
          let child = element.querySelector(tag);
          if (!child) {child=xml.createElement(tag);element.appendChild(child);}
          for (const [key,value] of Object.entries(attrs)) child.setAttribute(key,String(value));
        }
        api.evalXML(new XMLSerializer().serializeToString(element));
      };
      const point = name => [api.getXcoord(name), api.getYcoord(name)];
      const distance = (a,b) => Math.hypot(a[0]-Number(b[0]),a[1]-Number(b[1]));
      run('O=(0,0)');run('A=(1,0)');run('c=Circle(O,A)');
      const nativeSteps = {O:1,A:2,c:api.getConstructionSteps()};
      const indices = {};
      for (const entry of spec.certificate.construction.program) {
        const name=spec.labels[entry.id];
        if (entry.op==='line') run(`${name}=Line(${entry.through.map(r=>spec.labels[r]).join(',')})`);
        else if (entry.op==='circle') run(`${name}=Circle(${spec.labels[entry.center]},${spec.labels[entry.through]})`);
        else {
          const refs=entry.objects.map(r=>spec.labels[r]).join(',');
          const isLinePair=entry.objects.every(r=>api.getObjectType(spec.labels[r])==='line');
          if (isLinePair) {run(`${name}=Intersect(${refs})`);indices[name]=null;}
          else {
            const expected=spec.points[name].xy;
            run(`${name}=Intersect(${refs},1)`);
            const firstDistance=distance(point(name),expected);
            if (firstDistance<1e-9) indices[name]=1;
            else {run(`${name}=Intersect(${refs},2)`);indices[name]=2;}
          }
          if (distance(point(name),spec.points[name].xy)>1e-9) throw Error('Intersection branch mismatch: '+name);
        }
        nativeSteps[name]=api.getConstructionSteps();
      }
      const geometryEnd=api.getConstructionSteps();
      const descriptions=['初始点 O、A 与单位圆 · 免费', ...spec.steps.map(s=>s.op==='line'
        ? `直线 ${s.refs.join('、')}` : `以 ${s.refs[0]} 为圆心，过 ${s.refs[1]} 画圆`)];
      patch('c',{objColor:{r:224,g:91,b:238,alpha:0},lineStyle:{thickness:3,opacity:255},
        show:{object:true,label:false},layer:{val:2}});
      for (const [i,step] of spec.steps.entries()) {
        const rgb=[255,200,87], old=[55,104,131];
        const color={r:old[0],g:old[1],b:old[2],alpha:0};
        const nextNativeStep=i+1<spec.steps.length?nativeSteps[spec.steps[i+1].label]:geometryEnd+1;
        const active=`ConstructionStep() >= ${nativeSteps[step.label]} && ConstructionStep() < ${nextNativeStep}`;
        ['dynamicr','dynamicg','dynamicb'].forEach((key,i)=>color[key]=`If(${active},${rgb[i]}/255,${old[i]}/255)`);
        patch(step.label,{objColor:color,lineStyle:{thickness:2,opacity:255},
          show:{object:true,label:false},layer:{val:1},
          caption:{val:step.e+' E · '+descriptions[step.e]}});
      }
      const offsets={O:[-22,34],A:[16,20],C:[-14,23],D:[10,-15],E:[12,22],F:[-15,23],
        G:[12,-12],H:[10,-16],I:[12,22],J:[-14,-13],K:[-18,23],L:[-27,-12],
        M:[12,25],N:[14,23],U:[-16,24],P:[12,-17],B_plus:[17,-11],B_minus:[17,22]};
      for (const name of Object.keys(spec.points)) {
        const target=name==='B_plus'||name==='B_minus';
        patch(name,{show:{object:true,label:true},
          objColor:target?{r:85,g:224,b:175,alpha:0}:{r:217,g:230,b:242,alpha:0},
          pointSize:{val:target?5:3.5},labelOffset:{x:offsets[name][0],y:offsets[name][1]},
          layer:{val:4},labelMode:{val:target?3:0},
          ...(target?{caption:{val:name==='B_plus'?'B₊':'B₋'}}:{})});
      }
      // Only these two initial points are free construction inputs.
      api.setFixed('O',false);api.setFixed('A',false);
      const doc=new DOMParser().parseFromString(api.getXML(),'application/xml');
      doc.querySelector('euclidianView bgColor').setAttribute('r','7');
      doc.querySelector('euclidianView bgColor').setAttribute('g','16');
      doc.querySelector('euclidianView bgColor').setAttribute('b','31');
      doc.querySelector('construction').setAttribute('title','正十七边形相邻顶点 · 12 E');
      doc.querySelector('construction').setAttribute('author','QQ 讨论组提供原图（首创者未确认）；euclid-min 改写与核验');
      doc.querySelector('gui font').setAttribute('size','18');
      // The native navigation bar belongs to the file's view settings. It
      // creates no construction objects and adds no rows after the targets.
      const nav=doc.createElement('consProtNavigationBar');
      for(const [key,value] of Object.entries({id:'1',playButton:true,playDelay:2,protButton:true}))
        nav.setAttribute(key,String(value));
      doc.querySelector('gui').appendChild(nav);
      api.setXML(new XMLSerializer().serializeToString(doc));
      api.setAxesVisible(false,false);api.setGridVisible(false);
      api.setCoordSystem(-3.9,3.1,-2.3,2.2);
      return {indices,nativeSteps,geometryEnd,version:api.getVersion()};
    }, spec);
    console.log('Built native GGB with',Object.keys(built.indices).length,'intersection bindings');
    const base64 = await page.evaluate(() => new Promise(resolve => api.getBase64(resolve)));
    const bytes = Buffer.from(base64,'base64');
    fs.writeFileSync(output,bytes);
    // Reload the actual archive, then verify geometry and native playback.
    await page.evaluate(b64=>new Promise(resolve=>api.setBase64(b64,resolve)),base64);
    await page.waitForFunction(()=>api.exists('B_minus'));
    // Regression for the native Construction Protocol (the fourth native row
    // is the first paid line). getVisible() also checks native availability.
    const nativeChecks = await page.evaluate(({spec,built}) => {
      const total=api.getConstructionSteps();
      // This scripting command creates no object; validate its effect below
      // instead of interpreting evalCommand's return as a creation result.
      const setStep=n=>api.evalCommand(`SetConstructionStep(${n})`);
      if(total!==built.geometryEnd || total!==31 || api.getObjectNumber()!==31)
        throw Error('Non-geometric or trailing construction entries: '+total);
      let statesChecked=0;
      const forward=Array.from({length:total+1},(_,i)=>i);
      for(const n of [...forward,...forward.slice().reverse()]) {
        setStep(n);
        for(const [name,birth] of Object.entries(built.nativeSteps)) {
          const expected=birth<=n;
          if(api.exists(name)!==expected||api.getVisible(name)!==expected)
            throw Error(`Native visibility mismatch: step ${n}, ${name}`);
        }
        const drawn=spec.steps.filter(s=>built.nativeSteps[s.label]<=n);
        for(const s of drawn) {
          const expected=s===drawn.at(-1)?'#FFC857':'#376883';
          if(api.getColor(s.label)!==expected)throw Error(`Native highlight mismatch: step ${n}, ${s.label}`);
        }
        statesChecked++;
      }
      setStep(total);
      const doc=new DOMParser().parseFromString(api.getXML(),'application/xml');
      const nav=doc.querySelector('gui consProtNavigationBar');
      if(!nav || nav.getAttribute('playButton')!=='true')throw Error('Native playback bar missing');
      const elements=[...doc.querySelectorAll('construction > element')];
      if(elements.some(e=>!['point','line','conic'].includes(e.getAttribute('type'))))
        throw Error('Presentation controls leaked into the construction');
      if(elements.at(-1).getAttribute('label')!=='B_minus')throw Error('Trailing objects after target');
      return {geometry_end_step:built.geometryEnd,total_protocol_steps:total,
        first_paid_line_step:built.nativeSteps[spec.steps[0].label],
        last_paid_circle_step:built.nativeSteps[spec.steps.at(-1).label],
        target_binding_steps:[built.nativeSteps.B_plus,built.nativeSteps.B_minus],
        forward_and_backward:true,checked_states:statesChecked,
        geometry_visibility:true,current_draw_highlight:true,
        native_navigation_bar:true,non_geometric_entries:0,trailing_entries_after_targets:0};
    }, {spec,built});
    const checks = await page.evaluate(spec => {
      const compare=(origin=[0,0],vector=[1,0])=>Object.entries(spec.points).map(([name,p])=>{
        const [x,y]=p.xy.map(Number);
        const expected=[origin[0]+vector[0]*x-vector[1]*y,origin[1]+vector[1]*x+vector[0]*y];
        const error=Math.hypot(api.getXcoord(name)-expected[0],api.getYcoord(name)-expected[1]);
        if (!Number.isFinite(error)||error>1e-8) throw Error('Saved/runtime geometry mismatch: '+name+' '+error);
        return error;
      });
      const initialErrors=compare();
      const count=api.getAllObjectNames().map(n=>api.getObjectType(n));
      if(count.filter(t=>t==='point').length!==18||count.filter(t=>t==='line').length!==3||count.filter(t=>t==='circle').length!==10)
        throw Error('Unexpected geometric object count: '+JSON.stringify(count));
      const transformations=[];
      for (const [origin,vector] of [[[2,3],[1.5,0.4]],[[-2,1],[-0.6,1.2]],[[0,0],[-1,-0.3]]]) {
        api.setCoords('O',...origin);api.setCoords('A',origin[0]+vector[0],origin[1]+vector[1]);
        transformations.push(Math.max(...compare(origin,vector)));
      }
      api.setCoords('O',0,0);api.setCoords('A',1,0);compare();
      return {max_initial_coordinate_error:Math.max(...initialErrors),similarity_errors:transformations,
        saved_point_count:18,saved_line_count:3,saved_circle_count_including_initial:10};
    }, spec);
    checks.native_construction_protocol=nativeChecks;
    // Exercise the actual native navigation controls in the headless app.
    const navButtons=page.locator('.navbar_leftPanel button');
    const playButton=page.locator('.navbar_playPanel button');
    const delayInput=page.locator('.navbar_playPanel input');
    if(await navButtons.count()!==4||await playButton.count()!==1)
      throw Error('Unexpected native navigation layout');
    const stoppedIcon=await playButton.locator('img').getAttribute('src');
    await navButtons.nth(0).click();
    for(let n=0;n<4&&!await page.evaluate(()=>api.exists('f'));n++)await navButtons.nth(2).click();
    if(!await page.evaluate(()=>api.getVisible('f')&&!api.exists('C')&&api.getColor('f')==='#FFC857'))
      throw Error('Native Next failed to reveal the first paid line');
    await navButtons.nth(1).click();
    if(await page.evaluate(()=>api.exists('f')))throw Error('Native Previous failed');
    await navButtons.nth(3).click();
    if(!await page.evaluate(()=>api.getVisible('B_minus')))throw Error('Native Last failed');
    await navButtons.nth(0).click();
    await delayInput.fill('0.1');await delayInput.press('Enter');
    await playButton.click();
    await page.waitForFunction(()=>api.getVisible('f'),{}, {timeout:15000});
    await playButton.click();
    if(await playButton.locator('img').getAttribute('src')!==stoppedIcon)
      throw Error('Native Pause failed');
    await playButton.click();
    await page.waitForFunction(stoppedIcon=>api.getVisible('B_minus') &&
      document.querySelector('.navbar_playPanel button img').getAttribute('src')===stoppedIcon,
    stoppedIcon,{timeout:20000});
    if(!await page.evaluate(()=>api.getConstructionSteps()===31&&api.getObjectNumber()===31))
      throw Error('Playback did not finish at the final target');
    await delayInput.fill('2');await delayInput.press('Enter');
    nativeChecks.navigation_buttons=true;
    nativeChecks.play_pause_buttons=true;
    nativeChecks.automatic_playback_stops_at=31;
    if(await page.locator('[role="dialog"]').count())throw Error('Unexpected GeoGebra dialog');
    for(const step of [3,4,13,built.geometryEnd]) {
      await page.evaluate(step=>api.evalCommand(`SetConstructionStep(${step})`),step);
      await page.screenshot({path:path.join(__dirname,`preview-native-${step}.png`)});
    }
    const report={passed:true,geogebra_version:built.version,
      certificate_sha256:spec.certificate_sha256,construction_sha256:spec.construction_sha256,
      oracle_sha256:sha256(specBytes),ggb_sha256:sha256(bytes),
      deploy_script_sha256:sha256(deploy),geogebra_intersection_indices:built.indices,
      compatibility_checks:checks,page_errors:errors,
      scope:'Native file reload, numerical compatibility, similarity transforms and native Construction Protocol playback with no non-geometric construction entries. Exact mathematical proof is supplied by the certificate and the two Sage replayers.'};
    if(errors.length)throw Error('GeoGebra page errors: '+errors.join('; '));
    fs.writeFileSync(path.join(__dirname,'runtime-report.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  } finally {
    if(browser)await browser.close();
    server.close();
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
