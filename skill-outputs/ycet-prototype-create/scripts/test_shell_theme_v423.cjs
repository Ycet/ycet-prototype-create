// 使用内置 Chrome 离线检查样式匹配与原有交互，不安装运行时依赖。
const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const root=path.resolve(process.argv[2]);const browser=await chromium.launch({channel:'chrome',headless:true});
 const results=[],errors=[],network=[];
 try{
  const context=await browser.newContext({offline:true,viewport:{width:1280,height:800}});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  for(const name of ['light','dark'])for(const [kind,file]of [['pages','prototype-pages'],['demo','prototype-demo'],['direction','design-direction'],['nonframe','prototype-nonframe']]){
   const output=path.join(root,'独立 分享',name);fs.mkdirSync(output,{recursive:true});const source=path.join(output,file+'.html');fs.copyFileSync(path.join(root,name,'prototype/outputs',file+'.html'),source);
   await page.setViewportSize({width:1280,height:800});await page.goto(pathToFileURL(source).href);
   const theme=await page.locator('#ycet-metadata').evaluate(e=>JSON.parse(e.textContent).shellTheme);
   const rgb=hex=>'rgb('+hex.slice(1).match(/../g).map(v=>parseInt(v,16)).join(', ')+')';
   const style=async(selector,property)=>page.locator(selector).first().evaluate((e,p)=>getComputedStyle(e)[p],property);
   assert.equal(await style('[data-ycet-page-id=home]','backgroundColor'),rgb(theme.surface));
   assert.equal(await style('[data-ycet-page-id=home]','color'),rgb(theme.text));
   if(kind!=='nonframe')assert.equal(await style('body','backgroundColor'),rgb(theme.background));
   if(kind==='direction'){assert.equal(await style('.ycet-direction-summary','backgroundColor'),'rgba(0, 0, 0, 0)');assert.equal(await style('.ycet-direction-custom p','color'),rgb(theme.muted));}
   if(['pages','direction'].includes(kind)){assert.equal(await style('.ycet-card>h2','color'),rgb(theme.accent));assert.equal(await page.locator('.ycet-page:visible').count(),kind==='pages'?2:1);}
   if(kind==='demo'){
    assert.equal(await style('.ycet-nav','backgroundColor'),rgb(theme.surface));assert.equal(await style('.ycet-toolbar button','borderRadius'),theme.radius);
    assert.equal(await style('[aria-current=page]','backgroundColor'),rgb(theme.activeBackground));
    const width=(await page.locator('.ycet-nav').boundingBox()).width;
    const before=(await page.locator('.ycet-fit').boundingBox()).width;
    await page.locator('[data-ycet-zoom=in]').click();assert((await page.locator('.ycet-fit').boundingBox()).width>before);assert.equal((await page.locator('.ycet-nav').boundingBox()).width,width);
    await page.locator('[data-ycet-tool-target=detail]').click();await page.locator('[data-ycet-page-id=detail]').waitFor({state:'visible'});await page.waitForFunction(color=>getComputedStyle(document.querySelector('[data-ycet-tool-target=detail]')).backgroundColor===color,rgb(theme.activeBackground));
    await page.goBack();await page.locator('[data-ycet-page-id=home]').waitFor({state:'visible'});
    await page.locator('[data-ycet-element-id=count]').first().click();assert.equal(await page.locator('[data-ycet-element-id=count]').first().innerText(),'1');
    for(const viewport of [{width:1280,height:800},{width:390,height:844}]){
     await page.setViewportSize(viewport);await page.locator('[data-ycet-zoom=fit]').click();
     await page.waitForFunction(()=>{const b=document.querySelector('.ycet-fit-content').getBoundingClientRect();return b.x>=0&&b.y>=0&&b.right<=innerWidth+1&&b.bottom<=innerHeight+1;});
    }
    await page.setViewportSize({width:1280,height:800});await page.locator('[data-ycet-zoom=fit]').click();
   }
   if(kind==='nonframe'){
    await page.setViewportSize({width:390,height:844});await page.locator('.ycet-menu').click();assert.equal(await style('.ycet-drawer','backgroundColor'),rgb(theme.surface));
    await page.locator('[data-ycet-tool-target=detail]').click();await page.locator('.ycet-drawer').waitFor({state:'hidden'});await page.locator('[data-ycet-page-id=detail]').waitFor({state:'visible'});
    assert.equal(await page.locator('[data-ycet-page-id=detail]').evaluate(e=>e.clientWidth),390);
    await page.locator('.ycet-menu').click();await page.keyboard.press('Escape');await page.locator('.ycet-drawer').waitFor({state:'hidden'});
   }
   await page.screenshot({path:path.join(root,`${name}-${kind}.png`),fullPage:true});results.push({theme:name,kind,status:'passed'});
  }
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
  const result={results,errors,network};fs.writeFileSync(path.join(root,'shell-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
