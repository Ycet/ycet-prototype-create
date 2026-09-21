// 右侧属性面板真实浏览器回归；仅修改临时预览草稿。
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),net=require('node:net'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
(async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'ycet-inspector-'));
 const output=path.resolve(process.argv[2]||root);fs.mkdirSync(output,{recursive:true});
 const dir=path.join(root,'prototype/outputs');fs.mkdirSync(dir,{recursive:true});
 const source=path.join(dir,'prototype-demo.html');
 const html='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>body{padding:36px;font-family:system-ui;background:#f6f8fc}h2{width:240px;height:40px;font-size:24px;border-radius:4px;background:white}p{color:#667085}</style><h2 id="sample">项目概览</h2><p>查看项目进展，管理团队工作。</p></html>';
 fs.writeFileSync(source,html);
 const port=await new Promise(resolve=>{const server=net.createServer();server.listen(0,'127.0.0.1',()=>{const value=server.address().port;server.close(()=>resolve(value));});});
 const token='inspector-test',url='http://127.0.0.1:'+port;
 const server=spawn(process.env.PYTHON||'python3',[path.join(__dirname,'prototype_workbench.py'),'serve','--project-root',root,'--port',String(port),'--token',token],{env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},stdio:'ignore'});
 let browser;const errors=[],checks=[];
 try{
  let ready=false;for(let i=0;i<60;i++){try{if((await fetch(url+'/api/health',{headers:{'X-YCET-Token':token}})).ok){ready=true;break;}}catch{}await new Promise(resolve=>setTimeout(resolve,100));}assert(ready);
  browser=await chromium.launch({channel:'chrome',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:2});page.on('pageerror',error=>errors.push(error.message));
  const hasStyle=async(property,value)=>page.waitForFunction(([property,value])=>getComputedStyle(document.querySelector('#preview-frame').contentDocument.querySelector('#sample'))[property]===value,[property,value]);
  await page.goto(url+'/?token='+token);await page.locator('.file-row').filter({hasText:'prototype-demo.html'}).click();
  const preview=page.frameLocator('#preview-frame');await preview.locator('#sample').waitFor();await page.locator('#select-mode').click();await preview.locator('#sample').click();
  await page.waitForFunction(()=>document.querySelector('#selected-name').textContent==='h2#sample');

  const undo=page.locator('#undo-changes'), color=page.locator('[data-color-property="color"]');
  const openColor=async(target=color)=>{await target.click();await page.locator('#color-dialog').waitFor();};
  const change=async(hex)=>{await page.locator('#color-hex').fill(hex);await page.locator('#color-hex').dispatchEvent('input');};
  const cancel=async()=>{await page.locator('#color-dialog button[value="cancel"]').click();await page.waitForFunction(()=>!document.querySelector('#color-dialog').open);};
  const clean=async()=>page.waitForFunction(()=>document.querySelector('#undo-changes').disabled);
  const original=await preview.locator('#sample').evaluate(e=>getComputedStyle(e).color);
  assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
  assert.equal(await page.locator('#toggle-theme').evaluate(e=>e.nextElementSibling.id),'shutdown-workbench');
  await openColor();await cancel();await clean();
  await openColor();await change('#ee2233');await hasStyle('color','rgb(238, 34, 51)');await cancel();await hasStyle('color',original);await clean();
  await openColor();await change('#336699');await page.keyboard.press('Escape');await hasStyle('color',original);await clean();
  await page.locator('#font-size').fill('28');await page.locator('#font-size').press('Tab');await hasStyle('fontSize','28px');
  await openColor();await change('#112233');await cancel();await hasStyle('color',original);assert(!(await undo.isDisabled()));await undo.click();await hasStyle('fontSize','24px');await clean();
  await openColor();await change('#112233');await change('#abcdef');await page.locator('#apply-color').click();await hasStyle('color','rgb(171, 205, 239)');
  await openColor();await page.locator('#apply-color').click();await undo.click();await hasStyle('color',original);await clean();
  // 边框自动补线与颜色同一事务，取消无历史，应用可整批撤回。
  const border=page.locator('[data-color-property="border-color"]');
  await openColor(border);await change('#112233');await hasStyle('borderStyle','solid');await cancel();await hasStyle('borderStyle','none');await clean();
  await openColor(border);await change('#112233');await page.locator('#apply-color').click();await undo.click();await hasStyle('borderStyle','none');await clean();
  // 点击折叠也必须取消尚未提交的颜色预览。
  await openColor();await change('#ee2233');await page.locator('#collapse-inspector').click();await hasStyle('color',original);await page.locator('#collapse-inspector').click();await clean();
  const canvasWidth=async()=>(await page.locator('.canvas-viewport').boundingBox()).width;
  const initial=await canvasWidth();
  for(const [id,cls,edge] of [['sidebar','sidebar-collapsed','edge-reveal'],['inspector','inspector-collapsed','edge-reveal-right']]){
   await page.locator('#collapse-'+id).click();assert(await canvasWidth()>initial);assert.equal(await page.locator('#collapse-'+id).getAttribute('aria-expanded'),'false');
   await page.locator('#'+edge).hover();await page.waitForFunction(cls=>!document.querySelector('.layout').classList.contains(cls),cls);
   // 超过收起延迟后仍应展开；模拟旧 focusout/close 计时器在边缘停留期间到期。
   await page.locator('#'+id).dispatchEvent('focusout');
   await page.waitForTimeout(500);assert.equal(await page.locator('#collapse-'+id).getAttribute('aria-expanded'),'true');
   const panelBox=await page.locator('#'+id).boundingBox();
   await page.mouse.move(id==='sidebar'?panelBox.x+20:panelBox.x+panelBox.width-20,300);
   await page.waitForTimeout(350);assert.equal(await page.locator('#collapse-'+id).getAttribute('aria-expanded'),'true');
   await page.mouse.move(700,35);await page.waitForFunction(cls=>document.querySelector('.layout').classList.contains(cls),cls);
   // 直接进入折叠栏本体也可展开，离开后恢复折叠，再点击固定展开。
   const foldedBox=await page.locator('#'+id).boundingBox();
   await page.mouse.move(foldedBox.x+foldedBox.width/2,300);
   await page.waitForTimeout(500);assert.equal(await page.locator('#collapse-'+id).getAttribute('aria-expanded'),'true');
   await page.mouse.move(700,35);await page.waitForFunction(cls=>document.querySelector('.layout').classList.contains(cls),cls);
   await page.locator('#collapse-'+id).click();assert.equal(await page.locator('#collapse-'+id).getAttribute('aria-expanded'),'true');
  }
  await page.locator('#collapse-sidebar').click();await page.locator('#collapse-inspector').click();assert(await canvasWidth()>initial+300);await page.locator('#collapse-sidebar').click();await page.locator('#collapse-inspector').click();
  const group=page.locator('.group-toggle').first();assert((await group.locator('use').getAttribute('href')).endsWith('#folder-open'));await group.click();assert((await group.locator('use').getAttribute('href')).endsWith('#folder-closed'));await group.click();
  await openColor();await page.setViewportSize({width:1000,height:480});
  await page.waitForFunction(()=>{const b=document.querySelector('#color-dialog').getBoundingClientRect();return b.x>=0&&b.y>=0&&b.right<=innerWidth&&b.bottom<=innerHeight;});await cancel();await clean();
  await page.setViewportSize({width:1440,height:900});
  await page.locator('#add-effect').click();await page.locator('.effect-settings').first().click();
  const shadowBefore=await page.locator('#shadow-color').getAttribute('data-color');
  await openColor(page.locator('#shadow-color'));await change('#112233');await cancel();assert.equal(await page.locator('#shadow-color').getAttribute('data-color'),shadowBefore);
  await page.locator('#effect-dialog button[value="cancel"]').click();await undo.click();await hasStyle('boxShadow','none');await clean();
  // 深浅主题、所有弹窗与最小支持视口：视觉检查不发送伪请求。
  for(const theme of ['light','dark']){
   if(theme==='dark')await page.locator('#toggle-theme').click();
   await hasStyle('color',original);assert.equal(await preview.locator('html').getAttribute('data-theme'),null);
   for(const [width,height]of [[1440,900],[1000,640]]){
    await page.setViewportSize({width,height});await page.locator('.inspector-scroll').evaluate(e=>e.scrollTop=0);
    assert(await page.evaluate(()=>document.body.scrollWidth<=innerWidth));
    await page.mouse.move(700,40);await page.locator('#toast').waitFor({state:'hidden'});
    await page.screenshot({animations:'disabled',path:path.join(output,`workbench-${theme}-${width}.png`)});
    for(const id of ['confirm-dialog','annotation-dialog','request-dialog','result-dialog','color-dialog','effect-dialog']){
     await page.locator('#'+id).evaluate(e=>{if(e.classList.contains('anchored-popover')){e.style.left='16px';e.style.top='16px';}e.showModal();});
     const geometry=await page.locator('#'+id).evaluate(e=>{const b=e.getBoundingClientRect();return{inside:b.x>=0&&b.y>=0&&b.right<=innerWidth&&b.bottom<=innerHeight,overflow:e.scrollWidth>e.clientWidth,bg:getComputedStyle(e).backgroundColor};});
     assert(geometry.inside,`${id} bounds ${width}`);assert(!geometry.overflow,`${id} overflow`);assert.equal(geometry.bg,theme==='dark'?'rgb(27, 36, 50)':'rgb(255, 255, 255)');
     if(width===1440)await page.locator('#'+id).screenshot({animations:'disabled',path:path.join(output,`${id}-${theme}.png`)});
     await page.locator('#'+id).evaluate(e=>e.close('cancel'));
    }
    checks.push({theme,width,height,dialogs:6});
   }
  }
  await page.reload();assert.equal(await page.locator('html').getAttribute('data-theme'),'light');assert.equal(await page.locator('#collapse-inspector').getAttribute('aria-expanded'),'true');
  assert.equal(fs.readFileSync(source,'utf8'),html);assert.deepEqual(errors,[]);
  const result={checks,colorCancel:true,shadowCancel:true,resizePopover:true,colorEscape:true,priorUndoPreserved:true,colorApplySingleUndo:true,borderTransaction:true,collapseCancelsColor:true,bothPanelsAndHover:true,folderIcons:true,themeIsolated:true,defaults:true,sourceUnchanged:true,pageErrors:errors};
  fs.writeFileSync(path.join(output,'workbench-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
 }finally{if(browser)await browser.close();try{await fetch(url+'/api/shutdown',{method:'POST',headers:{'X-YCET-Token':token,'Content-Type':'application/json'},body:'{}'});}catch{}server.kill('SIGTERM');}
})().catch(error=>{console.error(error);process.exitCode=1;});
