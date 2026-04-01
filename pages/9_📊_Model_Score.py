import streamlit as st
import ifcopenshell
import pandas as pd

st.set_page_config(page_title="Model Score", page_icon="📊", layout="wide")

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container { background-color: #0d1117 !important; color: #e6edf3 !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background-color: #161b22 !important; border-right: 1px solid #30363d !important; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
h1,h2,h3,h4,p,span,label { color: #e6edf3 !important; }
[data-testid="stMetric"] { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:12px; }
div[data-testid="stButton"] > button { background:#161b22 !important; border:1px solid #30363d !important;
    color:#e6edf3 !important; border-radius:8px !important; }
div[data-testid="stButton"] > button:hover { background:#1c2333 !important; border-color:#58a6ff !important; }
[data-testid="stExpander"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px !important; }
::-webkit-scrollbar { width:6px; } ::-webkit-scrollbar-thumb { background:#30363d; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    st.warning("Please log in from the Home page first.")
    st.stop()

an = st.session_state.get("analysis", {})
if not an:
    st.warning("No analysis data. Please upload an IFC file on the Home page first.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# RECALCULATE SCORE LIVE FROM CURRENT MODEL
# This ensures score reflects any corrections applied (reclassified proxies,
# injected Psets) by reading temp.ifc directly — same formula as Home.py
# ══════════════════════════════════════════════════════════════════════════════

ELEM_PSET_MAP = {
    "IfcWall":"Pset_WallCommon","IfcWallStandardCase":"Pset_WallCommon",
    "IfcDoor":"Pset_DoorCommon","IfcWindow":"Pset_WindowCommon",
    "IfcSlab":"Pset_SlabCommon","IfcColumn":"Pset_ColumnCommon",
    "IfcBeam":"Pset_BeamCommon","IfcRoof":"Pset_RoofCommon",
    "IfcStair":"Pset_StairCommon","IfcRailing":"Pset_RailingCommon",
    "IfcPipeSegment":"Pset_PipeSegmentTypeCommon",
    "IfcPipeFitting":"Pset_PipeFittingTypeCommon",
    "IfcFlowSegment":"Pset_FlowSegmentTypeCommon",
    "IfcFlowTerminal":"Pset_FlowTerminalTypeCommon",
    "IfcMechanicalEquipment":"Pset_ManufacturerTypeInformation",
    "IfcEnergyConversionDevice":"Pset_EnergyConversionDeviceCommon",
    "IfcElectricalElement":"Pset_ElectricalDeviceCommon",
    "IfcLightFixture":"Pset_LightFixtureTypeCommon",
    "IfcDistributionElement":"Pset_DistributionSystemCommon",
    "IfcPlant":"Pset_PlantCommon",
}

SKIP_TYPES = {
    "IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
    "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject",
    "IfcRelAggregates","IfcZone","IfcSpatialZone",
}

def compute_score(ifc_path="temp.ifc"):
    try:
        model = ifcopenshell.open(ifc_path)
    except Exception:
        return None

    all_elements = [e for e in model.by_type("IfcProduct") if e.is_a() not in SKIP_TYPES]
    total = len(all_elements)
    if total == 0:
        return None

    proxies   = model.by_type("IfcBuildingElementProxy")
    proxy_ct  = len(proxies)
    proxy_pct = proxy_ct / total * 100
    sem_pct   = 100 - proxy_pct

    # Pset check
    with_pset = 0
    missing_psets = []
    req_total = 0
    type_pset_stats = {}

    for elem in all_elements:
        etype    = elem.is_a()
        req_pset = ELEM_PSET_MAP.get(etype)
        if not req_pset:
            with_pset += 1
            continue
        req_total += 1
        has_req = any(
            d.is_a("IfcRelDefinesByProperties") and
            d.RelatingPropertyDefinition and
            d.RelatingPropertyDefinition.is_a("IfcPropertySet") and
            d.RelatingPropertyDefinition.Name == req_pset
            for d in getattr(elem, "IsDefinedBy", [])
        )
        if has_req:
            with_pset += 1
            type_pset_stats.setdefault(etype, {"req":req_pset,"total":0,"with":0})
            type_pset_stats[etype]["total"] += 1
            type_pset_stats[etype]["with"]  += 1
        else:
            missing_psets.append({"Name": elem.Name or "Unnamed","Type": etype,"Needs": req_pset})
            type_pset_stats.setdefault(etype, {"req":req_pset,"total":0,"with":0})
            type_pset_stats[etype]["total"] += 1

    pset_score_raw = (with_pset / total * 40) if total else 40
    sem_score_raw  = sem_pct / 100 * 60
    proxy_penalty  = proxy_pct / 100 * 30
    quality_score  = round(min(100, max(0, sem_score_raw - proxy_penalty + pset_score_raw)), 1)

    if   quality_score >= 85: grade, color = "Excellent", "#238636"
    elif quality_score >= 70: grade, color = "Good",      "#58a6ff"
    elif quality_score >= 50: grade, color = "Fair",      "#3ab8d9"
    else:                     grade, color = "Poor",      "#ff7070"

    if   proxy_pct <= 10: severity = "LOW"
    elif proxy_pct < 20:  severity = "MEDIUM"
    elif proxy_pct < 50:  severity = "HIGH"
    else:                 severity = "CRITICAL"

    pset_pct = round(with_pset / req_total * 100, 1) if req_total else 100.0

    return {
        "total": total, "proxies": proxy_ct, "proxy_pct": round(proxy_pct,1),
        "sem_pct": round(sem_pct,1),
        "sem_score": round(sem_score_raw,1),
        "proxy_penalty": round(proxy_penalty,1),
        "pset_score": round(pset_score_raw,1),
        "pset_pct": pset_pct,
        "with_pset": with_pset,
        "req_total": req_total,
        "quality_score": quality_score,
        "grade": grade, "color": color, "severity": severity,
        "missing_psets": missing_psets,
        "type_pset_stats": type_pset_stats,
    }

# ── Live recalculate — prefer corrected IFC if corrections have been applied ──
corrected_bytes = st.session_state.get("corrected_ifc_bytes")
_using_corrected = False

with st.spinner("Calculating live score from current model..."):
    if corrected_bytes:
        import tempfile as _tmpmod, os as _os
        _tmp = _tmpmod.NamedTemporaryFile(delete=False, suffix=".ifc", mode="wb")
        _tmp.write(corrected_bytes)
        _tmp.close()
        live = compute_score(_tmp.name)
        _os.unlink(_tmp.name)
        if live:
            _using_corrected = True
    if not _using_corrected:
        live = compute_score()

st.title("📊 Model Quality Score")

# Banner: which file the score is based on
if _using_corrected:
    _fix_ct  = st.session_state.get("corrected_fix_count", 0)
    _pset_ct = st.session_state.get("corrected_pset_count", 0)
    st.markdown(f"""
<div style="background:#0d2b18;border:1.5px solid #238636;border-radius:8px;
padding:10px 18px;margin-bottom:8px;display:flex;align-items:center;gap:12px;">
  <span style="font-size:18px;">✅</span>
  <div style="font-size:13px;color:#e6edf3;">
    Score reflects <strong style="color:#238636;">corrected model</strong>
    — {_fix_ct} proxy fix{'es' if _fix_ct!=1 else ''} &amp; {_pset_ct} Pset injection{'s' if _pset_ct!=1 else ''} applied.
    <span style="color:#8b949e;margin-left:8px;font-size:11px;">
      Upload the corrected IFC to the Home page to make this permanent.
    </span>
  </div>
</div>""", unsafe_allow_html=True)
else:
    st.caption("Apply corrections in Correction Suggestions, then return here to see your improved score.")

st.markdown("---")

if not live:
    # Fallback to session state score
    live = {
        "quality_score": an.get("quality_score", 0),
        "grade":  an.get("quality_grade","—"),
        "color":  an.get("quality_color","#8b949e"),
        "severity": an.get("severity","—"),
        "sem_score": an.get("score_breakdown",{}).get("sem_score",0),
        "proxy_penalty": an.get("score_breakdown",{}).get("proxy_score",0),
        "pset_score": an.get("score_breakdown",{}).get("pset_score",0),
        "pset_pct": an.get("score_breakdown",{}).get("pset_pct",0),
        "with_pset": an.get("score_breakdown",{}).get("elems_with_pset",0),
        "req_total": an.get("score_breakdown",{}).get("elems_requiring_pset",0),
        "proxies": an.get("proxy_elements",0),
        "proxy_pct": an.get("proxy_pct",0),
        "sem_pct": an.get("semantic_pct",0),
        "total": an.get("total_elements",0),
        "missing_psets": an.get("missing_pset_list",[]),
        "type_pset_stats": {},
    }
    st.warning("Could not read IFC file directly — showing last cached score.")

sc = live["quality_score"]
gr = live["grade"]
co = live["color"]

# ── Big score display ─────────────────────────────────────────────────────────
sev_col_map = {"LOW":"#238636","MEDIUM":"#58a6ff","HIGH":"#d29922","CRITICAL":"#da3633"}
sev_col = sev_col_map.get(live["severity"],"#8b949e")

st.markdown(f"""
<div style="background:{co}12;border:2px solid {co};border-radius:16px;
padding:24px 32px;margin-bottom:16px;display:flex;align-items:center;gap:40px;flex-wrap:wrap;">
  <div style="text-align:center;min-width:140px;">
    <div style="font-size:11px;color:#8b949e;letter-spacing:2px;margin-bottom:6px;">MODEL QUALITY SCORE</div>
    <div style="font-size:72px;font-weight:900;color:{co};line-height:1;">{sc}</div>
    <div style="font-size:16px;color:{co};font-weight:700;">/ 100</div>
  </div>
  <div style="flex:1;min-width:200px;">
    <div style="font-size:28px;font-weight:800;color:{co};margin-bottom:8px;">{gr}</div>
    <div style="background:#21262d;border-radius:8px;height:14px;overflow:hidden;margin-bottom:12px;">
      <div style="width:{sc}%;background:{co};height:14px;border-radius:8px;transition:width 1s;"></div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <span style="background:{sev_col}22;color:{sev_col};border:1px solid {sev_col};
      border-radius:6px;padding:3px 12px;font-size:12px;font-weight:700;">⚠ {live["severity"]}</span>
      <span style="background:#30363d;color:#8b949e;border-radius:6px;padding:3px 12px;font-size:12px;">
        {live["total"]} elements · {live["proxies"]} proxies · {len(live["missing_psets"])} missing Psets
      </span>
    </div>
  </div>
  <div style="text-align:center;min-width:120px;">
    <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">GRADES</div>
    <div style="font-size:11px;color:#238636;">✅ Excellent ≥ 85</div>
    <div style="font-size:11px;color:#58a6ff;">🔵 Good ≥ 70</div>
    <div style="font-size:11px;color:#3ab8d9;">🟡 Fair ≥ 50</div>
    <div style="font-size:11px;color:#ff7070;">🔴 Poor &lt; 50</div>
  </div>
</div>""", unsafe_allow_html=True)

# ── Score breakdown — 3 components ───────────────────────────────────────────
st.subheader("🧮 Score Breakdown")
st.caption("Score = Semantic Score − Proxy Penalty + Pset Score")

b1, b2, b3, b4 = st.columns(4)

b1.markdown(f"""
<div style="background:#161b22;border:1px solid #238636;border-radius:12px;padding:16px;text-align:center;">
  <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:4px;">① SEMANTIC RICHNESS</div>
  <div style="font-size:30px;font-weight:800;color:#238636;">+{live['sem_score']}</div>
  <div style="font-size:12px;color:#238636;margin-bottom:6px;">pts</div>
  <div style="font-size:11px;color:#8b949e;">{live['sem_pct']:.1f}% correctly typed</div>
  <div style="font-size:10px;color:#8b949e;margin-top:4px;">= (Non-proxy ÷ Total) × 60</div>
  <div style="font-size:10px;color:#8b949e;">Max: 60 pts</div>
</div>""", unsafe_allow_html=True)

b2.markdown(f"""
<div style="background:#161b22;border:1px solid #da3633;border-radius:12px;padding:16px;text-align:center;">
  <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:4px;">② PROXY PENALTY</div>
  <div style="font-size:30px;font-weight:800;color:#da3633;">−{live['proxy_penalty']}</div>
  <div style="font-size:12px;color:#da3633;margin-bottom:6px;">pts</div>
  <div style="font-size:11px;color:#8b949e;">{live['proxy_pct']:.1f}% are proxies</div>
  <div style="font-size:10px;color:#8b949e;margin-top:4px;">= (Proxy ÷ Total) × 30</div>
  <div style="font-size:10px;color:#8b949e;">Max deduction: 30 pts</div>
</div>""", unsafe_allow_html=True)

b3.markdown(f"""
<div style="background:#161b22;border:1px solid #58a6ff;border-radius:12px;padding:16px;text-align:center;">
  <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:4px;">③ PSET COMPLETENESS</div>
  <div style="font-size:30px;font-weight:800;color:#58a6ff;">+{live['pset_score']}</div>
  <div style="font-size:12px;color:#58a6ff;margin-bottom:6px;">pts</div>
  <div style="font-size:11px;color:#8b949e;">{live['pset_pct']:.1f}% have required Pset</div>
  <div style="font-size:10px;color:#8b949e;margin-top:4px;">= (With Pset ÷ Requiring Pset) × 40</div>
  <div style="font-size:10px;color:#8b949e;">Max: 40 pts</div>
</div>""", unsafe_allow_html=True)

b4.markdown(f"""
<div style="background:{co}18;border:2px solid {co};border-radius:12px;padding:16px;text-align:center;">
  <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:4px;">TOTAL</div>
  <div style="font-size:30px;font-weight:800;color:{co};">{live['sem_score']} − {live['proxy_penalty']} + {live['pset_score']}</div>
  <div style="font-size:22px;font-weight:900;color:{co};margin-top:4px;">= {sc}</div>
  <div style="font-size:13px;color:{co};font-weight:700;margin-top:4px;">{gr}</div>
</div>""", unsafe_allow_html=True)

# ── How to improve ────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 How to Improve Your Score")

tips = []
if live["proxy_pct"] > 0:
    pts = round(live["proxy_penalty"], 1)
    tips.append(("🛠️ Fix Proxy Elements",
                 f"Reclassify {live['proxies']} proxy elements → gain up to +{pts} proxy penalty removed",
                 "#da3633", "Correction Suggestions"))
if live["pset_pct"] < 100:
    missing_ct = len(live["missing_psets"])
    pts_gain   = round((100 - live["pset_pct"]) / 100 * 40, 1)
    tips.append(("📦 Add Missing Psets",
                 f"{missing_ct} elements need their required Pset → gain up to +{pts_gain} pts",
                 "#58a6ff", "Pset Analysis"))
if live["quality_score"] < 85:
    tips.append(("🤖 Use AI Smart Fix",
                 "Type one command — AI fixes all proxy elements and injects Psets automatically",
                 "#00bcd4", "AI Smart Fix"))

if tips:
    for title, desc, col, page in tips:
        st.markdown(f"""
<div style="background:#161b22;border:1px solid {col}55;border-left:4px solid {col};
border-radius:8px;padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-size:13px;font-weight:700;color:#e6edf3;">{title}</div>
    <div style="font-size:11px;color:#8b949e;margin-top:2px;">{desc}</div>
  </div>
  <span style="font-size:10px;color:{col};background:{col}22;border:1px solid {col};
  border-radius:4px;padding:2px 10px;white-space:nowrap;">→ {page}</span>
</div>""", unsafe_allow_html=True)
else:
    st.success("🏆 Model is fully optimised! Nothing left to improve.")
