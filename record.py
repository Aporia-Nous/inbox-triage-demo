"""Headless recording of demo.html -> triage-demo.mp4 (1600x1000). No desktop browser involved."""
import asyncio, base64, os, shutil, subprocess
from playwright.async_api import async_playwright
W,H=1600,1000
URL="file:///workspace/inbox-triage-demo/demo.html"
FR="/tmp/triage_frames"; OUT="/workspace/upwork-portfolio/triage-demo.mp4"
SCROLL_JS="""(a)=>new Promise(r=>{const [to,dur]=a;const from=window.scrollY;const s=performance.now();
function f(n){let t=Math.min(1,(n-s)/dur);let e=t*t*(3-2*t);window.scrollTo(0,from+(to-from)*e);if(t<1)requestAnimationFrame(f);else r();}
requestAnimationFrame(f);})"""
CURSOR_JS="""()=>{const c=document.createElement('div');c.id='fakecur';
c.style.cssText='position:fixed;left:1300px;top:600px;width:22px;height:22px;border-radius:50%;background:rgba(255,255,255,.85);box-shadow:0 0 0 4px rgba(110,168,255,.35),0 4px 14px rgba(0,0,0,.5);z-index:9999;pointer-events:none;transition:left .7s ease,top .7s ease,transform .15s';
document.body.appendChild(c);}"""
async def main():
    shutil.rmtree(FR, ignore_errors=True); os.makedirs(FR)
    frames=[]
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True, args=["--hide-scrollbars"])
        pg = await b.new_page(viewport={"width":W,"height":H}, device_scale_factor=1)
        await pg.goto(URL); await pg.wait_for_timeout(500)
        await pg.evaluate(CURSOR_JS)
        cdp = await pg.context.new_cdp_session(pg)
        def on_frame(ev):
            i=len(frames); fn=f"{FR}/f{i:05d}.jpg"
            open(fn,"wb").write(base64.b64decode(ev["data"]))
            frames.append((fn, ev["metadata"]["timestamp"]))
            asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]}))
        cdp.on("Page.screencastFrame", on_frame)
        await cdp.send("Page.startScreencast", {"format":"jpeg","quality":92,"maxWidth":W,"maxHeight":H,"everyNthFrame":1})
        async def move(sel):
            box = await pg.locator(sel).first.bounding_box()
            await pg.evaluate("([x,y])=>{const c=document.getElementById('fakecur');c.style.left=x+'px';c.style.top=y+'px'}",
                              [box["x"]+box["width"]/2-11, box["y"]+box["height"]/2-11])
            await pg.wait_for_timeout(850)
        async def click(sel):
            await move(sel)
            await pg.evaluate("()=>{const c=document.getElementById('fakecur');c.style.transform='scale(.7)';setTimeout(()=>c.style.transform='',160)}")
            await pg.click(sel); await pg.wait_for_timeout(300)
        await pg.wait_for_timeout(2200)                       # hold on the summary
        await pg.evaluate(SCROLL_JS,[1300,3800])                # scroll through the board
        await pg.wait_for_timeout(800)
        await pg.evaluate(SCROLL_JS,[0,1600]); await pg.wait_for_timeout(400)
        await click('.tab[data-tab="urgent"]'); await pg.wait_for_timeout(2000)
        await click('.tab[data-tab="unsure"]'); await pg.wait_for_timeout(1800)
        await click('#mail-7 summary'); await pg.wait_for_timeout(400)
        await pg.evaluate(SCROLL_JS,[420,1300]); await pg.wait_for_timeout(2000)
        await pg.evaluate(SCROLL_JS,[0,900])
        await click('.tab[data-tab="normal"]'); await pg.wait_for_timeout(1200)
        await pg.evaluate(SCROLL_JS,[700,2200]); await pg.wait_for_timeout(500)
        await pg.evaluate(SCROLL_JS,[0,1000])
        await click('.tab[data-tab="all"]'); await pg.wait_for_timeout(600)
        await move('#alerts'); await pg.wait_for_timeout(2000)
        await cdp.send("Page.stopScreencast")
        await b.close()
    # Variable-timing frames -> constant 30 fps video
    lines=[]
    for i,(fn,ts) in enumerate(frames):
        dur = (frames[i+1][1]-ts) if i+1<len(frames) else 0.5
        lines.append(f"file '{fn}'\nduration {max(dur,0.001):.4f}")
    lines.append(f"file '{frames[-1][0]}'")
    open(f"{FR}/list.txt","w").write("\n".join(lines))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",f"{FR}/list.txt",
        "-vf",f"fps=30,scale={W}:{H}:flags=lanczos,format=yuv420p","-c:v","libx264","-preset","medium","-crf","18",
        "-threads","2","-movflags","+faststart",OUT],check=True)
    print("frames",len(frames),"span",round(frames[-1][1]-frames[0][1],1),"s")
asyncio.run(main())
