// 真实浏览器回归。先用 test_prototype_v4.fixture 生成四类样本到参数目录。
const {chromium,firefox}=require('playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const {pathToFileURL}=require('node:url');
(async()=>{const root=path.resolve(process.argv[2]);let passed=0;const results=[];
for(const channel of ['chrome','msedge','firefox']){
 let browser;try{browser=channel==='firefox'?await firefox.launch({headless:true}):await chromium.launch({channel,headless:true});}catch(e){results.push({channel,status:'unavailable',reason:e.message.split('\n')[0]});continue;}
 try{
 const context=await browser.newContext({viewport:{width:1280,height:720},offline:true});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));const network=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
 for(const [type,name] of [['pages','prototype-pages'],['demo','prototype-demo'],['mobile','prototype-mobile'],['direction','design-direction']]){
  const share=path.join(root,'独立 分享',name);fs.mkdirSync(share,{recursive:true});const standalone=path.join(share,name+'.html');fs.copyFileSync(path.join(root,'prototype/outputs',name+'.html'),standalone);await page.goto(pathToFileURL(standalone).href);assert.equal(await page.locator('iframe,object,embed').count(),0);
  if(type==='pages') {assert.equal(await page.locator('.ycet-page:visible').count(),2);const url=page.url();await page.locator('[data-ycet-page-id=home] [data-ycet-nav-target]').click();assert.equal(page.url(),url);}
  if(type==='mobile'){const b=await page.locator('.ycet-menu').boundingBox();await page.mouse.move(b.x+20,b.y+20);await page.mouse.down();await page.mouse.move(b.x+220,b.y+300,{steps:8});await page.mouse.up();}
  if(['demo','mobile'].includes(type)){
   await page.locator('[data-ycet-page-id=home] [data-ycet-element-id=count]').click();assert.equal(await page.locator('[data-ycet-page-id=home] [data-ycet-element-id=count]').textContent(),'1');
   await page.locator('[data-ycet-page-id=home] [data-ycet-nav-target]').click();await page.waitForFunction(()=>!document.querySelector('[data-ycet-page-id=detail]').hidden);assert.equal(await page.locator('.ycet-page:visible').count(),1);
   await page.goBack();await page.waitForFunction(()=>!document.querySelector('[data-ycet-page-id=home]').hidden);assert.equal(await page.locator('[data-ycet-page-id=home] [data-ycet-element-id=count]').textContent(),'1');
  }
  if(type==='demo')for(const [width,height]of [[1440,900],[1280,720],[1024,768]]){await page.setViewportSize({width,height});await page.waitForTimeout(80);const a=await page.locator('.ycet-fit-content').boundingBox();assert(a.x>=0&&a.y>=0&&a.x+a.width<=width+1&&a.y+a.height<=height+1,JSON.stringify(a));}
  if(type==='mobile'){await page.setViewportSize({width:390,height:844});await page.locator('.ycet-menu').click();assert(await page.locator('.ycet-drawer').isVisible());await page.locator('[data-ycet-tool-target=detail]').click();assert(await page.locator('.ycet-drawer').isHidden());await page.setViewportSize({width:844,height:390});assert.equal(await page.locator('[data-ycet-page-id=detail]').evaluate(e=>e.clientWidth),844);}
  await page.screenshot({path:path.join(root,channel+'-'+type+'.png')});passed++;
 }
 assert.deepEqual(network,[]);assert.deepEqual(errors,[]);await context.close();results.push({channel,status:'passed'});
 }finally{await browser.close();}
}
fs.writeFileSync(path.join(root,'browser-results.json'),JSON.stringify({passed,results},null,2));console.log(JSON.stringify({passed,results},null,2));if(!passed)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
