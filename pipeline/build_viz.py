#!/usr/bin/env python3
"""Make the brain visible — a self-contained HTML explorer of the one canon.

The signature view: the whole canon (Genesis → Revelation) laid on one axis, with the
corpus's dense cross-reference web drawn as a faint underlay and the authored Messianic
threads drawn as bold arcs on top — the constitution's two layers (corpus vs. interpretation)
made visual. Below, each thread opens to its three witnesses (MT Hebrew · LXX Greek · NT) and
the pivotal words that carry it.

Everything is inlined (no external assets), so viz/index.html opens straight in a browser and
is safe to publish as a static page. Data is embedded as JSON, computed here from the parquets.

Run:  python3 pipeline/build_viz.py     (after the other build steps)
"""
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
OUT = ROOT / "viz" / "index.html"
OUT.parent.mkdir(exist_ok=True)

CAT_COLOR = {"messianic-prophecy": "#d9b25a", "type": "#5ec8be", "thematic-thread": "#e08aa6"}


def main():
    con = duckdb.connect()
    for f in ("verses", "bridge", "interpretive", "interp_words", "lxx"):
        p = D / f"{f}.parquet"
        if p.exists():
            con.execute(f"CREATE VIEW {f} AS SELECT * FROM '{p}'")

    maxord = con.sql("SELECT max(ord) FROM verses").fetchone()[0]
    ordof = dict(con.sql("SELECT ref, ord FROM verses").fetchall())
    texts = {r[0]: (r[1], r[2], r[3]) for r in con.sql(
        "SELECT ref, canon, text_en, text_orig FROM verses").fetchall()}
    lxxof = dict(con.sql("SELECT ref, text_lxx FROM lxx WHERE resolved").fetchall()) \
        if (D / "lxx.parquet").exists() else {}

    books = [{"book": b, "canon": c, "lo": lo, "hi": hi}
             for b, c, lo, hi in con.sql("""SELECT book, canon, min(ord), max(ord)
                 FROM verses GROUP BY book, canon ORDER BY min(ord)""").fetchall()]

    # Faint underlay: a sample of the corpus NT→Tanakh apparatus (the community web).
    sample = con.sql("""SELECT from_ref, to_ref FROM bridge
        WHERE resolved AND to_canon='Tanakh' AND votes >= 3
        ORDER BY votes DESC LIMIT 1400""").fetchall()
    web = [[ordof[f], ordof[t]] for f, t in sample if f in ordof and t in ordof]

    # The bold overlay: the authored Messianic threads, each with its primary witnesses.
    threads = []
    heads = con.sql("""SELECT id, any_value(category) c, any_value(confidence) conf,
                              any_value(title) t, any_value(basis) b, any_value(note) n
                       FROM interpretive GROUP BY id""").fetchall()
    for tid, cat, conf, title, basis, note in heads:
        pairs = con.sql(f"""SELECT from_ref, from_range, to_ref, to_range
                            FROM interpretive WHERE id='{tid}'""").fetchall()
        tk_ref, tk_range = pairs[0][0], pairs[0][1]
        nt_ref, nt_range = pairs[0][2], pairs[0][3]
        _, mt_en, mt_he = texts.get(tk_ref, (None, "", ""))
        _, nt_en, _ = texts.get(nt_ref, (None, "", ""))
        words = [{"lang": l, "strongs": s, "lemma": lm, "translit": tr, "gloss": g}
                 for l, s, lm, tr, g in con.sql(f"""SELECT lang, strongs, lemma, translit,
                     gloss FROM interp_words WHERE id='{tid}' ORDER BY lang DESC""").fetchall()] \
            if (D / "interp_words.parquet").exists() else []
        lxx_txt = lxxof.get(tk_ref, "")
        # the hinge: does the LXX of the anchor already read the NT's Greek key word?
        hinge = ""
        for w in words:
            if w["lang"] == "Greek" and w["lemma"] and w["lemma"][:4] in lxx_txt:
                hinge = w["lemma"]
                break
        threads.append({
            "id": tid, "cat": cat, "conf": conf, "title": title, "note": note, "basis": basis,
            "tkRef": tk_range, "ntRef": nt_range,
            "x1": ordof.get(tk_ref, 0), "x2": ordof.get(nt_ref, 0),
            "mtHe": mt_he or "", "mtEn": mt_en or "", "lxx": lxx_txt, "ntEn": nt_en or "",
            "words": words, "hinge": hinge,
        })

    stats = {
        "verses": con.sql("SELECT count(*) FROM verses").fetchone()[0],
        "words": con.sql("SELECT count(*) FROM '%s'" % (D / "words.parquet")).fetchone()[0]
                 if (D / "words.parquet").exists() else 0,
        "xrefs": con.sql("SELECT count(*) FROM bridge").fetchone()[0],
        "threads": len(threads),
    }
    payload = {"maxord": maxord, "books": books, "web": web,
               "threads": threads, "stats": stats, "catColor": CAT_COLOR}

    OUT.write_text(TEMPLATE.replace("/*DATA*/null", json.dumps(payload, ensure_ascii=False)))
    print(f"→ viz/index.html ({OUT.stat().st_size // 1024:,} KB, self-contained)")
    print(f"   {stats['threads']} threads · {len(web)} apparatus arcs · "
          f"{len(books)} books on the canon axis")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bible-Brain — one canon, one story</title>
<style>
:root{
  --bg:#0d1017; --panel:#141925; --ink:#e8e3d6; --muted:#9aa2b1; --line:#242c3a;
  --gold:#d9b25a; --teal:#5ec8be; --rose:#e08aa6; --tanakh:#c8a24a; --nt:#7fb6d6;
}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 600px at 50% -10%,#171d2b,var(--bg));
  color:var(--ink);font:16px/1.6 "Iowan Old Style","Palatino Linotype",Georgia,serif;}
.wrap{max-width:1200px;margin:0 auto;padding:0 20px}
header{padding:54px 20px 26px;text-align:center}
h1{font-size:clamp(30px,5vw,52px);margin:0;letter-spacing:.5px;font-weight:600}
h1 .amp{color:var(--gold)}
.sub{color:var(--muted);font-size:clamp(15px,2vw,19px);margin:.5em auto 0;max-width:640px}
.chips{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin:22px 0 0}
.chip{background:var(--panel);border:1px solid var(--line);border-radius:20px;
  padding:7px 15px;font-size:13px;color:var(--muted);font-family:ui-sans-serif,system-ui}
.chip b{color:var(--ink);font-family:inherit}
.legend{display:flex;gap:22px;flex-wrap:wrap;justify-content:center;margin:16px 0 4px;
  font-size:12.5px;color:var(--muted);font-family:ui-sans-serif,system-ui}
.legend span{display:inline-flex;align-items:center;gap:7px}
.swatch{width:22px;height:0;border-top:3px solid}
.arcbox{background:linear-gradient(180deg,#0f1420,#0c0f16);border:1px solid var(--line);
  border-radius:14px;margin:10px 0 6px;overflow:hidden}
svg{display:block;width:100%;height:auto}
.filters{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin:18px 0 4px;
  font-family:ui-sans-serif,system-ui}
.filters button{background:var(--panel);border:1px solid var(--line);color:var(--muted);
  border-radius:8px;padding:7px 13px;font-size:13px;cursor:pointer}
.filters button.on{color:#0d1017;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;
  padding:14px 0 60px}
.card{background:var(--panel);border:1px solid var(--line);border-left-width:4px;
  border-radius:12px;padding:16px 17px;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-2px);box-shadow:0 10px 30px #0006}
.card h3{margin:.1em 0 .3em;font-size:19px}
.meta{font-family:ui-sans-serif,system-ui;font-size:12px;color:var(--muted);
  display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.badge{font-size:11px;padding:2px 8px;border-radius:10px;border:1px solid;text-transform:uppercase;
  letter-spacing:.5px}
.refline{font-family:ui-sans-serif,system-ui;font-size:13px;color:var(--ink);margin:9px 0}
.refline .to{color:var(--nt)} .refline .from{color:var(--tanakh)}
.note{color:var(--muted);font-size:14.5px;margin:6px 0 4px;font-style:italic}
details{margin-top:10px;border-top:1px solid var(--line);padding-top:10px}
summary{cursor:pointer;font-family:ui-sans-serif,system-ui;font-size:12.5px;color:var(--muted)}
.wit{margin:10px 0;font-size:15px}
.wit .tag{display:inline-block;font-family:ui-sans-serif,system-ui;font-size:10.5px;
  letter-spacing:.5px;color:var(--muted);border:1px solid var(--line);border-radius:4px;
  padding:1px 6px;margin-right:7px;vertical-align:middle}
.he{direction:rtl;font-size:20px;line-height:1.9}
.gr{color:#d7e6e3}
.words{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 2px}
.word{background:#0e1420;border:1px solid var(--line);border-radius:8px;padding:6px 10px;
  font-size:14px}
.word .s{font-family:ui-monospace,monospace;font-size:11px;color:var(--muted);margin-left:6px}
.hinge{margin-top:10px;background:#1a1608;border:1px solid #4a3d17;border-radius:8px;
  padding:9px 12px;font-size:13.5px;color:var(--gold);font-family:ui-sans-serif,system-ui}
.basis{font-family:ui-sans-serif,system-ui;font-size:12px;color:var(--muted);margin-top:8px}
footer{border-top:1px solid var(--line);padding:26px 20px 50px;text-align:center;
  color:var(--muted);font-size:12.5px;font-family:ui-sans-serif,system-ui}
footer a{color:var(--teal)}
@media (prefers-color-scheme:light){
  :root{--bg:#f6f2e9;--panel:#fffdf7;--ink:#26221a;--muted:#6b6656;--line:#e4dccb}
  body{background:radial-gradient(1200px 600px at 50% -10%,#fffdf6,var(--bg))}
}
</style></head>
<body>
<header>
  <h1>Bible-Brain</h1>
  <p class="sub">The whole of Scripture — the Tanakh <span class="amp">&amp;</span> the New
     Testament — read as one canon telling one story.</p>
  <div class="chips" id="chips"></div>
</header>
<div class="wrap">
  <div class="legend">
    <span><i class="swatch" style="border-color:#5a6684;opacity:.6"></i> the corpus
      cross-reference web — <em>what Scripture says</em></span>
    <span><i class="swatch" style="border-color:var(--gold)"></i> Messianic threads —
      <em>the community's confession</em></span>
  </div>
  <div class="arcbox"><svg id="arc" viewBox="0 0 1200 440" preserveAspectRatio="xMidYMid meet"
     role="img" aria-label="The canon on one axis; cross-references and Messianic threads as arcs"></svg></div>
  <div class="filters" id="filters"></div>
  <div class="grid" id="grid"></div>
</div>
<footer>
  Corpus (verse text + cross-references) is faithful, license-clean data; the Messianic
  layer is the community's confession, graded and grounded — the two are never blurred.<br>
  Text: WEB &amp; JPS 1917 &amp; Tanach (Public Domain) · Words &amp; lexicon: STEPBible (CC BY 4.0) ·
  LXX: Swete (CC BY-SA) · Cross-references: <a href="https://www.openbible.info">OpenBible.info</a> (CC-BY).
</footer>
<script>
const DATA = /*DATA*/null;
const W=1200, H=440, BASE=376, PAD=18, maxord=DATA.maxord;
const X = o => PAD + (o/maxord)*(W-2*PAD);
const arc=document.getElementById('arc');
const NS='http://www.w3.org/2000/svg';
function el(t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e;}
function path(x1,x2,h,cls,color,w,op){
  const mx=(x1+x2)/2, top=BASE-h;
  const p=el('path',{d:`M ${x1} ${BASE} Q ${mx} ${top} ${x2} ${BASE}`,fill:'none',
    stroke:color,'stroke-width':w,'stroke-opacity':op,class:cls});
  return p;
}
// book bands + divider
let ntStart=W;
DATA.books.forEach(b=>{
  const x0=X(b.lo), x1=X(b.hi);
  arc.appendChild(el('rect',{x:x0,y:BASE,width:Math.max(1,x1-x0),height:12,
    fill:b.canon==='Tanakh'?'#c8a24a':'#7fb6d6','fill-opacity':.28}));
  if(b.canon==='NT') ntStart=Math.min(ntStart,x0);
});
arc.appendChild(el('line',{x1:ntStart,y1:BASE-8,x2:ntStart,y2:BASE+20,
  stroke:'#e8e3d6','stroke-opacity':.5,'stroke-dasharray':'3 3'}));
[['Tanakh',X(11000),'#c8a24a'],['New Testament',X(27500),'#7fb6d6']].forEach(([t,x,c])=>{
  const e=el('text',{x:x,y:BASE+32,fill:c,'font-size':12,'font-weight':600,
    'font-family':'ui-sans-serif,system-ui','text-anchor':'middle'});e.textContent=t;arc.appendChild(e);
});
// faint underlay: the corpus apparatus
DATA.web.forEach(([a,b])=>{
  const x1=X(a),x2=X(b);arc.appendChild(path(x1,x2,Math.min(300,Math.abs(x2-x1)*0.42),
    'web','#5a6684',1,.13));
});
// bold overlay: the Messianic threads
const threadPaths={};
DATA.threads.forEach(t=>{
  const x1=X(t.x1),x2=X(t.x2),col=DATA.catColor[t.cat];
  const p=path(x1,x2,Math.min(330,Math.abs(x2-x1)*0.5+40),'thread',col,2.4,.9);
  p.style.cursor='pointer'; p.dataset.cat=t.cat;
  p.addEventListener('mouseenter',()=>{p.setAttribute('stroke-width',4);p.setAttribute('stroke-opacity',1);});
  p.addEventListener('mouseleave',()=>{p.setAttribute('stroke-width',2.4);p.setAttribute('stroke-opacity',.9);});
  p.addEventListener('click',()=>{const c=document.getElementById('c-'+t.id);
    c.scrollIntoView({behavior:'smooth',block:'center'});c.animate(
      [{boxShadow:'0 0 0 2px '+col},{boxShadow:'0 0 0 0 transparent'}],{duration:1400});});
  arc.appendChild(p); threadPaths[t.id]=p;
});
// stat chips
const s=DATA.stats, fmt=n=>n.toLocaleString();
document.getElementById('chips').innerHTML=[
  ['Verses',s.verses],['Original-language words',s.words],['Cross-references',s.xrefs],
  ['Messianic threads',s.threads]
].map(([k,v])=>`<span class="chip"><b>${fmt(v)}</b> ${k}</span>`).join('');
// cards
const CATN={'messianic-prophecy':'Messianic prophecy','type':'Type &amp; foreshadow',
  'thematic-thread':'Thematic thread'};
const grid=document.getElementById('grid');
function esc(x){return (x||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function card(t){
  const col=DATA.catColor[t.cat];
  const words=t.words.map(w=>`<span class="word">${esc(w.lemma)} <i>${esc(w.translit)}</i>
    <span class="s">${w.strongs}</span></span>`).join('');
  const hinge=t.hinge?`<div class="hinge">↳ the LXX of ${esc(t.tkRef)} already reads
    <b>${esc(t.hinge)}</b> — the very word the New Testament quotes.</div>`:'';
  const lxx=t.lxx?`<div class="wit gr"><span class="tag">LXX</span>${esc(t.lxx)}</div>`:'';
  return `<div class="card" id="c-${t.id}" data-cat="${t.cat}" style="border-left-color:${col}">
    <div class="meta"><span class="badge" style="color:${col};border-color:${col}">${t.conf}</span>
      <span>${CATN[t.cat]}</span></div>
    <h3>${esc(t.title)}</h3>
    <div class="note">${esc(t.note)}</div>
    <div class="refline"><span class="from">${esc(t.tkRef)}</span> →
      <span class="to">${esc(t.ntRef)}</span></div>
    ${words?`<div class="words">${words}</div>`:''}
    ${hinge}
    <details><summary>the three witnesses</summary>
      <div class="wit he"><span class="tag">MT · Hebrew</span>${esc(t.mtHe)}</div>
      <div class="wit"><span class="tag">MT · English</span>${esc(t.mtEn)}</div>
      ${lxx}
      <div class="wit"><span class="tag">NT</span>${esc(t.ntEn)}</div>
      <div class="basis">basis — ${esc(t.basis)}</div>
    </details></div>`;
}
const order={'messianic-prophecy':0,'type':1,'thematic-thread':2};
DATA.threads.sort((a,b)=>order[a.cat]-order[b.cat]);
grid.innerHTML=DATA.threads.map(card).join('');
// filters
const cats=['all','messianic-prophecy','type','thematic-thread'];
const fb=document.getElementById('filters');
cats.forEach((c,i)=>{
  const b=document.createElement('button');b.textContent=c==='all'?'All threads':CATN[c];
  if(c!=='all'){b.style.borderColor=DATA.catColor[c];}
  if(i===0){b.classList.add('on');b.style.background='#e8e3d6';}
  b.onclick=()=>{
    [...fb.children].forEach(x=>{x.classList.remove('on');x.style.background='';x.style.color='';});
    b.classList.add('on');b.style.background=c==='all'?'#e8e3d6':DATA.catColor[c];
    document.querySelectorAll('.card').forEach(el=>el.style.display=(c==='all'||el.dataset.cat===c)?'':'none');
    Object.values(threadPaths).forEach(p=>p.style.opacity=(c==='all'||p.dataset.cat===c)?1:.08);
  };
  fb.appendChild(b);
});
</script>
</body></html>
"""


if __name__ == "__main__":
    main()
