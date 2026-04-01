import streamlit as st
import ifcopenshell
import pandas as pd
from fpdf import FPDF
import datetime

st.set_page_config(page_title="NBC 2016 Compliance", page_icon="🇮🇳", layout="wide")

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main, .block-container {
    background-color: #0d1117 !important; color: #e6edf3 !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background-color: #161b22 !important; border-right: 1px solid #30363d !important;
}
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
h1,h2,h3,h4,p,span,label { color: #e6edf3 !important; }
[data-testid="stMetric"] { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:12px; }
div[data-testid="stButton"] > button {
    background:#161b22 !important; border:1px solid #30363d !important;
    color:#e6edf3 !important; border-radius:8px !important;
}
div[data-testid="stButton"] > button:hover { background:#1c2333 !important; border-color:#58a6ff !important; }
[data-testid="stExpander"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px; }
::-webkit-scrollbar { width:6px; } ::-webkit-scrollbar-thumb { background:#30363d; border-radius:3px; }
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

def safe(text):
    return (str(text)
        .replace("\u2014","-").replace("\u2013","-").replace("\u2019","'")
        .replace("\u2018","'").replace("\u201c",'"').replace("\u201d",'"')
        .replace("\u2192","->").replace("\u2190","<-")
        .encode("latin-1", errors="replace").decode("latin-1"))

# ══════════════════════════════════════════════════════════════════════════════
# NBC 2016 COMPLIANCE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def check_nbc_compliance(model, an):
    results = []

    walls   = model.by_type("IfcWall") + model.by_type("IfcWallStandardCase")
    doors   = model.by_type("IfcDoor")
    windows = model.by_type("IfcWindow")
    columns = model.by_type("IfcColumn")
    slabs   = model.by_type("IfcSlab")
    stairs  = model.by_type("IfcStair")
    proxies = model.by_type("IfcBuildingElementProxy")

    def get_pset_value(elem, pset_name, prop_name):
        for d in getattr(elem, "IsDefinedBy", []):
            if d.is_a("IfcRelDefinesByProperties"):
                ps = d.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet") and ps.Name == pset_name:
                    for p in getattr(ps, "HasProperties", []):
                        if p.Name == prop_name:
                            val = getattr(p, "NominalValue", None)
                            return str(val.wrappedValue) if val else None
        return None

    def has_pset(elem, pset_name):
        for d in getattr(elem, "IsDefinedBy", []):
            if d.is_a("IfcRelDefinesByProperties"):
                ps = d.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet") and ps.Name == pset_name:
                    return True
        return False

    # ── SECTION 1: FIRE SAFETY (NBC Part 4) ──────────────────────────────────
    walls_no_fire   = [w for w in walls if not get_pset_value(w, "Pset_WallCommon", "FireRating")]
    walls_fire_pass = len(walls) - len(walls_no_fire)
    fire_pct        = round(walls_fire_pass / len(walls) * 100, 1) if walls else 100
    results.append({
        "NBC Section":   "Part 4 — Fire Safety",
        "Check":         "Walls must have FireRating defined",
        "Standard":      "NBC 2016 Cl. 4.3.2",
        "Total":         len(walls),
        "Passed":        walls_fire_pass,
        "Failed":        len(walls_no_fire),
        "Score %":       fire_pct,
        "Status":        "✅ Pass" if fire_pct >= 80 else "❌ Fail",
        "Severity":      "Critical",
        "Failed Elements": [w.Name or "Unnamed" for w in walls_no_fire[:20]],
    })

    # ── SECTION 2: STRUCTURAL SAFETY (NBC Part 6) ─────────────────────────────
    cols_no_pset    = [c for c in columns if not has_pset(c, "Pset_ColumnCommon")]
    cols_pass       = len(columns) - len(cols_no_pset)
    col_pct         = round(cols_pass / len(columns) * 100, 1) if columns else 100
    results.append({
        "NBC Section":   "Part 6 — Structural Design",
        "Check":         "Columns must have Pset_ColumnCommon",
        "Standard":      "NBC 2016 Cl. 6.1.1",
        "Total":         len(columns),
        "Passed":        cols_pass,
        "Failed":        len(cols_no_pset),
        "Score %":       col_pct,
        "Status":        "✅ Pass" if col_pct >= 80 else "❌ Fail",
        "Severity":      "Critical",
        "Failed Elements": [c.Name or "Unnamed" for c in cols_no_pset[:20]],
    })

    # Load bearing check
    walls_no_lb = [w for w in walls if get_pset_value(w, "Pset_WallCommon", "LoadBearing") is None]
    lb_pass     = len(walls) - len(walls_no_lb)
    lb_pct      = round(lb_pass / len(walls) * 100, 1) if walls else 100
    results.append({
        "NBC Section":   "Part 6 — Structural Design",
        "Check":         "Walls must have LoadBearing status defined",
        "Standard":      "NBC 2016 Cl. 6.2.3",
        "Total":         len(walls),
        "Passed":        lb_pass,
        "Failed":        len(walls_no_lb),
        "Score %":       lb_pct,
        "Status":        "✅ Pass" if lb_pct >= 80 else "❌ Fail",
        "Severity":      "High",
        "Failed Elements": [w.Name or "Unnamed" for w in walls_no_lb[:20]],
    })

    # ── SECTION 3: ACCESSIBILITY (NBC Part 8) ─────────────────────────────────
    doors_no_pset   = [d for d in doors if not has_pset(d, "Pset_DoorCommon")]
    doors_pass      = len(doors) - len(doors_no_pset)
    door_pct        = round(doors_pass / len(doors) * 100, 1) if doors else 100
    results.append({
        "NBC Section":   "Part 8 — Accessibility",
        "Check":         "Doors must have Pset_DoorCommon (width, height)",
        "Standard":      "NBC 2016 Cl. 8.2.1",
        "Total":         len(doors),
        "Passed":        doors_pass,
        "Failed":        len(doors_no_pset),
        "Score %":       door_pct,
        "Status":        "✅ Pass" if door_pct >= 80 else "❌ Fail",
        "Severity":      "High",
        "Failed Elements": [d.Name or "Unnamed" for d in doors_no_pset[:20]],
    })

    # ── SECTION 4: ENVELOPE / THERMAL (NBC Part 11) ──────────────────────────
    walls_no_ext    = [w for w in walls if get_pset_value(w, "Pset_WallCommon", "IsExternal") is None]
    ext_pass        = len(walls) - len(walls_no_ext)
    ext_pct         = round(ext_pass / len(walls) * 100, 1) if walls else 100
    results.append({
        "NBC Section":   "Part 11 — Approach to Sustainability",
        "Check":         "Walls must define IsExternal for thermal analysis",
        "Standard":      "NBC 2016 Cl. 11.2",
        "Total":         len(walls),
        "Passed":        ext_pass,
        "Failed":        len(walls_no_ext),
        "Score %":       ext_pct,
        "Status":        "✅ Pass" if ext_pct >= 80 else "❌ Fail",
        "Severity":      "Medium",
        "Failed Elements": [w.Name or "Unnamed" for w in walls_no_ext[:20]],
    })

    # ── SECTION 5: DATA INTEGRITY (NBC BIM Addendum) ─────────────────────────
    proxy_pct_val = round(len(proxies) / max(an.get("total_elements",1), 1) * 100, 1)
    proxy_pass    = 100 - proxy_pct_val
    results.append({
        "NBC Section":   "BIM Addendum — Data Integrity",
        "Check":         "No IfcBuildingElementProxy objects (semantic data loss)",
        "Standard":      "NBC 2016 BIM Addendum Cl. 3.1",
        "Total":         an.get("total_elements", 0),
        "Passed":        an.get("total_elements", 0) - len(proxies),
        "Failed":        len(proxies),
        "Score %":       round(proxy_pass, 1),
        "Status":        "✅ Pass" if proxy_pct_val <= 5 else "❌ Fail",
        "Severity":      "Critical",
        "Failed Elements": [p.Name or "Unnamed" for p in proxies[:20]],
    })

    # ── SECTION 6: WINDOWS (NBC Part 8 / Part 3) ─────────────────────────────
    wins_no_pset  = [w for w in windows if not has_pset(w, "Pset_WindowCommon")]
    wins_pass     = len(windows) - len(wins_no_pset)
    win_pct       = round(wins_pass / len(windows) * 100, 1) if windows else 100
    results.append({
        "NBC Section":   "Part 8 — Daylighting & Ventilation",
        "Check":         "Windows must have Pset_WindowCommon",
        "Standard":      "NBC 2016 Cl. 8.3.1",
        "Total":         len(windows),
        "Passed":        wins_pass,
        "Failed":        len(wins_no_pset),
        "Score %":       win_pct,
        "Status":        "✅ Pass" if win_pct >= 80 else "❌ Fail",
        "Severity":      "Medium",
        "Failed Elements": [w.Name or "Unnamed" for w in wins_no_pset[:20]],
    })

    # ── SECTION 7: SLAB (NBC Part 6) ─────────────────────────────────────────
    slabs_no_pset = [s for s in slabs if not has_pset(s, "Pset_SlabCommon")]
    slabs_pass    = len(slabs) - len(slabs_no_pset)
    slab_pct      = round(slabs_pass / len(slabs) * 100, 1) if slabs else 100
    results.append({
        "NBC Section":   "Part 6 — Floor Slabs",
        "Check":         "Slabs must have Pset_SlabCommon",
        "Standard":      "NBC 2016 Cl. 6.4.1",
        "Total":         len(slabs),
        "Passed":        slabs_pass,
        "Failed":        len(slabs_no_pset),
        "Score %":       slab_pct,
        "Status":        "✅ Pass" if slab_pct >= 80 else "❌ Fail",
        "Severity":      "Medium",
        "Failed Elements": [s.Name or "Unnamed" for s in slabs_no_pset[:20]],
    })

    return results

# ── Run checks ────────────────────────────────────────────────────────────────
st.title("🇮🇳 NBC 2016 BIM Compliance Checker")
st.caption("Validates your IFC model against National Building Code of India 2016 standards.")

with st.spinner("Running NBC 2016 compliance checks..."):
    checks = check_nbc_compliance(model, an)

# ── Overall Score ─────────────────────────────────────────────────────────────
total_checks  = len(checks)
passed_checks = sum(1 for c in checks if "Pass" in c["Status"])
failed_checks = total_checks - passed_checks
overall_pct   = round(sum(c["Score %"] for c in checks) / total_checks, 1)

if overall_pct >= 85:   grade, gcol = "Fully Compliant",     "#238636"
elif overall_pct >= 70: grade, gcol = "Largely Compliant",   "#1f6feb"
elif overall_pct >= 50: grade, gcol = "Partially Compliant", "#d29922"
else:                   grade, gcol = "Non-Compliant",        "#da3633"

st.markdown("---")
st.subheader("📊 Overall NBC 2016 Compliance")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Overall Score",    f"{overall_pct}%")
m2.metric("Total Checks",     total_checks)
m3.metric("✅ Checks Passed", passed_checks)
m4.metric("❌ Checks Failed", failed_checks)

st.markdown(f"""
<div style="background:{gcol}18;border:2px solid {gcol};border-radius:12px;padding:18px 24px;margin-top:8px;">
  <div style="font-size:12px;color:#8b949e;letter-spacing:1px;margin-bottom:4px;">NBC 2016 COMPLIANCE VERDICT</div>
  <div style="font-size:26px;font-weight:800;color:{gcol};">{grade} — {overall_pct}%</div>
  <div style="font-size:13px;color:#8b949e;margin-top:6px;">
  {"✅ This model meets NBC 2016 BIM data requirements and is ready for submission." if overall_pct >= 85
   else "⚠️ This model partially meets NBC 2016. Fix the failed checks before submission." if overall_pct >= 70
   else "🔴 This model does not meet NBC 2016 standards. Significant rework required." if overall_pct >= 50
   else "🚨 Critical non-compliance. This model cannot be submitted under NBC 2016."}
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── NBC Section Scores ────────────────────────────────────────────────────────
st.subheader("📋 NBC 2016 Section-wise Results")

for c in checks:
    pct   = c["Score %"]
    col   = "#238636" if pct >= 80 else "#d29922" if pct >= 50 else "#da3633"
    sev_c = {"Critical":"#da3633","High":"#d29922","Medium":"#1f6feb","Low":"#238636"}.get(c["Severity"],"#8b949e")

    with st.expander(f"{c['Status']}  |  {c['NBC Section']}  —  {pct}%"):
        ex1, ex2 = st.columns([2,1])
        with ex1:
            st.markdown(f"**Check:** {c['Check']}")
            st.markdown(f"**Standard Reference:** `{c['Standard']}`")
            st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-top:8px;">
  <div style="display:flex;gap:24px;flex-wrap:wrap;">
    <div><span style="color:#8b949e;font-size:11px;">TOTAL</span><br>
    <strong style="font-size:18px;">{c['Total']}</strong></div>
    <div><span style="color:#8b949e;font-size:11px;">PASSED</span><br>
    <strong style="font-size:18px;color:#238636;">{c['Passed']}</strong></div>
    <div><span style="color:#8b949e;font-size:11px;">FAILED</span><br>
    <strong style="font-size:18px;color:#da3633;">{c['Failed']}</strong></div>
  </div>
  <div style="margin-top:10px;background:#21262d;border-radius:4px;height:8px;overflow:hidden;">
    <div style="width:{pct}%;background:{col};height:8px;border-radius:4px;"></div>
  </div>
  <div style="margin-top:4px;font-size:11px;color:{col};">{pct}% compliant</div>
</div>""", unsafe_allow_html=True)

        with ex2:
            st.markdown(f"""
<div style="background:#161b22;border:1px solid {sev_c};border-radius:8px;padding:12px;text-align:center;">
  <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">SEVERITY</div>
  <div style="font-size:16px;font-weight:700;color:{sev_c};">{c['Severity']}</div>
</div>""", unsafe_allow_html=True)

        if c["Failed Elements"]:
            st.markdown(f"**Failed elements** (first {len(c['Failed Elements'])}):")
            st.markdown(" · ".join([f"`{e}`" for e in c["Failed Elements"]]))

st.markdown("---")

# ── Export NBC Report ─────────────────────────────────────────────────────────
st.subheader("📄 Export NBC 2016 Compliance Report")

if st.button("📄 Generate NBC Compliance PDF", use_container_width=True):
    pdf = FPDF()
    pdf.add_page()

    # Header
    pdf.set_fill_color(13, 31, 61)
    pdf.rect(0, 0, 210, 35, "F")
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(255,255,255)
    pdf.cell(0, 12, "NBC 2016 BIM Compliance Report", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, safe(f"IFC Semantic Data-Loss Analyzer  |  KPRIET — CSE Dept"), ln=True, align="C")
    pdf.cell(0, 6, safe(f"Generated: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(8)

    # Summary
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "Overall Compliance Summary", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 7, safe(f"Overall Score    : {overall_pct}%"), ln=True)
    pdf.cell(0, 7, safe(f"Verdict          : {grade}"), ln=True)
    pdf.cell(0, 7, safe(f"Checks Passed    : {passed_checks} / {total_checks}"), ln=True)
    pdf.cell(0, 7, safe(f"Checks Failed    : {failed_checks} / {total_checks}"), ln=True)
    pdf.ln(4)

    # Section results
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "Section-wise Results", ln=True)
    for i, c in enumerate(checks, 1):
        pdf.set_font("Arial", "B", 11)
        status_sym = "PASS" if "Pass" in c["Status"] else "FAIL"
        pdf.cell(0, 7, safe(f"{i}. [{status_sym}] {c['NBC Section']}  —  {c['Score %']}%"), ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, safe(f"   Check     : {c['Check']}"), ln=True)
        pdf.cell(0, 6, safe(f"   Standard  : {c['Standard']}"), ln=True)
        pdf.cell(0, 6, safe(f"   Result    : {c['Passed']}/{c['Total']} elements compliant"), ln=True)
        pdf.cell(0, 6, safe(f"   Severity  : {c['Severity']}"), ln=True)
        if c["Failed Elements"]:
            pdf.cell(0, 6, safe(f"   Failed    : {', '.join(c['Failed Elements'][:5])}{'...' if len(c['Failed Elements'])>5 else ''}"), ln=True)
        pdf.ln(2)

    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    st.download_button(
        "⬇️ Download NBC Compliance PDF",
        data=pdf_bytes,
        file_name="NBC2016_Compliance_Report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
