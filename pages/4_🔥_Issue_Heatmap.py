import streamlit as st
import ifcopenshell
import json

st.set_page_config(
    page_title="Issue Heatmap — IFC Analyzer",
    page_icon="🔥",
    layout="wide",
)

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container {
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background-color: #161b22 !important;
    border-right: 1px solid #30363d !important;
}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #e6edf3 !important;
}
h1, h2, h3, h4, h5, h6, p, span, label { color: #e6edf3 !important; }
input, textarea {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
}
[data-baseweb="select"] > div:first-child {
    background-color: #161b22 !important;
    border-color: #30363d !important;
}
[data-baseweb="select"] span, [data-baseweb="select"] div {
    color: #e6edf3 !important;
    background-color: transparent !important;
}
[data-baseweb="popover"], [data-baseweb="popover"] ul,
[data-baseweb="popover"] li, [data-baseweb="menu"], [data-baseweb="menu"] li {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
    border-color: #30363d !important;
}
[data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] section, [data-testid="stFileUploader"] > div {
    background-color: #161b22 !important;
    border-color: #30363d !important;
    color: #e6edf3 !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] div {
    color: #8b949e !important;
    background-color: transparent !important;
}
[data-testid="stDataFrame"], [data-testid="stDataFrame"] > div {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}
[data-testid="stDataFrame"] th, [data-testid="stDataFrame"] [role="columnheader"] {
    background-color: #21262d !important;
    color: #e6edf3 !important;
}
[data-testid="stDataFrame"] td, [data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] [role="gridcell"] * {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
}
[data-testid="stMetric"] {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { color: #e6edf3 !important; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: #8b949e !important; }
[data-testid="stExpander"] {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {
    color: #e6edf3 !important;
    background-color: #161b22 !important;
}
[data-testid="stAlert"] { border-radius: 8px !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] span { color: inherit !important; }
div[data-testid="stButton"] > button {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #e6edf3 !important;
}
div[data-testid="stButton"] > button:hover {
    background: #1c2333 !important;
    border-color: #58a6ff !important;
    color: #e6edf3 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background-color: #161b22 !important;
    border-bottom: 2px solid #30363d !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background-color: transparent !important;
    color: #8b949e !important;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    color: #58a6ff !important;
    border-bottom: 2px solid #58a6ff !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] { background-color: #0d1117 !important; }
[data-testid="stCaptionContainer"] p, .stCaption, small { color: #8b949e !important; }
hr { border: none !important; border-top: 1px solid #30363d !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Guard ──────────────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in"):
    st.warning("Please log in from the Home page first.")
    st.stop()

try:
    model = ifcopenshell.open("temp.ifc")
except Exception:
    st.warning("⚠️ No IFC file found. Please upload a file on the **Home** page first.")
    st.stop()

# ── Proxy classification (mirrors AI Assistant logic) ─────────────────────────
VALID_PROXY_KW     = {"rpc","entourage","geo","georeference","geo-reference","survey",
                      "origin","basepoint","site origin","car","vehicle","truck","bus",
                      "people","person","human","pedestrian"}
INVALID_KW         = {"wall","door","window","slab","floor","roof","column","beam",
                      "stair","railing","pipe","duct","cable","wire","pump","fan",
                      "boiler","chiller","light","fixture","wash","toilet","sink",
                      "bath","panel","board","frame"}

def classify_proxy_heatmap(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in VALID_PROXY_KW):  return "valid"
    if any(k in n for k in INVALID_KW):      return "invalid"
    return "unknown"

# ── Re-derive issue sets ───────────────────────────────────────────────────────
proxies   = model.by_type("IfcBuildingElementProxy")
proxy_ids = set(p.GlobalId for p in proxies)
# Build name lookup for classification
proxy_name_map = {p.GlobalId: (p.Name or "") for p in proxies}

walls_missing_pset = []
for wall in model.by_type("IfcWall"):
    has_pset = False
    if hasattr(wall, "IsDefinedBy"):
        for defn in wall.IsDefinedBy:
            if defn.is_a("IfcRelDefinesByProperties"):
                ps = defn.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet") and ps.Name == "Pset_WallCommon":
                    has_pset = True
    if not has_pset:
        walls_missing_pset.append(wall)
missing_pset_ids = set(w.GlobalId for w in walls_missing_pset)

# ── Build heatmap element list ─────────────────────────────────────────────────
heatmap_elements = []
for elem in model.by_type("IfcProduct"):
    try:
        if hasattr(elem, 'ObjectPlacement') and elem.ObjectPlacement:
            pl = elem.ObjectPlacement
            if hasattr(pl, 'RelativePlacement'):
                rel = pl.RelativePlacement
                if hasattr(rel, 'Location') and rel.Location:
                    c = rel.Location.Coordinates
                    x = float(c[0])
                    z = float(c[1]) if len(c) > 1 else 0.0
                    if abs(x) > 500 or abs(z) > 500:
                        x /= 1000.0; z /= 1000.0
                    gid = elem.GlobalId
                    if gid in proxy_ids:
                        cls   = classify_proxy_heatmap(proxy_name_map.get(gid,""))
                        issue = cls   # "invalid" | "furnishing" | "valid" | "unknown"
                    elif gid in missing_pset_ids:
                        issue = "missing_pset"
                    else:
                        issue = "ok"
                    # Detect which storey this element belongs to
                    storey_name = "Unassigned"
                    try:
                        for rel in getattr(elem, "ContainedInStructure", []):
                            if rel.is_a("IfcRelContainedInSpatialStructure"):
                                st_elem = rel.RelatingStructure
                                if st_elem.is_a("IfcBuildingStorey"):
                                    storey_name = st_elem.Name or "Unnamed Storey"
                                    break
                    except Exception:
                        pass
                    heatmap_elements.append({
                        "x": x, "z": z, "issue": issue,
                        "name": elem.Name or "Unnamed",
                        "type": elem.is_a(),
                        "storey": storey_name,
                    })
    except Exception:
        continue

# For very large models cap heatmap elements to keep canvas fast
MAX_HEATMAP = 5000
if len(heatmap_elements) > MAX_HEATMAP:
    import random
    # Always keep all issue elements, sample clean ones
    issue_elems = [e for e in heatmap_elements if e["issue"] != "ok"]
    clean_elems = [e for e in heatmap_elements if e["issue"] == "ok"]
    sample_clean = random.sample(clean_elems, min(len(clean_elems), MAX_HEATMAP - len(issue_elems)))
    heatmap_elements = issue_elems + sample_clean
    st.info(f"ℹ️ Large model — showing all {len(issue_elems)} issue elements + {len(sample_clean)} sampled clean elements on heatmap.")

heatmap_json   = json.dumps(heatmap_elements)
invalid_count  = sum(1 for e in heatmap_elements if e["issue"] == "invalid")
valid_count    = sum(1 for e in heatmap_elements if e["issue"] == "valid")
unknown_count  = sum(1 for e in heatmap_elements if e["issue"] == "unknown")
pset_count     = sum(1 for e in heatmap_elements if e["issue"] == "missing_pset")
ok_count       = sum(1 for e in heatmap_elements if e["issue"] == "ok")
total_issues   = invalid_count + unknown_count + pset_count

# Build sorted storey list for JS
all_storeys  = sorted(set(e["storey"] for e in heatmap_elements))
storeys_json = json.dumps(["All Floors"] + all_storeys)

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🔥 Issue Heatmap — 2D Floor Plan Overlay")
st.caption("Spatial issue density map · Hover any cell for a full breakdown · Colour = issue density per zone")

m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("Total Issues",    total_issues)
m2.metric("🔴 Invalid",      invalid_count)
m3.metric("✅ Reference",    valid_count)
m4.metric("❓ Unknown",      unknown_count)
m5.metric("🟠 Missing Pset", pset_count)
m6.metric("🔵 Clean",        ok_count)

# ── Heatmap HTML ───────────────────────────────────────────────────────────────
heatmap_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:#0d1117;font-family:'Segoe UI',system-ui,sans-serif;color:#e6edf3;display:flex;flex-direction:column;height:100vh;overflow:hidden;}}
  #toolbar{{display:flex;align-items:center;gap:10px;padding:9px 16px;background:#161b22;border-bottom:1px solid #30363d;flex-shrink:0;flex-wrap:wrap;}}
  .tb-label{{font-size:12px;color:#8b949e;}}
  .tb-select{{background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:4px 10px;border-radius:6px;font-size:12px;cursor:pointer;}}
  .tb-select:hover{{border-color:#58a6ff;}}
  .legend-strip{{display:flex;align-items:center;gap:6px;margin-left:auto;font-size:11px;color:#8b949e;}}
  .grad-bar{{width:100px;height:10px;border-radius:4px;background:linear-gradient(to right,#1a2a1a,#ffff00,#ff6600,#cc0000);border:1px solid #30363d;}}
  #main{{flex:1;display:flex;overflow:hidden;position:relative;}}
  #canvas-wrap{{flex:1;position:relative;overflow:hidden;}}
  canvas{{display:block;cursor:crosshair;}}
  #side-panel{{width:240px;background:#161b22;border-left:1px solid #30363d;display:flex;flex-direction:column;overflow:hidden;flex-shrink:0;}}
  #side-header{{padding:12px 14px 8px;border-bottom:1px solid #30363d;font-size:12px;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;}}
  #zone-details{{padding:12px 14px;flex:1;overflow-y:auto;font-size:12px;}}
  .zone-stat{{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #21262d;}}
  .zone-stat:last-child{{border-bottom:none;}}
  .zs-label{{color:#8b949e;}}
  .zs-val{{font-weight:700;}}
  .badge{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:700;}}
  .badge-crit{{background:#cc000033;color:#ff6b6b;border:1px solid #cc0000;}}
  .badge-high{{background:#ff660033;color:#ffaa44;border:1px solid #ff6600;}}
  .badge-med{{background:#aaaa0033;color:#ffff66;border:1px solid #aaaa00;}}
  .badge-low{{background:#1a4a1a33;color:#66cc66;border:1px solid #1a6a1a;}}
  .badge-none{{background:#1a2a3a33;color:#4fc3f7;border:1px solid #1a4a6e;}}
  .elem-item{{padding:5px 0;border-bottom:1px solid #21262d;font-size:11px;}}
  .elem-item:last-child{{border-bottom:none;}}
  .elem-type{{color:#8b949e;font-size:10px;}}
  .elem-dot{{display:inline-block;width:7px;height:7px;border-radius:1px;margin-right:4px;vertical-align:middle;}}
  #tooltip{{position:absolute;background:#161b22ee;border:1px solid #30363d;border-radius:7px;padding:8px 12px;font-size:11px;pointer-events:none;display:none;z-index:20;backdrop-filter:blur(8px);box-shadow:0 6px 20px #00000099;max-width:200px;}}
</style>
</head>
<body>
<div id="toolbar">
  <span class="tb-label">Grid:</span>
  <select class="tb-select" id="grid-res" onchange="rebuildAndDraw()">
    <option value="8">Coarse 8×8</option>
    <option value="12" selected>Medium 12×12</option>
    <option value="20">Fine 20×20</option>
    <option value="30">Ultra 30×30</option>
  </select>
  <span class="tb-label" style="margin-left:8px">Show:</span>
  <select class="tb-select" id="show-mode" onchange="rebuildAndDraw()">
    <option value="all">All Issues</option>
    <option value="invalid">❌ Invalid Proxy</option>
    <option value="valid">✅ Reference</option>
    <option value="unknown">❓ Unknown</option>
    <option value="missing_pset">🟠 Missing Pset</option>
  </select>
  <span class="tb-label" style="margin-left:8px">Floor:</span>
  <select class="tb-select" id="floor-filter" onchange="rebuildAndDraw()">
  </select>
  <div class="legend-strip">
    <span>Low</span><div class="grad-bar"></div><span>High</span>
  </div>
</div>
<div id="main">
  <div id="canvas-wrap">
    <canvas id="hmap"></canvas>
    <div id="tooltip"></div>
  </div>
  <div id="side-panel">
    <div id="side-header">Zone Details</div>
    <div id="zone-details" style="color:#8b949e;font-size:12px;margin-top:20px;text-align:center">
      <div style="font-size:22px;margin-bottom:8px">🗺️</div>
      <b style="color:#e6edf3">Hover</b> a zone to preview it.<br><br>
      <b style="color:#ffe066">Click</b> a zone to <b style="color:#ffe066">lock 📌</b> the panel<br>so you can scroll all elements freely.<br><br>
      <span style="font-size:10px;color:#58a6ff">Click the same zone again to unlock.</span>
    </div>
  </div>
</div>
<script>
const ALL_ELEMS={heatmap_json};
const ALL_STOREYS={storeys_json};
let gridN=12,showMode='all',floorFilter='All Floors',hoverCell=null,lockedCell=null,grid=[],bounds={{}};
const canvas=document.getElementById('hmap');
const ctx=canvas.getContext('2d');

function resize(){{
  const wrap=document.getElementById('canvas-wrap');
  canvas.width=wrap.clientWidth; canvas.height=wrap.clientHeight; rebuildAndDraw();
}}
window.addEventListener('resize',resize);

function computeBounds(elems){{
  let minX=Infinity,maxX=-Infinity,minZ=Infinity,maxZ=-Infinity;
  for(const e of elems){{if(e.x<minX)minX=e.x;if(e.x>maxX)maxX=e.x;if(e.z<minZ)minZ=e.z;if(e.z>maxZ)maxZ=e.z;}}
  if(!isFinite(minX)){{minX=0;maxX=50;minZ=0;maxZ=50;}}
  const px=(maxX-minX)*0.05||1,pz=(maxZ-minZ)*0.05||1;
  return{{minX:minX-px,maxX:maxX+px,minZ:minZ-pz,maxZ:maxZ+pz}};
}}

function buildGrid(elems,n,b){{
  const cells=Array.from({{length:n}},()=>Array.from({{length:n}},()=>({{
    total:0,invalid:0,valid:0,unknown:0,missing_pset:0,ok:0,items:[]
  }})));
  const xR=b.maxX-b.minX,zR=b.maxZ-b.minZ;
  for(const e of elems){{
    const ci=Math.min(n-1,Math.floor((e.x-b.minX)/xR*n));
    const cj=Math.min(n-1,Math.floor((e.z-b.minZ)/zR*n));
    if(ci>=0&&cj>=0){{
      cells[cj][ci].total++;
      cells[cj][ci][e.issue]=(cells[cj][ci][e.issue]||0)+1;
      cells[cj][ci].items.push(e);
    }}
  }}
  return cells;
}}

function getCellCount(c){{
  if(showMode==='all') return c.invalid+c.unknown+c.missing_pset;
  return c[showMode]||0;
}}

function issueColor(cnt,max,cell){{
  if(cnt===0)return'rgba(20,30,20,0.85)';
  const t=Math.min(1,cnt/Math.max(1,max));
  if(showMode==='invalid'){{
    if(t<0.33){{const s=t/0.33;return`rgba(${{Math.floor(20+s*235)}},40,20,0.9)`;}}
    else if(t<0.66){{const s=(t-0.33)/0.33;return`rgba(255,${{Math.floor(40-s*20)}},20,0.9)`;}}
    else return'rgba(255,20,20,0.9)';
  }} else if(showMode==='valid'){{
    return`rgba(20,${{Math.floor(80+t*175)}},20,0.9)`;
  }} else if(showMode==='unknown'){{
    return`rgba(${{Math.floor(150+t*105)}},${{Math.floor(100+t*80)}},20,0.9)`;
  }} else if(showMode==='missing_pset'){{
    return`rgba(255,${{Math.floor(180-t*130)}},20,0.9)`;
  }}
  // 'all' — red heat gradient weighted by worst issue
  if(t<0.33){{const s=t/0.33;return`rgba(${{Math.floor(20+s*235)}},${{Math.floor(80+s*175)}},20,0.9)`;}}
  else if(t<0.66){{const s=(t-0.33)/0.33;return`rgba(255,${{Math.floor(255-s*153)}},20,0.9)`;}}
  else{{const s=(t-0.66)/0.34;return`rgba(255,${{Math.floor(102-s*102)}},${{Math.floor(20-s*20)}},0.9)`;}}
}}

function severityLabel(cnt,max){{
  if(cnt===0)return['None','badge-none'];
  const t=cnt/Math.max(1,max);
  if(t>0.75)return['Critical','badge-crit'];
  if(t>0.5)return['High','badge-high'];
  if(t>0.25)return['Medium','badge-med'];
  return['Low','badge-low'];
}}

function draw(){{
  ctx.clearRect(0,0,canvas.width,canvas.height);
  const pad=40,W=canvas.width-pad*2,H=canvas.height-pad*2;
  const n=grid.length; if(!n)return;
  const cw=W/n,ch=H/n;
  let maxIssues=1;
  for(let j=0;j<n;j++)for(let i=0;i<n;i++){{
    const cnt=getCellCount(grid[j][i]);
    if(cnt>maxIssues)maxIssues=cnt;
  }}
  for(let j=0;j<n;j++)for(let i=0;i<n;i++){{
    const c=grid[j][i];
    const cnt=getCellCount(c);
    const x=pad+i*cw,y=pad+j*ch;
    ctx.fillStyle=issueColor(cnt,maxIssues,c); ctx.fillRect(x,y,cw,ch);
    const isLocked=lockedCell&&lockedCell[0]===i&&lockedCell[1]===j;
    const isHover=hoverCell&&hoverCell[0]===i&&hoverCell[1]===j;
    if(isLocked){{
      ctx.fillStyle='rgba(255,224,102,0.10)'; ctx.fillRect(x,y,cw,ch);
      ctx.strokeStyle='#ffe066'; ctx.lineWidth=2.5; ctx.strokeRect(x+1,y+1,cw-2,ch-2);
    }} else if(isHover){{
      ctx.fillStyle='rgba(255,255,255,0.10)'; ctx.fillRect(x,y,cw,ch);
      ctx.strokeStyle='#ffffffbb'; ctx.lineWidth=1.5; ctx.strokeRect(x+1,y+1,cw-2,ch-2);
    }} else {{ctx.strokeStyle='#ffffff11';ctx.lineWidth=0.5;ctx.strokeRect(x,y,cw,ch);}}
    if(cw>28&&ch>18&&cnt>0){{
      ctx.fillStyle=cnt>maxIssues*0.5?'#ffffffdd':'#ffffffaa';
      ctx.font=`bold ${{Math.min(13,cw*0.35)}}px Segoe UI,sans-serif`;

      ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(cnt,x+cw/2,y+ch/2);
    }}
  }}
  ctx.fillStyle='#8b949e'; ctx.font='10px Segoe UI,sans-serif';
  ctx.textAlign='center'; ctx.textBaseline='middle';
  for(let i=0;i<n;i++) ctx.fillText(i+1,pad+i*cw+cw/2,pad/2);
  ctx.textAlign='right';
  for(let j=0;j<n;j++) ctx.fillText(String.fromCharCode(65+j),pad-6,pad+j*ch+ch/2);
  ctx.strokeStyle='#30363d'; ctx.lineWidth=1; ctx.strokeRect(pad,pad,W,H);
  const cx2=canvas.width-24,cy2=canvas.height-24;
  ctx.fillStyle='#8b949e'; ctx.font='bold 10px sans-serif'; ctx.textAlign='center';
  ctx.fillText('N',cx2,cy2-14);
  ctx.beginPath(); ctx.moveTo(cx2,cy2-10); ctx.lineTo(cx2-5,cy2+4); ctx.lineTo(cx2+5,cy2+4); ctx.closePath();
  ctx.fillStyle='#58a6ff44'; ctx.fill(); ctx.strokeStyle='#58a6ff'; ctx.lineWidth=1; ctx.stroke();
}}

// ── Update side panel with full scrollable element list ───────────────────────
function updatePanel(ci, cj, isLocked){{
  const cell=grid[cj][ci];
  const issueCnt=getCellCount(cell);
  const maxIssues=Math.max(...grid.flat().map(c=>getCellCount(c)),1);
  const[sevLabel,sevClass]=severityLabel(issueCnt,maxIssues);
  const lockIcon = isLocked ? ' 📌' : '';
  document.getElementById('side-header').innerHTML=
    `Zone Details &nbsp;<span style="font-size:10px;background:#1f6feb22;border:1px solid #1f6feb44;color:#58a6ff;padding:1px 8px;border-radius:10px;font-weight:400;">Zone ${{String.fromCharCode(65+cj)}}${{ci+1}}${{lockIcon}}</span>`;
  const ISSUE_COLORS_MAP = {{
    invalid:'#ff4444',
    valid:'#238636',   unknown:'#d29922',
    missing_pset:'#ff9500', ok:'#4fc3f7'
  }};
  const ISSUE_LABELS = {{
    invalid:'❌ Invalid',
    valid:'✅ Reference',unknown:'❓ Unknown',
    missing_pset:'🟠 Pset',ok:'🔵 Clean'
  }};
  const allItems = cell.items.map(it=>`
    <div class="elem-item">
      <span class="elem-dot" style="background:${{ISSUE_COLORS_MAP[it.issue]||'#4fc3f7'}}"></span>
      <span>${{it.name}}</span>
      <div class="elem-type">${{it.type}} · ${{ISSUE_LABELS[it.issue]||it.issue}}</div>
    </div>`).join('');
  document.getElementById('zone-details').innerHTML=`
    <div style="font-size:15px;font-weight:700;margin-bottom:10px">Zone ${{String.fromCharCode(65+cj)}}${{ci+1}}</div>
    <div class="zone-stat"><span class="zs-label">Severity</span><span class="badge ${{sevClass}}">${{sevLabel}}</span></div>
    <div class="zone-stat"><span class="zs-label">Total elements</span><span class="zs-val">${{cell.total}}</span></div>
    <div class="zone-stat"><span class="zs-label">❌ Invalid Proxy</span><span class="zs-val" style="color:#ff6b6b">${{cell.invalid||0}}</span></div>
    <div class="zone-stat"><span class="zs-label">✅ Reference</span><span class="zs-val" style="color:#7ee787">${{cell.valid||0}}</span></div>
    <div class="zone-stat"><span class="zs-label">❓ Unknown</span><span class="zs-val" style="color:#e3b341">${{cell.unknown||0}}</span></div>
    <div class="zone-stat"><span class="zs-label">🟠 Missing Pset</span><span class="zs-val" style="color:#ffb347">${{cell.missing_pset||0}}</span></div>
    <div class="zone-stat"><span class="zs-label">🔵 Clean</span><span class="zs-val" style="color:#4fc3f7">${{cell.ok||0}}</span></div>
    <div style="margin-top:12px;font-size:11px;color:#8b949e;font-weight:600;text-transform:uppercase;
                letter-spacing:.5px;border-top:1px solid #30363d;padding-top:8px;margin-bottom:6px;">
      Elements in zone (${{cell.items.length}})
      ${{isLocked?'<span style="float:right;font-size:10px;color:#ffe066;">📌 Locked — scroll freely</span>':
                  '<span style="float:right;font-size:10px;color:#8b949e;">Click zone to lock</span>'}}
    </div>
    <div>${{allItems}}</div>`;
}}

// ── Mouse events ──────────────────────────────────────────────────────────────
canvas.addEventListener('mousemove', e=>{{
  const rect=canvas.getBoundingClientRect();
  const mx=e.clientX-rect.left, my=e.clientY-rect.top;
  const pad=40, W=canvas.width-pad*2, H=canvas.height-pad*2;
  const n=grid.length; if(!n)return;
  const cw=W/n, ch=H/n;
  const ci=Math.floor((mx-pad)/cw), cj=Math.floor((my-pad)/ch);
  const tt=document.getElementById('tooltip');
  if(ci>=0&&ci<n&&cj>=0&&cj<n){{
    hoverCell=[ci,cj];
    const cell=grid[cj][ci];
    tt.style.display='block'; tt.style.left=(mx+14)+'px'; tt.style.top=(my-10)+'px';
    tt.innerHTML=`<div style="font-weight:700;margin-bottom:4px">Zone ${{String.fromCharCode(65+cj)}}${{ci+1}}</div>
      <div style="color:#8b949e">Total: <b style="color:#e6edf3">${{cell.total}}</b></div>
      <div style="color:#ff6b6b">❌ Invalid: <b>${{cell.invalid||0}}</b></div>
      <div style="color:#7ee787">✅ Reference: <b>${{cell.valid||0}}</b></div>
      <div style="color:#e3b341">❓ Unknown: <b>${{cell.unknown||0}}</b></div>
      <div style="color:#ffb347">🟠 Missing Pset: <b>${{cell.missing_pset||0}}</b></div>
      <div style="color:#4fc3f7">🔵 Clean: <b>${{cell.ok||0}}</b></div>`;
    // Only update side panel if nothing is locked
    if(!lockedCell) updatePanel(ci, cj, false);
    draw();
  }} else {{
    hoverCell=null;
    tt.style.display='none';
    draw();
  }}
}});

// Click to LOCK / UNLOCK the side panel on a zone
canvas.addEventListener('click', e=>{{
  const rect=canvas.getBoundingClientRect();
  const mx=e.clientX-rect.left, my=e.clientY-rect.top;
  const pad=40, W=canvas.width-pad*2, H=canvas.height-pad*2;
  const n=grid.length; if(!n)return;
  const cw=W/n, ch=H/n;
  const ci=Math.floor((mx-pad)/cw), cj=Math.floor((my-pad)/ch);
  if(ci>=0&&ci<n&&cj>=0&&cj<n){{
    if(lockedCell&&lockedCell[0]===ci&&lockedCell[1]===cj){{
      // Click same zone again → unlock
      lockedCell=null;
      updatePanel(ci, cj, false);
    }} else {{
      lockedCell=[ci,cj];
      updatePanel(ci, cj, true);
    }}
    draw();
  }}
}});

// Mouse leave canvas — only hide tooltip, NEVER touch side panel
canvas.addEventListener('mouseleave',()=>{{
  hoverCell=null;
  document.getElementById('tooltip').style.display='none';
  draw();
}});

function rebuildAndDraw(){{
  gridN=parseInt(document.getElementById('grid-res').value);
  showMode=document.getElementById('show-mode').value;
  floorFilter=document.getElementById('floor-filter').value;
  const filtered = floorFilter==='All Floors'
    ? ALL_ELEMS
    : ALL_ELEMS.filter(e=>e.storey===floorFilter);
  bounds=computeBounds(filtered);
  grid=buildGrid(filtered,gridN,bounds);
  lockedCell=null;
  // Update floor badge
  const fc = document.getElementById('floor-count');
  if(fc) fc.textContent = filtered.length+' elements';
  draw();
}}
// Populate floor dropdown
(function(){{
  const sel = document.getElementById('floor-filter');
  ALL_STOREYS.forEach(s=>{{
    const opt=document.createElement('option');
    opt.value=s; opt.textContent=s;
    sel.appendChild(opt);
  }});
}})();
resize();
</script>
</body>
</html>
"""

st.components.v1.html(heatmap_html, height=660, scrolling=False)
st.info("💡 Hover any zone for breakdown · Change grid resolution · Filter by issue type · Side panel shows all elements per zone")