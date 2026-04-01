import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

st.set_page_config(page_title="Proxy Classification", page_icon="🔎", layout="wide")

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
[data-testid="stTabs"] [data-baseweb="tab-list"] { background:#161b22 !important; border-bottom:2px solid #30363d !important; }
[data-testid="stTabs"] [data-baseweb="tab"] { background:transparent !important; color:#8b949e !important; }
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] { color:#58a6ff !important; border-bottom:2px solid #58a6ff !important; }
[data-testid="stDataFrame"], [data-testid="stDataFrame"] > div { background-color: #161b22 !important; }
[data-testid="stDataFrame"] th, [data-testid="stDataFrame"] [role="columnheader"] {
    background-color: #21262d !important; color: #e6edf3 !important; }
[data-testid="stDataFrame"] td, [data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] [role="gridcell"] * { color: #e6edf3 !important; }
::-webkit-scrollbar { width:6px; } ::-webkit-scrollbar-thumb { background:#30363d; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    st.warning("Please log in from the Home page first.")
    st.stop()

an = st.session_state.get("analysis", {})
if not an:
    st.warning("⚠️ No analysis data. Please upload an IFC file on the Home page first.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICATION LOGIC
# ══════════════════════════════════════════════════════════════════════════════

# Valid = non-physical / reference elements — no IFC semantic class needed
VALID_PROXY_KEYWORDS = [
    "rpc", "entourage", "geo", "georeference", "geo-reference",
    "survey", "origin", "basepoint", "site origin",
    "car", "vehicle", "truck", "bus",
    "people", "person", "human", "pedestrian",
]

# Invalid = real building/MEP elements that lost their semantic type — must be fixed
INVALID_PROXY_KEYWORDS = [
    "wall", "door", "window", "slab", "floor", "roof",
    "column", "beam", "stair", "railing",
    "pipe", "duct", "cable", "wire",
    "pump", "fan", "boiler", "chiller",
    "light", "fixture",
    "wash", "toilet", "sink", "bath",
    "panel", "board", "frame",
]


def classify_proxy(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in VALID_PROXY_KEYWORDS):
        return "valid"
    if any(k in n for k in INVALID_PROXY_KEYWORDS):
        return "invalid"
    return "unknown"


proxy_list  = an.get("proxy_list", [])
proxy_total = an.get("proxy_list_total", an.get("proxy_elements", 0))

classified = []
for p in proxy_list:
    name = p.get("Name") or "Unnamed"
    cls  = classify_proxy(name)
    classified.append({
        "Name":     name,
        "GlobalId": p.get("GlobalId", ""),
        "Class":    cls,
        "IFC Type": p.get("IFC Type", "IfcBuildingElementProxy"),
    })

valid_proxies   = [p for p in classified if p["Class"] == "valid"]
invalid_proxies = [p for p in classified if p["Class"] == "invalid"]
unknown_proxies = [p for p in classified if p["Class"] == "unknown"]

# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("🔎 Proxy Classification")
st.caption("All IfcBuildingElementProxy elements are classified into Valid, Invalid, or Unknown based on their element names.")
st.markdown("---")

# ── Summary metrics ────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Proxies",        proxy_total,
          help="All IfcBuildingElementProxy elements in the uploaded model")
m2.metric("✅ Valid",             len(valid_proxies),
          help="Non-physical / reference elements — RPC, entourage, survey points, vehicles. No IFC class needed.")
m3.metric("❌ Invalid",           len(invalid_proxies),
          help="Real building/MEP elements whose semantic type was lost during export. Must be reclassified.")
m4.metric("❓ Unknown",           len(unknown_proxies),
          help="Cannot be automatically determined — review manually.")

# ── Visual breakdown bar ───────────────────────────────────────────────────────
if proxy_total > 0:
    v_pct = round(len(valid_proxies)   / proxy_total * 100, 1)
    i_pct = round(len(invalid_proxies) / proxy_total * 100, 1)
    u_pct = round(len(unknown_proxies) / proxy_total * 100, 1)

    st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px 20px;margin:12px 0;">
  <div style="font-size:11px;color:#8b949e;margin-bottom:10px;letter-spacing:1px;">PROXY BREAKDOWN</div>
  <div style="display:flex;height:22px;border-radius:6px;overflow:hidden;margin-bottom:10px;">
    <div style="width:{v_pct}%;background:#238636;" title="Valid {v_pct}%"></div>
    <div style="width:{i_pct}%;background:#da3633;" title="Invalid {i_pct}%"></div>
    <div style="width:{u_pct}%;background:#8b949e;" title="Unknown {u_pct}%"></div>
  </div>
  <div style="display:flex;gap:20px;font-size:13px;flex-wrap:wrap;align-items:center;">
    <span style="display:flex;align-items:center;gap:6px;"><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:#238636;flex-shrink:0;"></span><span style="color:#e6edf3;">Valid &nbsp;</span><strong style="color:#238636;">{v_pct}%</strong><span style="color:#8b949e;">&nbsp;({len(valid_proxies)})</span></span>
    <span style="display:flex;align-items:center;gap:6px;"><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:#da3633;flex-shrink:0;"></span><span style="color:#e6edf3;">Invalid &nbsp;</span><strong style="color:#da3633;">{i_pct}%</strong><span style="color:#8b949e;">&nbsp;({len(invalid_proxies)})</span></span>
    <span style="display:flex;align-items:center;gap:6px;"><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:#8b949e;flex-shrink:0;"></span><span style="color:#e6edf3;">Unknown &nbsp;</span><strong style="color:#8b949e;">{u_pct}%</strong><span style="color:#8b949e;">&nbsp;({len(unknown_proxies)})</span></span>
  </div>
  <div style="font-size:11px;color:#8b949e;margin-top:10px;line-height:1.6;">
    <strong style="color:#238636;">✅ Valid</strong> — non-physical reference elements; no IFC class needed.&nbsp;&nbsp;
    <strong style="color:#da3633;">❌ Invalid</strong> — building/MEP elements that lost their type; go to 🛠️ Correction Suggestions to fix.&nbsp;&nbsp;
    <strong style="color:#8b949e;">❓ Unknown</strong> — review manually.
  </div>
</div>""", unsafe_allow_html=True)

elif proxy_total == 0:
    st.success("✅ No proxy elements found in this model — all elements are correctly classified!")
    st.stop()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    f"❌ Invalid ({len(invalid_proxies)})",
    f"✅ Valid ({len(valid_proxies)})",
    f"❓ Unknown ({len(unknown_proxies)})",
    "📄 Export",
])

# ── TAB 1 — Invalid ────────────────────────────────────────────────────────────
with tab1:
    st.subheader("❌ Invalid Proxies — Semantic Data Loss")
    st.caption(
        f"{len(invalid_proxies)} elements are real building or MEP components whose IFC type was lost during export. "
        "These directly reduce your model quality score and must be reclassified."
    )
    if invalid_proxies:
        search_inv = st.text_input("Search", placeholder="e.g. Wall, Pipe", key="search_inv")
        filtered_inv = [p for p in invalid_proxies
                        if search_inv.lower() in p["Name"].lower()] if search_inv else invalid_proxies
        st.caption(f"Showing {len(filtered_inv)} of {len(invalid_proxies)}")
        st.dataframe(pd.DataFrame([{
            "Element Name": p["Name"],
            "GlobalId":     p["GlobalId"][:22] + "…",
            "IFC Type":     p["IFC Type"],
            "Status":       "❌ Invalid — Fix Required",
        } for p in filtered_inv]), use_container_width=True, hide_index=True, height=420)

        st.markdown("""
<div style="background:#1a0a0a;border:1px solid #da3633;border-radius:8px;padding:10px 16px;
margin-top:6px;font-size:12px;color:#ff6b6b;">
  Go to <strong>🛠️ Correction Suggestions</strong> to reclassify these elements and download the corrected IFC file.
</div>""", unsafe_allow_html=True)
    else:
        st.success("✅ No invalid proxies found — all building elements are correctly typed!")

# ── TAB 2 — Valid ─────────────────────────────────────────────────────────────
with tab2:
    st.subheader("✅ Valid Proxies — Reference / Non-physical Elements")
    st.caption(
        f"{len(valid_proxies)} elements are intentionally non-physical (RPC trees, entourage, survey points, vehicles). "
        "No IFC semantic class is required for these."
    )
    if valid_proxies:
        search_val = st.text_input("Search", placeholder="e.g. RPC, car", key="search_val")
        filtered_val = [p for p in valid_proxies
                        if search_val.lower() in p["Name"].lower()] if search_val else valid_proxies
        st.caption(f"Showing {len(filtered_val)} of {len(valid_proxies)}")
        st.dataframe(pd.DataFrame([{
            "Element Name": p["Name"],
            "GlobalId":     p["GlobalId"][:22] + "…",
            "IFC Type":     p["IFC Type"],
            "Status":       "✅ Non-physical / Reference — No Fix Needed",
        } for p in filtered_val]), use_container_width=True, hide_index=True, height=420)
    else:
        st.info("No valid/reference proxy elements found.")

# ── TAB 3 — Unknown ───────────────────────────────────────────────────────────
with tab3:
    st.subheader("❓ Unknown Proxies — Manual Review Required")
    st.caption(
        f"{len(unknown_proxies)} proxy elements could not be automatically classified. "
        "Review each one and reclassify manually in 🛠️ Correction Suggestions."
    )
    if unknown_proxies:
        search_unk = st.text_input("Search", placeholder="e.g. Generic, Object", key="search_unk")
        filtered_unk = [p for p in unknown_proxies
                        if search_unk.lower() in p["Name"].lower()] if search_unk else unknown_proxies
        st.caption(f"Showing {len(filtered_unk)} of {len(unknown_proxies)}")
        st.dataframe(pd.DataFrame([{
            "Element Name": p["Name"],
            "GlobalId":     p["GlobalId"][:22] + "…",
            "IFC Type":     p["IFC Type"],
            "Status":       "❓ Unknown — Review Manually",
        } for p in filtered_unk]), use_container_width=True, hide_index=True, height=420)
    else:
        st.info("No unknown proxies found.")

# ── TAB 4 — Export ────────────────────────────────────────────────────────────
with tab4:
    st.subheader("📄 Export Proxy Classification Report")

    all_rows = []
    for p in valid_proxies:
        all_rows.append({"Classification": "Valid", "Element Name": p["Name"],
                         "GlobalId": p["GlobalId"], "IFC Type": p["IFC Type"],
                         "Status": "Non-physical / Reference — No Fix Needed"})
    for p in invalid_proxies:
        all_rows.append({"Classification": "Invalid", "Element Name": p["Name"],
                         "GlobalId": p["GlobalId"], "IFC Type": p["IFC Type"],
                         "Status": "Semantic Data Loss — Fix Required"})
    for p in unknown_proxies:
        all_rows.append({"Classification": "Unknown", "Element Name": p["Name"],
                         "GlobalId": p["GlobalId"], "IFC Type": p["IFC Type"],
                         "Status": "Cannot Determine — Review Manually"})

    ec1, ec2 = st.columns(2)
    with ec1:
        if all_rows:
            csv = pd.DataFrame(all_rows).to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                data=csv,
                file_name="proxy_classification.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("No proxy elements to export.")

    with ec2:
        if st.button("📄 Generate PDF", use_container_width=True):
            def safe(t): return str(t).encode("latin-1", "replace").decode("latin-1")

            pdf = FPDF()
            pdf.add_page()
            pdf.set_fill_color(13, 31, 61)
            pdf.rect(0, 0, 210, 30, "F")
            pdf.set_font("Arial", "B", 16)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 10, "Proxy Classification Report", ln=True, align="C")
            pdf.set_font("Arial", size=9)
            pdf.cell(0, 6, safe(f"Generated: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}"), ln=True, align="C")
            pdf.ln(5)
            pdf.set_text_color(0, 0, 0)

            # Summary
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "Summary", ln=True)
            pdf.set_font("Arial", size=10)
            for label, val in [
                ("Total Proxies",  proxy_total),
                ("✅ Valid",        len(valid_proxies)),
                ("❌ Invalid",      len(invalid_proxies)),
                ("❓ Unknown",      len(unknown_proxies)),
            ]:
                pdf.cell(0, 6, safe(f"  {label:20}: {val}"), ln=True)

            # Invalid section
            if invalid_proxies:
                pdf.ln(3)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, safe(f"Invalid Proxies ({len(invalid_proxies)}) — Fix Required"), ln=True)
                pdf.set_font("Arial", size=9)
                for p in invalid_proxies[:100]:
                    pdf.cell(0, 5, safe(f"  ❌  {p['Name']}  |  {p['GlobalId'][:22]}"), ln=True)
                if len(invalid_proxies) > 100:
                    pdf.cell(0, 5, safe(f"  ... and {len(invalid_proxies)-100} more"), ln=True)

            # Valid section
            if valid_proxies:
                pdf.ln(3)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, safe(f"Valid Proxies ({len(valid_proxies)}) — No Fix Needed"), ln=True)
                pdf.set_font("Arial", size=9)
                for p in valid_proxies[:100]:
                    pdf.cell(0, 5, safe(f"  ✅  {p['Name']}  |  {p['GlobalId'][:22]}"), ln=True)
                if len(valid_proxies) > 100:
                    pdf.cell(0, 5, safe(f"  ... and {len(valid_proxies)-100} more"), ln=True)

            # Unknown section
            if unknown_proxies:
                pdf.ln(3)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, safe(f"Unknown Proxies ({len(unknown_proxies)}) — Review Manually"), ln=True)
                pdf.set_font("Arial", size=9)
                for p in unknown_proxies[:100]:
                    pdf.cell(0, 5, safe(f"  ❓  {p['Name']}  |  {p['GlobalId'][:22]}"), ln=True)
                if len(unknown_proxies) > 100:
                    pdf.cell(0, 5, safe(f"  ... and {len(unknown_proxies)-100} more"), ln=True)

            st.download_button(
                "⬇️ Download PDF",
                data=pdf.output(dest="S").encode("latin-1"),
                file_name="proxy_classification_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )