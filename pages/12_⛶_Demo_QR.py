import streamlit as st
import json
import pathlib

st.set_page_config(page_title="BIMGuard Demo", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main, .block-container {
    background-color: #060910 !important; color: #e6edf3 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background-color: #0d1117 !important; border-right: 1px solid #1e2733 !important;
}
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
/* Scope font only to main content area — NOT bare div (would bleed into sidebar nav) */
.main h1, .main h2, .main h3, .main h4, .main p, .main span, .main label,
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
[data-testid="stMain"] h4, [data-testid="stMain"] p, [data-testid="stMain"] span {
    font-family: 'Space Grotesk', sans-serif !important; color: #e6edf3 !important;
}
[data-testid="stMetric"] { background:#0d1117 !important; border:1px solid #1e2733 !important; border-radius:12px !important; padding:16px !important; }
[data-testid="stMetric"] label { color:#6e7f96 !important; font-size:11px !important; letter-spacing:1px !important; text-transform:uppercase !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { color:#e6edf3 !important; font-size:24px !important; font-weight:800 !important; }
div[data-testid="stButton"] > button { background:#0d1117 !important; border:1px solid #1e2733 !important; color:#e6edf3 !important; border-radius:8px !important; font-family:'Space Grotesk',sans-serif !important; font-weight:600 !important; }
div[data-testid="stButton"] > button:hover { background:#111827 !important; border-color:#3b8eea !important; color:#3b8eea !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { background:#0d1117 !important; border-bottom:1px solid #1e2733 !important; }
[data-testid="stTabs"] [data-baseweb="tab"] { background:transparent !important; color:#6e7f96 !important; font-family:'Space Grotesk',sans-serif !important; font-weight:600 !important; }
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] { background:#111827 !important; color:#3b8eea !important; border-bottom:2px solid #3b8eea !important; }
[data-testid="stExpander"] { background:#0d1117 !important; border:1px solid #1e2733 !important; border-radius:10px !important; }
[data-testid="stDataFrame"] > div { background:#0d1117 !important; border:1px solid #1e2733 !important; border-radius:8px !important; }
[data-testid="stDataFrame"] th { background:#111827 !important; color:#6e7f96 !important; font-size:11px !important; letter-spacing:1px !important; text-transform:uppercase !important; }
[data-testid="stDataFrame"] td { color:#c9d1d9 !important; }
[data-testid="stSelectbox"] > div, [data-baseweb="select"] > div { background:#0d1117 !important; border:1px solid #1e2733 !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background:#0d1117 !important; border:1px solid #1e2733 !important; }
[data-baseweb="popover"] li { color:#e6edf3 !important; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-thumb { background:#1e2733; border-radius:2px; }
hr { border:none !important; border-top:1px solid #1e2733 !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════
_snap_path = pathlib.Path("demo_snapshot.json")

if not _snap_path.exists():
    st.markdown("""
<div style="background:#1a0d0d;border:2px solid #da3633;border-radius:14px;
padding:40px;text-align:center;margin-top:60px;">
  <div style="font-size:48px;margin-bottom:16px;">📭</div>
  <div style="font-size:22px;font-weight:800;color:#da3633;margin-bottom:8px;">No Demo Published Yet</div>
  <div style="font-size:14px;color:#8b949e;">
    The presenter hasn't published a demo yet.<br>
    Please wait — they will click <strong style="color:#e6edf3;">"Publish Demo"</strong>
    on the Home page after uploading and analysing the IFC file.
  </div>
</div>""", unsafe_allow_html=True)
    st.stop()

with open(_snap_path, "r", encoding="utf-8") as _f:
    S = json.load(_f)

an       = S.get("analysis", {})
storeys  = S.get("storeys",  [])
rules    = S.get("rules",    [])
rels     = S.get("relationships", [])
ctx      = S.get("user_context", {})

# ── Helper: pull value with fallback ─────────────────────────────────────────
def g(key, fallback=0):
    return an.get(key, fallback)

quality_score = g("quality_score", 0)
quality_grade = g("quality_grade", "—")
quality_color = g("quality_color", "#3b8eea")

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
<div style="padding:16px 0 8px;">
  <div style="font-size:20px;font-weight:800;color:#e6edf3;">🛡️ BIMGuard</div>
  <div style="font-size:10px;color:#6e7f96;letter-spacing:1px;margin-top:2px;">LIVE DEMO SHOWCASE</div>
</div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"""
<div style="background:#0d1f3c;border:1px solid #1e3a5f;border-radius:10px;padding:14px;margin-bottom:12px;">
  <div style="font-size:10px;color:#6e7f96;letter-spacing:1px;margin-bottom:6px;">FILE ANALYSED</div>
  <div style="font-size:12px;font-weight:700;color:#e6edf3;font-family:'JetBrains Mono',monospace;word-break:break-all;">{S.get('file_name','model.ifc')}</div>
  <div style="font-size:11px;color:#6e7f96;margin-top:4px;">{S.get('ifc_version','—')} · {S.get('export_tool','—')}</div>
</div>""", unsafe_allow_html=True)

    sc = quality_color
    st.markdown(f"""
<div style="background:{sc}15;border:1.5px solid {sc};border-radius:10px;padding:14px;text-align:center;margin-bottom:12px;">
  <div style="font-size:10px;color:#6e7f96;letter-spacing:1px;">MODEL SCORE</div>
  <div style="font-size:36px;font-weight:800;color:{sc};">{quality_score}</div>
  <div style="font-size:13px;color:{sc};">{quality_grade}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div style='font-size:11px;color:#6e7f96;'>Published by <strong style='color:#e6edf3;'>{S.get('published_by','—')}</strong></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:11px;color:#6e7f96;margin-top:4px;'>🕐 {S.get('published_at','—')}</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:10px;">
  <div>
    <div style="font-size:26px;font-weight:800;color:#e6edf3;letter-spacing:-1px;">🛡️ BIMGuard — Live Demo</div>
    <div style="font-size:13px;color:#6e7f96;margin-top:2px;">IFC Integrity & Quality Platform</div>
  </div>
  <div style="background:#0d2b0d;border:1px solid #238636;border-radius:8px;padding:8px 16px;font-size:12px;color:#3fb950;font-weight:700;">
    📅 {S.get('published_at','—')}
  </div>
</div>
<div style="background:linear-gradient(135deg,#0d1f3c,#0a1628);border:1px solid #1e3a5f;border-radius:12px;padding:16px 22px;margin-bottom:16px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
  <div style="font-size:28px;">📂</div>
  <div style="flex:1;">
    <div style="font-size:14px;font-weight:700;color:#3b8eea;">{S.get('file_name','model.ifc')}</div>
    <div style="font-size:12px;color:#6e7f96;margin-top:2px;">
      {g('total_elements')} elements · {g('proxy_elements')} proxies · {S.get('ifc_version','—')} · {S.get('export_tool','—')}
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#6e7f96;">Quality Score</div>
    <div style="font-size:24px;font-weight:800;color:{quality_color};">{quality_score} / 100</div>
    <div style="font-size:11px;color:{quality_color};">{quality_grade}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📊 Dashboard",
    "🔴 Proxies",
    "📦 Psets",
    "🏢 Storeys",
    "📏 Rules",
    "🏛️ NBC",
    "🔗 Relationships",
])

# ── helpers ───────────────────────────────────────────────────────────────────
def bar(pct, color, height=6):
    return f'<div style="background:#1a2030;border-radius:4px;height:{height}px;"><div style="width:{min(float(pct),100):.1f}%;background:{color};height:{height}px;border-radius:4px;"></div></div>'

def metric_card(label, value, color="#e6edf3"):
    return f'<div style="background:#0d1117;border:1px solid #1e2733;border-radius:10px;padding:12px 16px;text-align:center;"><div style="font-size:10px;color:#6e7f96;letter-spacing:1px;">{label}</div><div style="font-size:22px;font-weight:800;color:{color};">{value}</div></div>'

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Total Elements",   g("total_elements"))
    m2.metric("Proxy Elements",   g("proxy_elements"))
    m3.metric("Missing Psets",    g("missing_pset_count"))
    m4.metric("Rel. Issues",      g("rel_loss_count"))
    m5.metric("Score",            f"{quality_score}/100")

    st.markdown("---")
    d1, d2 = st.columns(2)

    with d1:
        st.markdown("#### 📉 5-Level Data Loss")
        levels = [
            ("L1 Semantic Loss",     g("type_loss_pct"),  g("type_loss_count"),  "#da3633", 30),
            ("L2 Property Loss",     g("prop_loss_pct"),  g("prop_loss_count"),  "#d29922", 20),
            ("L3 Quantity Loss",     g("qty_loss_pct"),   g("qty_loss_count"),   "#e3b341", 15),
            ("L4 Relationship Loss", g("rel_loss_pct"),   g("rel_loss_count"),   "#3b8eea", 25),
            ("L5 Geometry Loss",     g("geo_loss_pct"),   g("geo_loss_count"),   "#8b949e", 10),
        ]
        for label, pct, count, color, weight in levels:
            st.markdown(f"""
<div style="background:#0d1117;border:1px solid #1e2733;border-radius:10px;padding:12px 16px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div><span style="font-size:13px;font-weight:700;color:#e6edf3;">{label}</span>
    <span style="font-size:10px;color:#6e7f96;margin-left:8px;">wt:{weight}%</span></div>
    <div><span style="font-size:11px;color:#6e7f96;">{count} elems · </span>
    <span style="font-size:16px;font-weight:800;color:{color};">{pct}%</span></div>
  </div>{bar(pct, color)}
</div>""", unsafe_allow_html=True)

    with d2:
        st.markdown("#### 🏆 Score Card")
        sc = quality_color
        st.markdown(f"""
<div style="background:{sc}12;border:2px solid {sc};border-radius:14px;padding:20px;text-align:center;margin-bottom:14px;">
  <div style="font-size:10px;color:#6e7f96;letter-spacing:1px;">OVERALL QUALITY SCORE</div>
  <div style="font-size:56px;font-weight:800;color:{sc};line-height:1.1;">{quality_score}</div>
  <div style="font-size:16px;font-weight:700;color:{sc};">{quality_grade}</div>
  <div style="font-size:12px;color:#6e7f96;margin-top:6px;">Severity: {g('severity','—')}</div>
</div>""", unsafe_allow_html=True)

        for label, val, col in [
            ("Semantic Coverage", f"{g('semantic_pct'):.1f}%", "#3fb950"),
            ("Pset Coverage",     f"{g('score_breakdown', {}).get('pset_pct', '—')}%", "#3b8eea"),
            ("Proxy Penalty",     f"{g('proxy_pct'):.1f}%",   "#da3633"),
        ]:
            st.markdown(f"""
<div style="display:flex;justify-content:space-between;background:#0d1117;border:1px solid #1e2733;
border-radius:8px;padding:10px 14px;margin-bottom:6px;">
  <span style="font-size:13px;color:#8b99aa;">{label}</span>
  <span style="font-size:15px;font-weight:800;color:{col};">{val}</span>
</div>""", unsafe_allow_html=True)

    # Element composition bar
    st.markdown("---")
    st.markdown("#### 🧱 Element Composition")
    w_p  = g("walls_pct");  d_p  = g("doors_pct")
    win_p= g("windows_pct");pr_p = g("proxy_pct"); ot_p = g("other_pct")
    st.markdown(f"""
<div style="border-radius:8px;overflow:hidden;height:28px;display:flex;margin-bottom:10px;">
  <div title="Walls" style="width:{w_p:.1f}%;background:#1f6feb;display:flex;align-items:center;justify-content:center;"><span style="font-size:10px;font-weight:700;color:#fff;">{w_p:.0f}%</span></div>
  <div title="Doors" style="width:{d_p:.1f}%;background:#238636;display:flex;align-items:center;justify-content:center;"><span style="font-size:10px;font-weight:700;color:#fff;">{d_p:.0f}%</span></div>
  <div title="Windows" style="width:{win_p:.1f}%;background:#8957e5;display:flex;align-items:center;justify-content:center;"><span style="font-size:10px;font-weight:700;color:#fff;">{win_p:.0f}%</span></div>
  <div title="Proxies" style="width:{pr_p:.1f}%;background:#da3633;display:flex;align-items:center;justify-content:center;"><span style="font-size:10px;font-weight:700;color:#fff;">{pr_p:.0f}%</span></div>
  <div title="Other" style="flex:1;background:#3b444d;display:flex;align-items:center;justify-content:center;"><span style="font-size:10px;color:#aaa;">{ot_p:.0f}%</span></div>
</div>
<div style="display:flex;gap:18px;flex-wrap:wrap;">
  <span style="font-size:12px;color:#6e7f96;">🔵 Walls ({g('total_walls')})</span>
  <span style="font-size:12px;color:#6e7f96;">🟢 Doors ({g('doors')})</span>
  <span style="font-size:12px;color:#6e7f96;">🟣 Windows ({g('windows')})</span>
  <span style="font-size:12px;color:#da3633;">🔴 Proxies ({g('proxy_elements')})</span>
  <span style="font-size:12px;color:#6e7f96;">⬛ Other ({g('other_semantic')})</span>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — PROXIES
# ─────────────────────────────────────────────────────────────────────────────

# ── Classification logic (mirrors 1_Proxy_Classification.py) ─────────────────
_VALID_KW   = ["rpc","entourage","geo","georeference","geo-reference","survey",
               "origin","basepoint","site origin","car","vehicle","truck","bus",
               "people","person","human","pedestrian"]
_INVALID_KW = ["wall","door","window","slab","floor","roof","column","beam",
               "stair","railing","pipe","duct","cable","wire","pump","fan",
               "boiler","chiller","light","fixture","wash","toilet","sink",
               "bath","panel","board","frame"]

def _cls_proxy(name):
    n = (name or "").lower()
    if any(k in n for k in _VALID_KW):   return "valid"
    if any(k in n for k in _INVALID_KW): return "invalid"
    return "unknown"

with tabs[1]:
    import pandas as pd
    st.markdown("#### 🔴 Proxy Element Classification")

    _raw_proxies = an.get("proxy_list", [])
    _total_px    = g("proxy_elements")

    # Classify every proxy in the snapshot
    _classified = []
    for _p in _raw_proxies:
        _name = _p.get("Name") or "Unnamed"
        _classified.append({
            "Name":     _name,
            "GlobalId": _p.get("GlobalId", ""),
            "Class":    _cls_proxy(_name),
            "IFC Type": _p.get("IFC Type", "IfcBuildingElementProxy"),
        })

    _valid_px   = [p for p in _classified if p["Class"] == "valid"]
    _invalid_px = [p for p in _classified if p["Class"] == "invalid"]
    _unknown_px = [p for p in _classified if p["Class"] == "unknown"]

    # ── Summary metrics ───────────────────────────────────────────────────────
    p1,p2,p3,p4 = st.columns(4)
    p1.metric("Total Proxies", _total_px)
    p2.metric("✅ Valid",       len(_valid_px),
              help="Non-physical/reference elements — RPC, entourage, vehicles. No IFC class needed.")
    p3.metric("❌ Invalid",     len(_invalid_px),
              help="Real building/MEP elements with lost semantic type — must be reclassified.")
    p4.metric("❓ Unknown",     len(_unknown_px),
              help="Cannot be auto-determined — review manually.")

    # ── Breakdown bar ─────────────────────────────────────────────────────────
    if _total_px and _total_px > 0:
        _v_pct = round(len(_valid_px)   / _total_px * 100, 1)
        _i_pct = round(len(_invalid_px) / _total_px * 100, 1)
        _u_pct = round(len(_unknown_px) / _total_px * 100, 1)
        st.markdown(f"""
<div style="background:#0d1117;border:1px solid #1e2733;border-radius:10px;padding:16px 20px;margin:12px 0;">
  <div style="font-size:10px;color:#6e7f96;margin-bottom:10px;letter-spacing:1px;">PROXY BREAKDOWN</div>
  <div style="display:flex;height:22px;border-radius:6px;overflow:hidden;margin-bottom:10px;">
    <div style="width:{_v_pct}%;background:#238636;" title="Valid {_v_pct}%"></div>
    <div style="width:{_i_pct}%;background:#da3633;" title="Invalid {_i_pct}%"></div>
    <div style="width:{_u_pct}%;background:#6e7f96;" title="Unknown {_u_pct}%"></div>
  </div>
  <div style="display:flex;gap:20px;font-size:12px;flex-wrap:wrap;">
    <span style="display:flex;align-items:center;gap:6px;">
      <span style="width:10px;height:10px;border-radius:2px;background:#238636;display:inline-block;"></span>
      <span style="color:#e6edf3;">Valid</span>
      <strong style="color:#238636;">{_v_pct}%</strong>
      <span style="color:#6e7f96;">({len(_valid_px)})</span>
    </span>
    <span style="display:flex;align-items:center;gap:6px;">
      <span style="width:10px;height:10px;border-radius:2px;background:#da3633;display:inline-block;"></span>
      <span style="color:#e6edf3;">Invalid</span>
      <strong style="color:#da3633;">{_i_pct}%</strong>
      <span style="color:#6e7f96;">({len(_invalid_px)})</span>
    </span>
    <span style="display:flex;align-items:center;gap:6px;">
      <span style="width:10px;height:10px;border-radius:2px;background:#6e7f96;display:inline-block;"></span>
      <span style="color:#e6edf3;">Unknown</span>
      <strong style="color:#6e7f96;">{_u_pct}%</strong>
      <span style="color:#6e7f96;">({len(_unknown_px)})</span>
    </span>
  </div>
  <div style="font-size:11px;color:#6e7f96;margin-top:10px;line-height:1.7;border-top:1px solid #1e2733;padding-top:10px;">
    <strong style="color:#238636;">✅ Valid</strong> — non-physical reference elements; no IFC class needed.&nbsp;&nbsp;
    <strong style="color:#da3633;">❌ Invalid</strong> — building/MEP elements that lost their type; need reclassification.&nbsp;&nbsp;
    <strong style="color:#6e7f96;">❓ Unknown</strong> — review manually.
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Sub-tabs: Invalid / Valid / Unknown ───────────────────────────────────
    _ptab1, _ptab2, _ptab3 = st.tabs([
        f"❌ Invalid ({len(_invalid_px)})",
        f"✅ Valid ({len(_valid_px)})",
        f"❓ Unknown ({len(_unknown_px)})",
    ])

    def _proxy_card(p, border_color, badge_text, badge_bg, badge_fg):
        return f"""
<div style="background:#060910;border:1px solid {border_color}44;border-radius:8px;
padding:10px 16px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-size:13px;font-weight:600;color:#e6edf3;font-family:'JetBrains Mono',monospace;">{p["Name"]}</div>
    <div style="font-size:11px;color:#6e7f96;margin-top:2px;font-family:'JetBrains Mono',monospace;">{p["GlobalId"][:26]}…</div>
  </div>
  <span style="font-size:11px;color:{badge_fg};background:{badge_bg};border:1px solid {border_color};
  border-radius:4px;padding:2px 8px;white-space:nowrap;">{badge_text}</span>
</div>"""

    with _ptab1:
        st.caption(f"{len(_invalid_px)} elements are real building/MEP components whose IFC type was lost during export.")
        if _invalid_px:
            _s1 = st.text_input("🔍 Search", placeholder="e.g. wall, door", key="demo_inv_search")
            _f1 = [p for p in _invalid_px if _s1.lower() in p["Name"].lower()] if _s1 else _invalid_px
            st.caption(f"Showing {len(_f1[:150])} of {len(_invalid_px)}")
            for p in _f1[:150]:
                st.markdown(_proxy_card(p, "#da3633", "❌ Fix Required", "#da363318", "#da3633"), unsafe_allow_html=True)
        else:
            st.success("✅ No invalid proxies — all building elements are correctly typed!")

    with _ptab2:
        st.caption(f"{len(_valid_px)} elements are intentionally non-physical (RPC trees, entourage, survey points, vehicles).")
        if _valid_px:
            _s2 = st.text_input("🔍 Search", placeholder="e.g. RPC, car", key="demo_val_search")
            _f2 = [p for p in _valid_px if _s2.lower() in p["Name"].lower()] if _s2 else _valid_px
            st.caption(f"Showing {len(_f2[:150])} of {len(_valid_px)}")
            for p in _f2[:150]:
                st.markdown(_proxy_card(p, "#238636", "✅ No Fix Needed", "#23863618", "#3fb950"), unsafe_allow_html=True)
        else:
            st.info("No valid/reference proxy elements found.")

    with _ptab3:
        st.caption(f"{len(_unknown_px)} proxy elements could not be automatically classified. Review manually.")
        if _unknown_px:
            _s3 = st.text_input("🔍 Search", placeholder="e.g. Generic, Object", key="demo_unk_search")
            _f3 = [p for p in _unknown_px if _s3.lower() in p["Name"].lower()] if _s3 else _unknown_px
            st.caption(f"Showing {len(_f3[:150])} of {len(_unknown_px)}")
            for p in _f3[:150]:
                st.markdown(_proxy_card(p, "#6e7f96", "❓ Review Manually", "#6e7f9618", "#8b99aa"), unsafe_allow_html=True)
        else:
            st.info("No unknown proxies found.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — PSETS
# ─────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    st.markdown("#### 📦 Property Set (Pset) Completeness")
    sb = an.get("score_breakdown", {})
    pset_pct   = sb.get("pset_pct", 0)
    pset_grade = "Excellent" if pset_pct >= 85 else "Good" if pset_pct >= 70 else "Fair" if pset_pct >= 50 else "Poor"
    pc = "#238636" if pset_pct >= 85 else "#3b8eea" if pset_pct >= 70 else "#d29922" if pset_pct >= 50 else "#da3633"

    ps1,ps2,ps3 = st.columns(3)
    ps1.metric("Pset Coverage",  f"{pset_pct}%")
    ps2.metric("Missing Psets",  g("missing_pset_count"))
    ps3.metric("Grade",          pset_grade)

    st.markdown(f"""
<div style="background:{pc}12;border:2px solid {pc};border-radius:12px;padding:16px 22px;margin:12px 0;">
  <div style="font-size:11px;color:#6e7f96;letter-spacing:1px;">PSET COMPLETENESS</div>
  <div style="font-size:26px;font-weight:800;color:{pc};">{pset_pct}% — {pset_grade}</div>
  <div style="font-size:12px;color:#6e7f96;margin-top:4px;">
    Pset completeness contributes <strong style="color:{pc};">40 points</strong> to the overall model score.
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    # Show missing pset list
    missing_list = an.get("missing_pset_list", [])
    if missing_list:
        import pandas as pd
        st.markdown(f"#### Elements Missing Required Psets ({len(missing_list)} total)")
        filter_type_p = st.selectbox("Filter by IFC Type",
            ["All"] + sorted(set(r.get("IFC Type","") for r in missing_list)), key="pset_type_filter")
        show_m = missing_list if filter_type_p == "All" else [r for r in missing_list if r.get("IFC Type") == filter_type_p]
        st.caption(f"Showing {min(len(show_m), 200)} of {len(show_m)}")
        df_m = pd.DataFrame([{
            "Element":   r.get("Element Name", r.get("Name","Unnamed")),
            "IFC Type":  r.get("IFC Type",""),
            "Needs":     r.get("Required Pset", r.get("Issue","—")),
            "GlobalId":  r.get("GlobalId","")[:22]+"…",
        } for r in show_m[:200]])
        st.dataframe(df_m, use_container_width=True, hide_index=True, height=350)
    else:
        st.success("✅ All elements have their required property sets.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — STOREYS
# ─────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown("#### 🏢 Storey-by-Storey Quality")
    if storeys:
        for s in storeys:
            score = s.get("Score", 0)
            sc2 = "#238636" if score >= 85 else "#3b8eea" if score >= 70 else "#d29922" if score >= 50 else "#da3633"
            elems = s.get("Elements", 0)
            prx   = s.get("Proxies", 0)
            mps   = s.get("MissingPset", 0)
            prx_pct = round(prx / elems * 100, 1) if elems else 0
            st.markdown(f"""
<div style="background:#0d1117;border:1px solid #1e2733;border-radius:12px;padding:16px 20px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <div>
      <span style="font-size:16px;font-weight:800;color:#e6edf3;">🏢 {s.get('Storey','—')}</span>
      <span style="font-size:12px;color:#6e7f96;margin-left:10px;">{elems} elements</span>
    </div>
    <div style="background:{sc2}20;border:1.5px solid {sc2};border-radius:8px;padding:6px 16px;text-align:center;">
      <div style="font-size:10px;color:#6e7f96;">SCORE</div>
      <div style="font-size:22px;font-weight:800;color:{sc2};">{score}</div>
    </div>
  </div>
  <div style="display:flex;gap:20px;margin-bottom:8px;">
    <div><span style="font-size:11px;color:#6e7f96;">Proxies: </span>
    <span style="font-size:13px;color:#da3633;font-weight:700;">{prx} ({prx_pct}%)</span></div>
    <div><span style="font-size:11px;color:#6e7f96;">Missing Psets: </span>
    <span style="font-size:13px;color:#d29922;font-weight:700;">{mps}</span></div>
  </div>
  {bar(score, sc2)}
</div>""", unsafe_allow_html=True)
    else:
        st.info("Storey data not available in this snapshot.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — RULE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown("#### 📏 BIM Rule Validation")
    if rules:
        pass_c = sum(1 for r in rules if r.get("Status","").startswith("✅"))
        fail_c = sum(1 for r in rules if r.get("Status","").startswith("❌"))
        warn_c = sum(1 for r in rules if r.get("Status","").startswith("⚠️"))

        rc1,rc2,rc3,rc4 = st.columns(4)
        rc1.metric("Total Rules", len(rules))
        rc2.metric("✅ Pass",     pass_c)
        rc3.metric("❌ Fail",     fail_c)
        rc4.metric("⚠️ Warning", warn_c)

        st.markdown("---")
        rf = st.selectbox("Filter", ["All","✅ Pass","❌ Fail","⚠️ Warning"], key="rule_filter")
        show_r = rules if rf == "All" else [r for r in rules if r.get("Status","").startswith(rf[:2])]

        for r in show_r:
            status = r.get("Status","")
            affected = r.get("Affected", 0)
            is_pass = status.startswith("✅")
            is_fail = status.startswith("❌")
            bc = "#238636" if is_pass else "#da3633" if is_fail else "#d29922"
            bg = "#0d2019" if is_pass else "#1a0d0d" if is_fail else "#1a1500"
            st.markdown(f"""
<div style="background:{bg};border-left:3px solid {bc};border-radius:0 8px 8px 0;
padding:12px 16px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <span style="font-size:13px;font-weight:600;color:#e6edf3;">{r.get('Rule','—')}</span>
    {f'<span style="font-size:11px;color:#da3633;margin-left:10px;">{affected} affected</span>' if affected else ''}
  </div>
  <span style="font-size:13px;font-weight:700;color:{bc};white-space:nowrap;">{status}</span>
</div>""", unsafe_allow_html=True)
    else:
        st.info("Rule validation data not available in this snapshot.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — NBC
# ─────────────────────────────────────────────────────────────────────────────
with tabs[5]:
    st.markdown("#### 🏛️ NBC 2016 Compliance")
    st.caption("National Building Code of India — automated compliance check from IFC model data.")

    # Derive NBC checks from rule data or show generic message
    if rules:
        # Pull relevant rules as NBC proxies
        nbc_checks = []
        nbc_map = {
            "FireRating":        ("4.3.1 — Wall FireRating",       "Walls must have fire resistance rating"),
            "Pset_DoorCommon":   ("4.5.2 — Door Data Completeness","Doors require standard property data"),
            "ThermalTransmittance":("5.4.3 — Window Thermal Value","Windows need thermal transmittance"),
            "storey":            ("3.2.1 — Spatial Assignment",    "All elements must be assigned to a storey"),
            "hosted":            ("4.5.1 — Door/Window Hosting",   "Doors/windows must be hosted in walls"),
            "GlobalId":          ("2.1.1 — Element Uniqueness",    "All GlobalIds must be unique"),
        }
        for r in rules:
            rule_text = r.get("Rule","").lower()
            for key, (clause, note) in nbc_map.items():
                if key.lower() in rule_text:
                    status_r = r.get("Status","")
                    is_pass = status_r.startswith("✅")
                    nbc_checks.append({
                        "Clause":  clause,
                        "Status":  "✅ Pass" if is_pass else ("⚠️ Check" if "WARN" in status_r else "❌ Fail"),
                        "Note":    f"{r.get('Affected',0)} elements affected" if r.get("Affected",0) > 0 else note,
                    })
                    break

        if not nbc_checks:
            st.info("NBC compliance mapping not available for this model's rules.")
        else:
            nbc_p = sum(1 for n in nbc_checks if n["Status"].startswith("✅"))
            nbc_f = sum(1 for n in nbc_checks if n["Status"].startswith("❌"))
            nbc_w = sum(1 for n in nbc_checks if n["Status"].startswith("⚠️"))
            comp_pct = round(nbc_p / len(nbc_checks) * 100) if nbc_checks else 0
            comp_col = "#238636" if comp_pct >= 80 else "#d29922" if comp_pct >= 50 else "#da3633"

            nc1,nc2,nc3,nc4 = st.columns(4)
            nc1.metric("Clauses",      len(nbc_checks))
            nc2.metric("✅ Compliant", nbc_p)
            nc3.metric("❌ Non-Compliant", nbc_f)
            nc4.metric("Compliance",   f"{comp_pct}%")

            st.markdown(f"""
<div style="background:{comp_col}12;border:2px solid {comp_col};border-radius:12px;padding:16px 22px;margin:12px 0;">
  <div style="font-size:11px;color:#6e7f96;letter-spacing:1px;">NBC 2016 OVERALL COMPLIANCE</div>
  <div style="font-size:26px;font-weight:800;color:{comp_col};">{comp_pct}% — {'Compliant' if comp_pct>=80 else 'Partially Compliant'}</div>
</div>""", unsafe_allow_html=True)

            st.markdown("---")
            for n in nbc_checks:
                is_pass = n["Status"].startswith("✅")
                is_fail = n["Status"].startswith("❌")
                bc = "#238636" if is_pass else "#da3633" if is_fail else "#d29922"
                bg = "#0d2019" if is_pass else "#1a0d0d" if is_fail else "#1a1500"
                st.markdown(f"""
<div style="background:{bg};border:1px solid {bc}55;border-radius:10px;
padding:12px 18px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-size:13px;font-weight:700;color:#e6edf3;">{n['Clause']}</div>
    <div style="font-size:11px;color:#6e7f96;margin-top:2px;">💬 {n['Note']}</div>
  </div>
  <span style="font-size:13px;font-weight:700;color:{bc};white-space:nowrap;">{n['Status']}</span>
</div>""", unsafe_allow_html=True)
    else:
        st.info("NBC compliance data requires rule validation data in the snapshot.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — RELATIONSHIPS
# ─────────────────────────────────────────────────────────────────────────────
with tabs[6]:
    st.markdown("#### 🔗 IFC Relationship Summary")
    st.caption(f"{g('rel_loss_count')} relationship issues · {g('rel_loss_pct')}% of elements affected")

    if rels:
        max_count = max((r.get("Count",0) for r in rels), default=1) or 1
        for r in rels:
            count = r.get("Count", 0)
            bp    = count / max_count * 100
            st.markdown(f"""
<div style="background:#0d1117;border:1px solid #1e2733;border-radius:10px;padding:12px 18px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div>
      <div style="font-size:12px;font-weight:700;color:#e6edf3;font-family:'JetBrains Mono',monospace;">{r.get('Relationship','—')}</div>
      <div style="font-size:11px;color:#6e7f96;">{r.get('Meaning','')}</div>
    </div>
    <span style="font-size:20px;font-weight:800;color:#3b8eea;">{count}</span>
  </div>
  {bar(bp, '#3b8eea', 4)}
</div>""", unsafe_allow_html=True)
    else:
        # Fallback: show from analysis
        rel_summary = an.get("relationship_summary", [])
        if rel_summary:
            max_c = max((r.get("Count",0) for r in rel_summary), default=1) or 1
            for r in rel_summary:
                count = r.get("Count",0)
                st.markdown(f"""
<div style="background:#0d1117;border:1px solid #1e2733;border-radius:10px;padding:12px 18px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div>
      <div style="font-size:12px;font-weight:700;color:#e6edf3;font-family:'JetBrains Mono',monospace;">{r.get('Relationship','—')}</div>
      <div style="font-size:11px;color:#6e7f96;">{r.get('Meaning','')}</div>
    </div>
    <span style="font-size:20px;font-weight:800;color:#3b8eea;">{count}</span>
  </div>
  {bar(count/max_c*100, '#3b8eea', 4)}
</div>""", unsafe_allow_html=True)
        else:
            st.info("Relationship data not available in this snapshot.")

    st.markdown("---")
    st.markdown(f"""
<div style="background:#1a0d0d;border:1px solid #da3633;border-radius:12px;padding:18px;">
  <div style="font-size:11px;color:#6e7f96;letter-spacing:1px;margin-bottom:8px;">RELATIONSHIP ISSUES DETECTED</div>
  <div style="font-size:36px;font-weight:800;color:#da3633;margin-bottom:4px;">{g('rel_loss_count')}</div>
  <div style="font-size:12px;color:#6e7f96;margin-bottom:12px;">elements with missing or broken relationships ({g('rel_loss_pct')}%)</div>
  <div style="font-size:12px;color:#6e7f96;border-top:1px solid #2d1515;padding-top:12px;">
    💡 Fix: Re-export from authoring tool with "Include Spatial Container" enabled.
    Ensure all doors/windows are placed as wall-hosted elements.
  </div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# WHAT THIS SYSTEM DOES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style="margin-bottom:6px;display:flex;align-items:center;gap:8px;">
  <span style="width:10px;height:10px;border-radius:50%;background:#3fb950;display:inline-block;flex-shrink:0;"></span>
  <span style="font-size:15px;font-weight:700;color:#e6edf3;">"What BIMGuard does"</span>
</div>
<div style="background:#0d1117;border:1px solid #1e2733;border-radius:10px;padding:14px 18px;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#c9d1d9;line-height:2;">
    ✓&nbsp; Detects IFC data loss<br>
    ✓&nbsp; Classifies proxy elements<br>
    ✓&nbsp; Suggests corrections<br>
    ✓&nbsp; Validates with rules &amp; NBC<br>
    ✓&nbsp; Exports issues via BCF
  </div>
</div>
""", unsafe_allow_html=True)
