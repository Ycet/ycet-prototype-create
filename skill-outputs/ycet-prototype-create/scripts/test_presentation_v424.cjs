// 验证完整展板与原有产品行为；截图用于人工视觉复核。
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
(async()=>{const root=path.resolve(process.argv[2]);const browser=await chromium.launch({channel:'chrome',headless:true});const results=[],errors=[],requests=[];
try{
 const context=await browser.newContext({offline:true,viewport:{width:1440,height:1000}});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
 for(const style of ['journal','studio'])for(const [kind,file]of [['direction','design-direction'],['pages','prototype-pages'],['demo','prototype-demo'],['nonframe','prototype-nonframe']]){
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,style,'prototype/outputs',file+'.html')).href);
  const product=page.locator('[data-ycet-page-id=home]');const before=await product.evaluate(e=>({text:e.innerText,color:getComputedStyle(e).color,font:getComputedStyle(e).fontFamily}));
  if(kind==='direction'){
   assert.equal(await page.locator('.ycet-swatch').count(),6);assert.equal(await page.locator('.ycet-specimen').count(),4);
   await page.locator('[data-save]').click();assert.equal(await page.locator('[data-result]').innerText(),'已保存');
   await page.locator('.ycet-specimen summary').click();assert(await page.locator('.ycet-specimen select').isVisible());
   assert.deepEqual(await product.evaluate(e=>({text:e.innerText,color:getComputedStyle(e).color,font:getComputedStyle(e).fontFamily})),before);
   for(const width of [1440,390]){
    await page.setViewportSize({width,height:1000});const overflow=await page.locator('.ycet-direction-summary').evaluate(e=>e.scrollWidth>e.clientWidth);assert(!overflow);
    await page.screenshot({path:path.join(root,`${style}-direction-${width}.png`),fullPage:true,animations:'disabled'});
   }
   await page.setViewportSize({width:1440,height:1000});
  }
  if(kind==='pages'){assert.equal(await page.locator('.ycet-card-description').count(),3);assert.equal(await page.locator('.ycet-page:visible').count(),3);}
  if(kind==='demo'){
   assert.equal(await page.locator('.ycet-nav-group').count(),2);const width=(await page.locator('.ycet-nav').boundingBox()).width;
   await page.locator('[data-ycet-tool-target=settings]').click();await page.locator('[data-ycet-page-id=settings]').waitFor({state:'visible'});await page.goBack();await product.waitFor({state:'visible'});
   await page.locator('[data-ycet-zoom=in]').click();assert.equal((await page.locator('.ycet-nav').boundingBox()).width,width);
   for(const viewport of [{width:1440,height:1000},{width:390,height:844}]){
    await page.setViewportSize(viewport);await page.locator('[data-ycet-zoom=fit]').click();await page.waitForFunction(()=>{const b=document.querySelector('.ycet-fit-content').getBoundingClientRect();return b.x>=0&&b.y>=0&&b.right<=innerWidth+1&&b.bottom<=innerHeight+1;});
    await page.locator('[data-ycet-tool-target=settings]').click();await page.locator('[data-ycet-tool-target=home]').click();
   }
   await page.setViewportSize({width:1440,height:1000});await page.locator('[data-ycet-zoom=fit]').click();
  }
  if(kind==='nonframe'){assert.equal(await page.locator('.ycet-shell-heading').count(),0);await page.locator('.ycet-menu').click();await page.locator('[data-ycet-tool-target=detail]').click();await page.locator('.ycet-drawer').waitFor({state:'hidden'});await page.goBack();await product.waitFor({state:'visible'});}
  await product.locator('[data-record]').click();assert.equal(await product.locator('[data-count]').innerText(),'新记录已创建');
  await page.mouse.move(5,5);await page.screenshot({path:path.join(root,`${style}-${kind}.png`),fullPage:true,animations:'disabled'});
  results.push({style,kind,status:'passed'});
 }
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);const result={results,errors,requests};fs.writeFileSync(path.join(root,'presentation-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
