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
  for(const [width,height]of [[1440,1000],[1280,720],[1000,640]]){
   await page.setViewportSize({width,height});await page.locator('.inspector-scroll').evaluate(element=>element.scrollTop=0);
   const geometry=await page.locator('.inspector').evaluate(element=>{
    const box=element.getBoundingClientRect();
    const visible=[...element.querySelectorAll('input:not([type=file]),select,button')].filter(control=>control.getClientRects().length);
    return {right:box.right,scrollWidth:element.scrollWidth,width:element.clientWidth,overflow:visible.filter(control=>{const b=control.getBoundingClientRect();return b.left<box.left||b.right>box.right;}).map(control=>control.id),heights:[...element.querySelectorAll('.primary-actions button')].map(button=>button.getBoundingClientRect().height)};
   });
   assert(geometry.right<=width);assert(geometry.scrollWidth<=geometry.width);assert.deepEqual(geometry.overflow,[]);assert.equal(new Set(geometry.heights).size,1);
   const actionY=(await page.locator('#send-ai').boundingBox()).y;
   await page.locator('#add-effect').scrollIntoViewIfNeeded();assert(await page.locator('#add-effect').isVisible());assert.equal((await page.locator('#send-ai').boundingBox()).y,actionY);
   await page.locator('.inspector-scroll').evaluate(element=>element.scrollTop=0);
   checks.push({width,height,status:'passed'});
   if(width===1440)await page.locator('.inspector').screenshot({path:path.join(output,'inspector-design.png')});
  }
  await page.setViewportSize({width:1440,height:1000});
  // 标签键盘切换不清空草稿，四角与宽高联动仍可撤回。
  await page.locator('#font-size').fill('28');await page.locator('#font-size').press('Tab');
  await page.waitForFunction(()=>document.querySelector('#undo-changes').disabled===false);
  await hasStyle('fontSize','28px');
  await page.locator('#tab-design').focus();await page.keyboard.press('ArrowRight');assert.equal(await page.locator('#tab-content').getAttribute('aria-selected'),'true');assert(await page.locator('#panel-content').isVisible());
  await page.locator('.inspector').screenshot({path:path.join(output,'inspector-content.png')});
  await page.keyboard.press('Home');assert.equal(await page.locator('#tab-design').getAttribute('aria-selected'),'true');
  await page.locator('#undo-changes').click();await hasStyle('fontSize','24px');
  for(const [id,label]of [['tl','左上'],['tr','右上'],['bl','左下'],['br','右下']])assert((await page.locator('#radius-'+id).locator('xpath=../..').innerText()).includes(label));
  await page.locator('#radius-tl').fill('12');await page.locator('#radius-tl').press('Tab');
  await hasStyle('borderBottomRightRadius','12px');
  await page.locator('#undo-changes').click();await hasStyle('borderBottomRightRadius','4px');await hasStyle('borderTopLeftRadius','4px');
  await page.locator('#link-radius').click();await page.locator('#radius-tr').fill('9');await page.locator('#radius-tr').press('Tab');await hasStyle('borderTopRightRadius','9px');await hasStyle('borderTopLeftRadius','4px');await page.locator('#undo-changes').click();
  await page.locator('#link-size').click();await page.locator('#width').fill('300');await page.locator('#width').press('Tab');await hasStyle('height','50px');await page.locator('#undo-changes').click();
  assert.equal(fs.readFileSync(source,'utf8'),html);assert.deepEqual(errors,[]);
  const result={checks,keyboardTabs:true,undo:true,cornerLabels:true,cornerLink:true,sizeLink:true,sourceUnchanged:true,pageErrors:errors};
  fs.writeFileSync(path.join(output,'inspector-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
 }finally{if(browser)await browser.close();try{await fetch(url+'/api/shutdown',{method:'POST',headers:{'X-YCET-Token':token,'Content-Type':'application/json'},body:'{}'});}catch{}server.kill('SIGTERM');}
})().catch(error=>{console.error(error);process.exitCode=1;});
