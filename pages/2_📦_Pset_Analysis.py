import streamlit as st
import ifcopenshell
import pandas as pd
from fpdf import FPDF
import datetime

st.set_page_config(page_title="Pset Analysis", page_icon="📦", layout="wide")

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container { background-color: #0d1117 !important; color: #e6edf3 !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background-color: #161b22 !important; border-right: 1px solid #30363d !important; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
h1,h2,h3,h4,p,span,label { color: #e6edf3 !important; }
[data-testid="stMetric"] { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:12px; }
div[data-testid="stButton"] > button { background:#161b22 !important; border:1px solid #30363d !important; color:#e6edf3 !important; border-radius:8px !important; }
div[data-testid="stButton"] > button:hover { background:#1c2333 !important; border-color:#58a6ff !important; }
[data-testid="stExpander"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { background:#161b22 !important; border-bottom:2px solid #30363d !important; }
[data-testid="stTabs"] [data-baseweb="tab"] { background:transparent !important; color:#8b949e !important; }
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] { color:#58a6ff !important; border-bottom:2px solid #58a6ff !important; }
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

try:
    model = ifcopenshell.open("temp.ifc")
except Exception:
    st.warning("No IFC file found. Please upload on the Home page first.")
    st.stop()

ELEM_PSET_MAP = {
    "IfcWall":                  "Pset_WallCommon",
    "IfcWallStandardCase":      "Pset_WallCommon",
    "IfcDoor":                  "Pset_DoorCommon",
    "IfcWindow":                "Pset_WindowCommon",
    "IfcSlab":                  "Pset_SlabCommon",
    "IfcColumn":                "Pset_ColumnCommon",
    "IfcBeam":                  "Pset_BeamCommon",
    "IfcRoof":                  "Pset_RoofCommon",
    "IfcStair":                 "Pset_StairCommon",
    "IfcRailing":               "Pset_RailingCommon",
    "IfcPipeSegment":           "Pset_PipeSegmentTypeCommon",
    "IfcPipeFitting":           "Pset_PipeFittingTypeCommon",
    "IfcFlowSegment":           "Pset_FlowSegmentTypeCommon",
    "IfcFlowTerminal":          "Pset_FlowTerminalTypeCommon",
    "IfcMechanicalEquipment":   "Pset_ManufacturerTypeInformation",
    "IfcEnergyConversionDevice":"Pset_EnergyConversionDeviceCommon",
    "IfcElectricalElement":     "Pset_ElectricalDeviceCommon",
    "IfcLightFixture":          "Pset_LightFixtureTypeCommon",
    "IfcDistributionElement":   "Pset_DistributionSystemCommon",
    "IfcPlant":                 "Pset_PlantCommon",
}

SKIP_TYPES = {
    "IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
    "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject",
    "IfcRelAggregates","IfcZone","IfcSpatialZone",
}

# Scan all elements
results = []
type_summary = {}

for elem in model.by_type("IfcProduct"):
    etype = elem.is_a()
    if etype in SKIP_TYPES or etype == "IfcBuildingElementProxy":
        continue
    req_pset = ELEM_PSET_MAP.get(etype)
    if not req_pset:
        continue

    actual_psets = []
    for d in getattr(elem, "IsDefinedBy", []):
        if d.is_a("IfcRelDefinesByProperties"):
            ps = d.RelatingPropertyDefinition
            if ps and ps.is_a("IfcPropertySet"):
                actual_psets.append(ps.Name)

    has_req = req_pset in actual_psets
    results.append({
        "Element Name":  elem.Name or "Unnamed",
        "GlobalId":      elem.GlobalId,
        "IFC Type":      etype,
        "Required Pset": req_pset,
        "Has Required":  has_req,
        "Status":        "Present" if has_req else "Missing",
        "All Psets":     ", ".join(actual_psets) if actual_psets else "None",
    })
    if etype not in type_summary:
        type_summary[etype] = {"req_pset": req_pset, "total": 0, "with_pset": 0, "without_pset": 0}
    type_summary[etype]["total"]       += 1
    type_summary[etype]["with_pset"]   += int(has_req)
    type_summary[etype]["without_pset"]+= int(not has_req)

if not results:
    st.title("📦 Pset Analysis")
    st.info("No elements with standard Pset requirements found in this model.")
    st.stop()

total_checked = len(results)
total_with    = sum(1 for r in results if r["Has Required"])
total_missing = total_checked - total_with
pset_pct      = round(total_with / total_checked * 100, 1) if total_checked else 0

if   pset_pct >= 85: pset_col, pset_grade = "#238636","Excellent"
elif pset_pct >= 70: pset_col, pset_grade = "#58a6ff","Good"
elif pset_pct >= 50: pset_col, pset_grade = "#d29922","Fair"
else:                pset_col, pset_grade = "#da3633","Poor"

st.title("📦 Property Set (Pset) Analysis")
st.caption("Completeness check for standard IFC property sets across all element types.")
st.markdown("---")

m1,m2,m3 = st.columns(3)
m1.metric("Elements Checked", total_checked)
m2.metric("Pset Present",     total_with)
m3.metric("Pset Missing",     total_missing)

st.markdown(f"""
<div style="background:{pset_col}18;border:2px solid {pset_col};border-radius:12px;
padding:16px 24px;margin:12px 0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
  <div>
    <div style="font-size:11px;color:#8b949e;letter-spacing:1px;">PSET COMPLETENESS SCORE</div>
    <div style="font-size:28px;font-weight:800;color:{pset_col};">{pset_pct}% — {pset_grade}</div>
    <div style="font-size:12px;color:#8b949e;margin-top:4px;">
      {total_with} of {total_checked} elements have their required property set
    </div>
  </div>
  <div style="font-size:12px;color:#8b949e;max-width:280px;">
    Pset completeness contributes <strong style="color:{pset_col};">40 points</strong>
    to the overall model quality score.<br>Fixing missing Psets improves your score directly.
  </div>
</div>""", unsafe_allow_html=True)

st.markdown("---")

tab1, tab2, tab4 = st.tabs(["📊 Type Summary","🔍 Element Details","📄 Export"])

with tab1:
    st.subheader("Pset Completeness by IFC Type")
    for etype, data in sorted(type_summary.items(), key=lambda x: x[1]["without_pset"], reverse=True):
        total = data["total"]; wp = data["with_pset"]; wo = data["without_pset"]
        pct   = round(wp/total*100,1) if total else 0
        col   = "#238636" if pct==100 else "#d29922" if pct>=50 else "#da3633"
        badge = f"<span style='background:#da363322;color:#da3633;border:1px solid #da3633;border-radius:4px;padding:1px 8px;font-size:10px;'>{wo} missing</span>" if wo else "<span style='background:#23863622;color:#238636;border:1px solid #238636;border-radius:4px;padding:1px 8px;font-size:10px;'>Complete</span>"
        st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div>
      <span style="font-size:14px;font-weight:700;color:#e6edf3;">{etype}</span>
      <span style="font-size:11px;color:#8b949e;margin-left:8px;">→ {data['req_pset']}</span>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      {badge}
      <span style="font-size:16px;font-weight:800;color:{col};">{pct}%</span>
      <span style="font-size:11px;color:#8b949e;">{wp}/{total}</span>
    </div>
  </div>
  <div style="background:#21262d;border-radius:4px;height:8px;overflow:hidden;">
    <div style="width:{pct}%;background:{col};height:8px;border-radius:4px;"></div>
  </div>
</div>""", unsafe_allow_html=True)

with tab2:
    st.subheader("Element-level Pset Details")
    f1,f2,f3 = st.columns(3)
    filter_status = f1.selectbox("Status",["All","Missing","Present"])
    filter_type   = f2.selectbox("IFC Type",["All"]+sorted(set(r["IFC Type"] for r in results)))
    search        = f3.text_input("Search name","",placeholder="e.g. Wall_001")

    filtered = results[:]
    if filter_status == "Missing": filtered = [r for r in filtered if not r["Has Required"]]
    elif filter_status == "Present": filtered = [r for r in filtered if r["Has Required"]]
    if filter_type != "All": filtered = [r for r in filtered if r["IFC Type"]==filter_type]
    if search: filtered = [r for r in filtered if search.lower() in r["Element Name"].lower()]

    st.caption(f"Showing **{len(filtered)}** of **{len(results)}** elements")
    if filtered:
        st.dataframe(pd.DataFrame([{
            "Element Name":  r["Element Name"],
            "IFC Type":      r["IFC Type"],
            "Required Pset": r["Required Pset"],
            "Status":        r["Status"],
            "All Psets":     r["All Psets"],
            "GlobalId":      r["GlobalId"][:22]+"…",
        } for r in filtered]), use_container_width=True, hide_index=True, height=450)
    else:
        st.info("No elements match the filters.")

with tab4:
    st.subheader("Export Pset Report")
    ec1, ec2 = st.columns(2)
    with ec1:
        csv = pd.DataFrame([{k:v for k,v in r.items() if k!="Has Required"} for r in results]).to_csv(index=False)
        st.download_button("⬇️ Download CSV", data=csv, file_name="pset_analysis.csv", mime="text/csv", use_container_width=True)
    with ec2:
        if st.button("📄 Generate PDF", use_container_width=True):
            def safe(t): return str(t).encode("latin-1","replace").decode("latin-1")
            pdf = FPDF(); pdf.add_page()
            pdf.set_fill_color(13,31,61); pdf.rect(0,0,210,30,"F")
            pdf.set_font("Arial","B",16); pdf.set_text_color(255,255,255)
            pdf.cell(0,10,"IFC Pset Analysis Report",ln=True,align="C")
            pdf.set_font("Arial",size=9)
            pdf.cell(0,6,safe(f"Generated: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}  |  KPRIET — CSE"),ln=True,align="C")
            pdf.ln(5); pdf.set_text_color(0,0,0)
            pdf.set_font("Arial","B",12); pdf.cell(0,8,"Summary",ln=True)
            pdf.set_font("Arial",size=10)
            for label, val in [("Elements Checked",total_checked),("Pset Present",total_with),("Pset Missing",total_missing),("Completeness",f"{pset_pct}% — {pset_grade}")]:
                pdf.cell(0,6,safe(f"{label:20}: {val}"),ln=True)
            pdf.ln(3)
            pdf.set_font("Arial","B",12); pdf.cell(0,8,"Type-wise Summary",ln=True)
            pdf.set_font("Arial",size=9)
            for etype, data in sorted(type_summary.items(), key=lambda x: x[1]["without_pset"],reverse=True):
                t=data["total"]; wp=data["with_pset"]; wo=data["without_pset"]
                p=round(wp/t*100,1) if t else 0
                pdf.cell(0,5,safe(f"{'PASS' if wo==0 else 'FAIL':4}  {etype:35} {wp}/{t} ({p}%)  {data['req_pset']}"),ln=True)
            missing=[r for r in results if not r["Has Required"]]
            if missing:
                pdf.ln(3); pdf.set_font("Arial","B",12); pdf.cell(0,8,safe(f"Missing Psets ({len(missing)})"),ln=True)
                pdf.set_font("Arial",size=8)
                for r in missing[:150]:
                    pdf.cell(0,4,safe(f"  {r['IFC Type']:28} {r['Element Name'][:28]:28}  needs: {r['Required Pset']}"),ln=True)
                if len(missing)>150: pdf.cell(0,4,safe(f"  ... and {len(missing)-150} more"),ln=True)
            st.download_button("⬇️ Download PDF", data=pdf.output(dest="S").encode("latin-1"), file_name="pset_report.pdf", mime="application/pdf", use_container_width=True)