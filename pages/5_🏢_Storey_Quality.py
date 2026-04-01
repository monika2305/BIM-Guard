import streamlit as st
import ifcopenshell
import pandas as pd
import json

st.set_page_config(page_title="Storey Quality Score", page_icon="🏢", layout="wide")

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
input, textarea { background-color: #161b22 !important; border: 1px solid #30363d !important; color: #e6edf3 !important; }
[data-baseweb="select"] > div:first-child { background-color: #161b22 !important; border: 1px solid #30363d !important; }
[data-baseweb="select"] span, [data-baseweb="select"] div { color: #e6edf3 !important; }
[data-baseweb="popover"], [data-baseweb="popover"] ul,
[data-baseweb="popover"] li, [data-baseweb="menu"], [data-baseweb="menu"] li {
    background-color: #161b22 !important; color: #e6edf3 !important;
}
[data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] section, [data-testid="stFileUploader"] > div {
    background-color: #161b22 !important; border-color: #30363d !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] div { color: #8b949e !important; }
[data-testid="stDataFrame"], [data-testid="stDataFrame"] > div { background-color: #161b22 !important; }
[data-testid="stDataFrame"] th, [data-testid="stDataFrame"] [role="columnheader"] {
    background-color: #21262d !important; color: #e6edf3 !important;
}
[data-testid="stDataFrame"] td, [data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] [role="gridcell"] * { color: #e6edf3 !important; }
[data-testid="stMetric"] { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 10px !important; padding: 12px !important; }
[data-testid="stExpander"] { background-color: #161b22 !important; border: 1px solid #30363d !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: #e6edf3 !important; }
div[data-testid="stButton"] > button { background: #161b22 !important; border: 1px solid #30363d !important; color: #e6edf3 !important; border-radius: 8px !important; }
div[data-testid="stButton"] > button:hover { background: #1c2333 !important; border-color: #58a6ff !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background-color: #161b22 !important;
    border-bottom: 2px solid #30363d !important;
    gap: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background-color: #161b22 !important;
    color: #8b949e !important;
    border-radius: 0 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 8px 16px !important;
    font-size: 13px !important;
    transition: color .15s !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    background-color: #1c2333 !important;
    color: #c9d1d9 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    background-color: #161b22 !important;
    color: #58a6ff !important;
    border-bottom: 2px solid #58a6ff !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    background-color: #0d1117 !important;
    padding-top: 16px !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background-color: transparent !important;
}
h1,h2,h3,h4,h5,h6,p,span,label { color: #e6edf3 !important; }
[data-testid="stCaptionContainer"] p, .stCaption, small { color: #8b949e !important; }
hr { border: none !important; border-top: 1px solid #30363d !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

</style>
""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    st.warning("Please log in from the Home page first.")
    st.stop()

try:
    model = ifcopenshell.open("temp.ifc")
except Exception:
    st.warning("⚠️ No IFC file found. Please upload a file on the Home page first.")
    st.stop()

an = st.session_state.get("analysis", {})
if not an:
    st.warning("⚠️ No analysis data. Please upload and analyse an IFC file first.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# STOREY ANALYSIS ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def analyse_storeys(model):
    storeys = model.by_type("IfcBuildingStorey")
    proxy_ids    = set(p.GlobalId for p in model.by_type("IfcBuildingElementProxy"))
    missing_pset = set()
    for w in model.by_type("IfcWall"):
        has = any(
            d.is_a("IfcRelDefinesByProperties") and
            getattr(d.RelatingPropertyDefinition, "Name","") == "Pset_WallCommon"
            for d in getattr(w, "IsDefinedBy", [])
        )
        if not has:
            missing_pset.add(w.GlobalId)

    SKIP = {"IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
            "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject"}

    storey_data = {}
    assigned_gids = set()   # track which elements are assigned to a storey

    for storey in storeys:
        name = storey.Name or f"Storey {storey.GlobalId[:8]}"
        elevation = round(float(storey.Elevation or 0), 2) if storey.Elevation else 0

        elements = []
        for rel in getattr(storey, "ContainsElements", []):
            if rel.is_a("IfcRelContainedInSpatialStructure"):
                for elem in rel.RelatedElements:
                    if elem.is_a() in SKIP:
                        continue
                    gid = elem.GlobalId
                    assigned_gids.add(gid)
                    if gid in proxy_ids:
                        issue = "proxy"
                    elif gid in missing_pset:
                        issue = "missing_pset"
                    else:
                        issue = "ok"
                    elements.append({
                        "name":  elem.Name or "Unnamed",
                        "type":  elem.is_a(),
                        "issue": issue,
                        "gid":   gid,
                    })

        total   = len(elements)
        proxies = sum(1 for e in elements if e["issue"] == "proxy")
        pset_m  = sum(1 for e in elements if e["issue"] == "missing_pset")
        ok      = sum(1 for e in elements if e["issue"] == "ok")

        if total == 0:
            score = 100.0
        else:
            sem_pct   = ok   / total * 100
            prx_pct   = proxies / total * 100
            pset_pct  = pset_m / total * 100
            score = max(0, min(100, round(
                (sem_pct/100)*60 - (prx_pct/100)*30 + (1 - pset_pct/100)*40
            , 1)))

        if   score >= 85: grade, col = "Excellent", "#238636"
        elif score >= 70: grade, col = "Good",      "#58a6ff"
        elif score >= 50: grade, col = "Fair",      "#3ab8d9"
        else:             grade, col = "Poor",      "#ff7070"

        storey_data[name] = {
            "elevation": elevation,
            "total":     total,
            "proxies":   proxies,
            "missing_pset": pset_m,
            "ok":        ok,
            "score":     score,
            "grade":     grade,
            "color":     col,
            "elements":  elements,
        }

    # Collect elements NOT assigned to any storey
    unassigned = []
    for elem in model.by_type("IfcProduct"):
        if elem.is_a() in SKIP:
            continue
        gid = elem.GlobalId
        if gid not in assigned_gids:
            if elem.GlobalId in proxy_ids:
                issue = "proxy"
            elif elem.GlobalId in missing_pset:
                issue = "missing_pset"
            else:
                issue = "ok"
            unassigned.append({
                "name":  elem.Name or "Unnamed",
                "type":  elem.is_a(),
                "issue": issue,
                "gid":   gid,
            })

    if unassigned:
        u_proxy = sum(1 for e in unassigned if e["issue"]=="proxy")
        u_pset  = sum(1 for e in unassigned if e["issue"]=="missing_pset")
        u_ok    = sum(1 for e in unassigned if e["issue"]=="ok")
        u_total = len(unassigned)
        if u_total > 0:
            u_score = max(0, min(100, round(
                (u_ok/u_total)*60 - (u_proxy/u_total)*30 + (1 - u_pset/u_total)*40, 1
            )))
            if   u_score >= 85: u_grade, u_col = "Excellent","#238636"
            elif u_score >= 70: u_grade, u_col = "Good",     "#58a6ff"
            elif u_score >= 50: u_grade, u_col = "Fair",     "#3ab8d9"
            else:               u_grade, u_col = "Poor",     "#ff7070"
            storey_data["⚠️ Unassigned (no storey)"] = {
                "elevation":    -9999,
                "total":        u_total,
                "proxies":      u_proxy,
                "missing_pset": u_pset,
                "ok":           u_ok,
                "score":        u_score,
                "grade":        u_grade,
                "color":        u_col,
                "elements":     unassigned,
            }

    # Sort by elevation (unassigned goes last)
    return dict(sorted(storey_data.items(), key=lambda x: x[1]["elevation"] if x[1]["elevation"] != -9999 else 9999))

# ── Run ───────────────────────────────────────────────────────────────────────
st.title("🏢 Storey-wise Quality Score")
st.caption("Individual BIM quality score for every floor. Elements assigned to a storey via IfcRelContainedInSpatialStructure are grouped per floor. Elements without storey assignment appear in the Unassigned bucket.")
st.info("ℹ️ Element counts per floor here show elements **directly assigned** to each storey in the IFC model. The Heatmap shows elements that have **geometric coordinates** within each zone — these may differ because some elements span multiple floors or lack storey assignments.")
st.markdown("---")

with st.spinner("Analysing each floor..."):
    storey_data = analyse_storeys(model)

if not storey_data:
    st.warning("⚠️ No storeys found in this IFC model. The model may not have floor assignments.")
    st.stop()

# ── Summary Metrics ───────────────────────────────────────────────────────────
scores     = [s["score"] for s in storey_data.values()]
avg_score  = round(sum(scores) / len(scores), 1)
best_floor = max(storey_data, key=lambda k: storey_data[k]["score"])
worst_floor= min(storey_data, key=lambda k: storey_data[k]["score"])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Floors",    len(storey_data))
m2.metric("Average Score",   f"{avg_score}/100")
m3.metric("🏆 Best Floor",   f"{best_floor} ({storey_data[best_floor]['score']}/100)")
m4.metric("⚠️ Worst Floor",  f"{worst_floor} ({storey_data[worst_floor]['score']}/100)")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 Floor-wise Score", "🔍 Element Details per Floor", "📋 Summary Table"])

# ── TAB 1 — Floor-wise Score ──────────────────────────────────────────────────
with tab1:
    st.subheader("Floor-by-Floor Quality Scores")
    st.caption("Each floor is scored 0–100 based on proxy ratio, Pset completeness, and clean element count.")
    st.markdown("<div style='display:flex;flex-direction:column;gap:10px;'>", unsafe_allow_html=True)
    for floor_name, data in storey_data.items():
        col   = data["color"]
        score = data["score"]
        grade = data["grade"]
        bar_w = score
        st.markdown(f"""
<div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:14px 18px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <div>
      <span style="font-size:15px;font-weight:700;color:#f0f4f8;">{floor_name}</span>
      <span style="font-size:11px;color:#8b949e;margin-left:10px;">Elevation: {data['elevation']}m</span>
    </div>
    <div style="text-align:right;">
      <span style="font-size:20px;font-weight:800;color:{col};">{score}/100</span>
      <span style="background:{col}22;color:{col};border:1px solid {col};border-radius:4px;
      font-size:11px;font-weight:700;padding:2px 8px;margin-left:8px;">{grade}</span>
    </div>
  </div>
  <div style="background:rgba(255,255,255,0.08);border-radius:6px;height:12px;overflow:hidden;margin-bottom:8px;">
    <div style="width:{bar_w}%;background:{col};height:12px;border-radius:6px;"></div>
  </div>
  <div style="display:flex;gap:20px;flex-wrap:wrap;">
    <span style="font-size:12px;color:#8b949e;">Total: <strong style="color:#f0f4f8;">{data['total']}</strong></span>
    <span style="font-size:12px;color:#8b949e;">🔴 Proxy: <strong style="color:#ff6b6b;">{data['proxies']}</strong></span>
    <span style="font-size:12px;color:#8b949e;">🟠 Missing Pset: <strong style="color:#ffb347;">{data['missing_pset']}</strong></span>
    <span style="font-size:12px;color:#8b949e;">🟢 Clean: <strong style="color:#58a6ff;">{data['ok']}</strong></span>
  </div>
</div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── TAB 2 — Element Details per Floor ────────────────────────────────────────
with tab2:
    st.subheader("Element Details per Floor")
    st.caption("Select a floor to inspect all elements assigned to it, filtered by issue type.")
    selected_floor = st.selectbox("Select floor to inspect", list(storey_data.keys()))
    if selected_floor:
        fd = storey_data[selected_floor]
        # Mini metrics for selected floor
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Elements", fd["total"])
        c2.metric("🔴 Proxy",        fd["proxies"])
        c3.metric("🟠 Missing Pset", fd["missing_pset"])
        c4.metric("🟢 Clean",        fd["ok"])
        if fd["elements"]:
            df = pd.DataFrame([{
                "Element Name": e["name"],
                "IFC Type":     e["type"],
                "Issue":        e["issue"],
                "GlobalId":     e["gid"][:22]+"…",
            } for e in fd["elements"]])
            issue_filter = st.selectbox(
                "Filter by issue", ["All", "proxy", "missing_pset", "ok"], key="floor_filter"
            )
            if issue_filter != "All":
                df = df[df["Issue"] == issue_filter]
            st.caption(f"Showing **{len(df)}** elements")
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No elements assigned to this floor.")

# ── TAB 3 — Summary Table ─────────────────────────────────────────────────────
with tab3:
    st.subheader("All Floors — Summary Table")
    st.caption("Complete floor-by-floor breakdown with scores and issue counts.")
    summary_rows = []
    for floor_name, data in storey_data.items():
        summary_rows.append({
            "Floor":         floor_name,
            "Elevation (m)": data["elevation"] if data["elevation"] != -9999 else "—",
            "Total":         data["total"],
            "Proxy":         data["proxies"],
            "Missing Pset":  data["missing_pset"],
            "Clean":         data["ok"],
            "Score":         f"{data['score']}/100",
            "Grade":         data["grade"],
        })
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    st.markdown("<br>", unsafe_allow_html=True)
    csv = pd.DataFrame(summary_rows).to_csv(index=False)
    st.download_button(
        "⬇️ Download Floor Report CSV",
        data=csv,
        file_name="storey_quality_scores.csv",
        mime="text/csv",
        use_container_width=True,
    )