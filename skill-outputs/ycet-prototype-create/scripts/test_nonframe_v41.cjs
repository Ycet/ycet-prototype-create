// 版本开发验收：一个浏览器进程复用多个端口／视口，不用于用户原型修改。
const {chromium,firefox,webkit}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
(async()=>{
 const root=path.resolve(process.argv[2]),results=[];
 for(const channel of ['chrome','msedge','firefox','webkit']){
  let browser;try{browser=channel==='firefox'?await firefox.launch():channel==='webkit'?await webkit.launch():await chromium.launch({channel});}
  catch(e){results.push({channel,status:'unavailable',reason:e.message.split('\n')[0]});continue;}
  let checks=0;
  try{
   const context=await browser.newContext({offline:true}),page=await context.newPage(),errors=[],network=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
   for(const port of ['ios','web','desktop-app']){
    const share=path.join(root,'独立 分享',port);fs.mkdirSync(share,{recursive:true});const file=path.join(share,'prototype-nonframe.html');
    fs.copyFileSync(path.join(root,port,'prototype/outputs/prototype-nonframe.html'),file);
    await page.goto(pathToFileURL(file).href);
    assert.equal(await page.locator('iframe,.ycet-fit,[data-ycet-zoom]').count(),0);
    // 移动菜单避免覆盖样本左上方控件。
    const box=await page.locator('.ycet-menu').boundingBox();await page.mouse.move(box.x+20,box.y+20);await page.mouse.down();await page.mouse.move(240,180,{steps:5});await page.mouse.up();
    const sizes=port==='ios'?[[320,568],[375,667],[390,844],[430,932],[844,390],[768,1024]]:[[1024,768],[1280,720],[1440,900],[1920,1080],[640,480]];
    for(const [width,height] of sizes){
     await page.setViewportSize({width,height});
     await page.waitForFunction(h=>Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ycet-view-height'))-h)<2,height);
     await page.evaluate(()=>{location.hash='#ycet=home'});await page.locator('[data-ycet-page-id=home]').waitFor({state:'visible'});
     const geometry=await page.locator('[data-ycet-page-id=home]').evaluate(e=>({w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height,sw:document.documentElement.scrollWidth}));
     assert.equal(geometry.w,width);assert(geometry.h>=height);assert(geometry.sw<=width+1);
     await page.locator('[data-ycet-element-id=last]').scrollIntoViewIfNeeded();assert(await page.locator('[data-ycet-element-id=last]').isVisible());
     const y=await page.evaluate(()=>scrollY);assert(y>0);
     await page.locator('.ycet-menu').click();await page.locator('[data-ycet-tool-target=detail]').click();await page.locator('[data-ycet-page-id=detail]').waitFor({state:'visible'});
     assert.equal(await page.evaluate(()=>scrollY),0);
     const short=await page.locator('[data-ycet-page-id=detail]').boundingBox();assert(short.height>=height-1);assert.equal(short.width,width);
     await page.goBack();await page.locator('[data-ycet-page-id=home]').waitFor({state:'visible'});assert(Math.abs(await page.evaluate(()=>scrollY)-y)<2);
     await page.locator('.ycet-menu').click();await page.locator('[data-ycet-tool-target=app]').click();await page.locator('[data-ycet-page-id=app]').waitFor({state:'visible'});
     const app=page.locator('[data-ycet-page-id=app]'),footer=app.locator('footer');const f=await footer.boundingBox();assert(f.y>=0&&f.y+f.height<=height+1);
     await app.locator('[data-ycet-element-id=app-last]').scrollIntoViewIfNeeded();assert(await app.locator('[data-ycet-scroll]').evaluate(e=>e.scrollTop>0));
     await page.locator('.ycet-menu').click();assert(await page.locator('.ycet-drawer').evaluate(e=>e.scrollHeight>e.clientHeight));
     await page.locator('[data-ycet-tool-target=extra-29]').focus();await page.keyboard.press('Tab');assert(await page.locator('[data-ycet-close]').evaluate(e=>e===document.activeElement));
     await page.keyboard.press('Escape');assert(await page.locator('.ycet-drawer').isHidden());assert.equal(await page.locator('body').evaluate(e=>e.style.position),'');
     checks++;
    }
    await page.evaluate(()=>{location.hash='#ycet=image'});await page.locator('[data-ycet-page-id=image]').waitFor({state:'visible'});
    const img=page.locator('[data-ycet-page-id=image] img');await img.evaluate(e=>e.decode());const size=await img.boundingBox();assert(Math.abs(size.height/size.width-3)<.01);
    const hotspot=page.getByRole('button',{name:'图片返回'});await hotspot.scrollIntoViewIfNeeded();await hotspot.click();await page.locator('[data-ycet-page-id=home]').waitFor({state:'visible'});
    await page.evaluate(()=>scrollTo(0,0));
    await page.screenshot({path:path.join(root,channel+'-'+port+'.png')});
   }
   assert.deepEqual(errors,[]);assert.deepEqual(network,[]);results.push({channel,status:'passed',checks});await context.close();
  }finally{await browser.close();}
 }
 fs.writeFileSync(path.join(root,'nonframe-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));assert(results.some(r=>r.status==='passed'));
})().catch(e=>{console.error(e);process.exitCode=1});
