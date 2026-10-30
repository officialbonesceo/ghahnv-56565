#!/usr/bin/env python3
"""Teaser render: Mike + quiz card, 4s countdown, wrapped choice text."""
from __future__ import annotations
import argparse, json, math, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 24
WHITE, BLACK = (255,255,255), (18,18,24)
YELLOW, YELLOW_D = (255,210,40), (230,175,20)
CARD, CARD_HI = (22,32,58), (32,48,85)
GREEN, SOFT = (34,160,90), (150,165,195)
BG_TOP, BG_BOT, RING_BG = (42,58,88), (18,26,42), (40,52,78)
COUNTDOWN_SECS = 4

def font(size):
    for n in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(n).exists(): return ImageFont.truetype(n, size)
    return ImageFont.load_default()

def wrap(d, text, tf, max_w):
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        test = (cur+" "+w).strip()
        if d.textbbox((0,0), test, font=tf)[2] > max_w:
            if cur: lines.append(cur)
            cur = w
        else: cur = test
    if cur: lines.append(cur)
    return lines

def lerp(a,b,t): return a+(b-a)*max(0.0,min(1.0,t))
def ease_out(t): t=max(0.0,min(1.0,t)); return 1-(1-t)**3

def bg_gradient():
    img = Image.new("RGB",(W,H)); px=img.load()
    for y in range(H):
        t=y/H; r,g,b=[int(lerp(BG_TOP[i],BG_BOT[i],t)) for i in range(3)]
        for x in range(W): px[x,y]=(r,g,b)
    return img

def load_mike(pose="point"):
    root=Path(__file__).resolve().parents[1]
    mapping={"point":"body_point.png","present":"body_present.png","happy":"body_happy.png","question":"body_question.png","stand":"body.png"}
    p=root/"assets"/"mezi"/mapping.get(pose,"body_point.png")
    if p.exists(): return Image.open(p).convert("RGBA")
    try:
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from write_mezi_assets import draw_pose
        mode="point" if pose=="point" else ("present" if pose=="present" else "stand")
        expr="happy" if pose in ("happy","present") else ("question" if pose=="question" else "neutral")
        return draw_pose(mode, expr)
    except Exception: return None

def paste_mike(base, pose, bob=0.0, scale=0.9):
    mike=load_mike(pose)
    if mike is None: return
    mw=int(500*scale); mh=int(mw*mike.height/max(1,mike.width))
    mike=mike.resize((mw,mh),Image.Resampling.LANCZOS)
    base.paste(mike,(-20,H-mh-40+int(bob)),mike)

def top_banner(d, text, fill=YELLOW, text_fill=BLACK):
    d.rectangle([0,0,W,110],fill=fill); d.rectangle([0,110,W,118],fill=YELLOW_D)
    tf=font(42); bb=d.textbbox((0,0),text,font=tf)
    d.text(((W-(bb[2]-bb[0]))//2,32),text,font=tf,fill=text_fill)

def q_by_index(job, qi):
    if not qi: return None
    for q in job.get("questions") or []:
        if q.get("index")==qi: return q
    return None

def draw_choice(d, left, top, right, height, text, fill, outline, width, fsize=30):
    d.rounded_rectangle([left,top,right,top+height],20,fill=fill,outline=outline,width=width)
    pad, max_w = 16, right-left-32
    size=fsize; lines=[]
    while size>=22:
        cf=font(size); lines=wrap(d,text,cf,max_w)[:2]
        if lines and d.textbbox((0,0),lines[0],font=cf)[2]<=max_w: break
        size-=2
    cf=font(size); th=len(lines)*(size+6); ty=top+max(6,(height-th)//2)
    for line in lines:
        d.text((left+pad,ty),line,font=cf,fill=WHITE); ty+=size+6

def draw_ask(q, remaining=None, t_local=0.0, total_cd=COUNTDOWN_SECS):
    img=bg_gradient(); d=ImageDraw.Draw(img)
    marks=int(q.get("marks") or 20)
    top_banner(d, f"QUESTION {q.get('index','')}  ·  {marks} MARKS")
    cx0, cx1, cy0 = 300, W-28, 150
    qf=font(32); q_lines=wrap(d,q.get("question") or "",qf,cx1-cx0-36)[:5]
    btn_h, gap = 108, 12
    card_h=56+len(q_lines)*40+16+3*(btn_h+gap)+16
    d.rounded_rectangle([cx0,cy0,cx1,cy0+card_h],26,fill=WHITE,outline=(200,210,230),width=3)
    hdr=48+len(q_lines)*40
    d.rounded_rectangle([cx0,cy0,cx1,cy0+hdr],26,fill=CARD)
    d.rectangle([cx0,cy0+28,cx1,cy0+hdr],fill=CARD)
    y=cy0+20
    for line in q_lines:
        bb=d.textbbox((0,0),line,font=qf)
        d.text((cx0+(cx1-cx0-(bb[2]-bb[0]))//2,y),line,font=qf,fill=WHITE); y+=40
    top=y+14
    for i,ch in enumerate((q.get("choices") or [])[:3]):
        appear=ease_out(max(0.0,min(1.0,(t_local-0.08*i)*4)))
        inset=int((1-appear)*24)
        draw_choice(d,cx0+16+inset,top+i*(btn_h+gap),cx1-16-inset,btn_h,ch,
            CARD_HI if appear>0.5 else CARD,(70,90,130),3,30)
    if remaining is not None:
        n_float=max(0.0,float(remaining)); n=max(0,int(math.ceil(n_float)))
        frac=n_float/max(0.01,total_cd); cx,cy,r=190,H-290,96
        pulse=1.0+0.08*abs(math.sin(t_local*math.pi*2)); rr=int(r*pulse)
        d.ellipse([cx-rr-8,cy-rr-8,cx+rr+8,cy+rr+8],outline=RING_BG,width=12)
        extent=int(360*frac)
        if extent>0:
            d.pieslice([cx-rr,cy-rr,cx+rr,cy+rr],start=-90,end=-90+extent,fill=YELLOW)
            d.ellipse([cx-rr+16,cy-rr+16,cx+rr-16,cy+rr-16],fill=CARD)
        else:
            d.ellipse([cx-rr,cy-rr,cx+rr,cy+rr],outline=YELLOW,width=10)
            d.ellipse([cx-rr+16,cy-rr+16,cx+rr-16,cy+rr-16],fill=CARD)
        nf=font(88); s=str(n) if n>0 else "!"
        bb=d.textbbox((0,0),s,font=nf)
        d.text((cx-(bb[2]-bb[0])//2,cy-(bb[3]-bb[1])//2-8),s,font=nf,fill=YELLOW)
        lf=font(22); lab="seconds — comment!" if n>0 else "time up"
        bb=d.textbbox((0,0),lab,font=lf)
        d.text((cx-(bb[2]-bb[0])//2,cy+rr+12),lab,font=lf,fill=SOFT)
    else:
        tip=font(28); msg="Get ready…"
        bb=d.textbbox((0,0),msg,font=tip)
        d.text(((W-(bb[2]-bb[0]))//2,H-200),msg,font=tip,fill=YELLOW)
    paste_mike(img,"point",bob=math.sin(t_local*3.2)*5,scale=0.88)
    return img

def draw_reveal(q, t_local=0.0):
    img=bg_gradient(); d=ImageDraw.Draw(img)
    marks=int(q.get("marks") or 20)
    top_banner(d,f"ANSWER · Q{q.get('index','')}  ·  +{marks}",fill=GREEN,text_fill=WHITE)
    ans=str(q.get("answer") or "").upper()
    cx0,cx1,cy0=300,W-28,150
    qf=font(30); q_lines=wrap(d,q.get("question") or "",qf,cx1-cx0-36)[:3]
    btn_h,gap=100,12
    card_h=48+len(q_lines)*38+12+3*(btn_h+gap)+90
    d.rounded_rectangle([cx0,cy0,cx1,cy0+card_h],26,fill=WHITE,outline=(200,210,230),width=3)
    y=cy0+20
    for line in q_lines:
        bb=d.textbbox((0,0),line,font=qf)
        d.text((cx0+(cx1-cx0-(bb[2]-bb[0]))//2,y),line,font=qf,fill=SOFT); y+=38
    flash=ease_out(min(1.0,t_local*4))
    for i,ch in enumerate((q.get("choices") or [])[:3]):
        top=y+12+i*(btn_h+gap)
        letter=ch.strip()[0].upper() if ch else "?"
        hit=letter==ans or ch.upper().startswith(ans+")")
        if hit:
            fill=(int(lerp(CARD[0],GREEN[0],flash)),int(lerp(CARD[1],GREEN[1],flash)),int(lerp(CARD[2],GREEN[2],flash)))
            outline,width=YELLOW,5
        else:
            fill,outline,width=CARD,(50,58,78),3
        draw_choice(d,cx0+16,top,cx1-16,btn_h,ch,fill,outline,width,28)
    rf=font(26); reason=(q.get("reason") or "")[:120]
    ry=y+12+3*(btn_h+gap)+6
    for line in wrap(d,reason,rf,cx1-cx0-36)[:3]:
        bb=d.textbbox((0,0),line,font=rf)
        d.text((cx0+(cx1-cx0-(bb[2]-bb[0]))//2,ry),line,font=rf,fill=YELLOW); ry+=34
    paste_mike(img,"happy",bob=math.sin(t_local*2.8)*5,scale=0.88)
    return img

def draw_outro(job, t_local=0.0):
    img=bg_gradient(); d=ImageDraw.Draw(img)
    total=int(job.get("total_marks") or 60)
    top_banner(d,f"YOUR SCORE / {total}?",fill=GREEN,text_fill=WHITE)
    y=280
    for i,q in enumerate(job.get("questions") or []):
        appear=ease_out(max(0.0,min(1.0,(t_local-i*0.12)*3)))
        marks=int(q.get("marks") or job.get("marks_each") or 20)
        line=f"Q{q['index']}: {q['answer']}  (+{marks})"
        tf=font(44); bb=d.textbbox((0,0),line,font=tf)
        x=int(lerp(W,(W-(bb[2]-bb[0]))//2,appear))
        d.text((x,y),line,font=tf,fill=YELLOW); y+=90
    full=font(42); msg=f"All correct = {total}"
    bb=d.textbbox((0,0),msg,font=full)
    d.text(((W-(bb[2]-bb[0]))//2,y+24),msg,font=full,fill=WHITE)
    cta=font(28); msg2="Comment your marks · Follow for more"
    bb=d.textbbox((0,0),msg2,font=cta)
    d.text(((W-(bb[2]-bb[0]))//2,H-220),msg2,font=cta,fill=SOFT)
    paste_mike(img,"happy",bob=math.sin(t_local*2.5)*5,scale=0.88)
    return img

def frame_at(job, timeline, t):
    seg=timeline[-1]
    for s in timeline:
        if s["start"]<=t<s["end"] or (s is timeline[-1] and t>=s["start"]):
            if t<s["end"] or s is timeline[-1]:
                seg=s
                if t<s["end"]: break
    phase,qi=seg.get("phase"),seg.get("q")
    q=q_by_index(job,qi)
    t_local=max(0.0,t-float(seg["start"]))
    dur=max(0.01,float(seg["end"])-float(seg["start"]))
    if phase=="outro": return draw_outro(job,t_local)
    if phase=="countdown" and q: return draw_ask(q,remaining=max(0.0,float(seg["end"])-t),t_local=t_local,total_cd=dur)
    if phase=="ask" and q: return draw_ask(q,remaining=None,t_local=t_local)
    if phase=="reveal" and q: return draw_reveal(q,t_local)
    if q: return draw_ask(q,remaining=None,t_local=t_local)
    return draw_outro(job,t_local)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--job",default="teaser_job.json")
    p.add_argument("--timeline",default="teaser_timeline.json")
    p.add_argument("--audio",required=True)
    p.add_argument("--out",default="output.mp4")
    args=p.parse_args()
    job=json.loads(Path(args.job).read_text(encoding="utf-8"))
    tl=json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    timeline=tl["timeline"]; audio=Path(args.audio)
    if not audio.exists(): sys.exit("missing audio")
    dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],text=True).strip())
    n=max(FPS,int(math.ceil(dur*FPS)))
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path=Path(tmp)
        for i in range(n):
            frame_at(job,timeline,i/float(FPS)).save(tmp_path/f"frame_{i:05d}.png")
        out=Path(args.out).resolve()
        subprocess.check_call(["ffmpeg","-y","-framerate",str(FPS),"-i",str(tmp_path/"frame_%05d.png"),"-i",str(audio),"-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart","-c:a","aac","-b:a","192k","-shortest",str(out)])
        print("OK",out,out.stat().st_size)

if __name__=="__main__": main()
