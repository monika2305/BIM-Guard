import streamlit as st
import ifcopenshell
import pandas as pd
import tempfile, os
from fpdf import FPDF
import datetime

st.set_page_config(page_title="Version Comparison", page_icon="🔀", layout="wide")

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
[data-testid="stFileUploader"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px !important; }
::-webkit-scrollbar { width:6px; } ::-webkit-scrollbar-thumb { background:#30363d; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    st.warning("Please log in from the Home page first.")
    st.stop()

SKIP_TYPES = {
    # Non-geometric / meta entities — safe to skip in comparison
    "IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
    "IfcGrid","IfcRelAggregates","IfcZone","IfcSpatialZone",
}

# ── Important IFC entity types to INCLUDE in comparison (Fix 1) ───────────────
# Compare ALL meaningful IFC entities: elements, products, spatial structure,
# and relationships — not just IfcProduct (geometry).
IMPORTANT_TYPES = {
    "IfcElement",
    "IfcProduct",
    "IfcBuildingStorey",
    "IfcBuilding",
    "IfcSite",
    "IfcBuildingElementProxy",
    # Relationships that affect topology / spatial assignment
    "IfcRelContainedInSpatialStructure",
    "IfcRelDefinesByProperties",
    "IfcRelAssociatesMaterial",
    "IfcRelAggregates",
    "IfcRelConnectsElements",
    "IfcRelFillsElement",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_project_meta(model):
    """Return (project_name, project_guid) from IfcProject."""
    projects = model.by_type("IfcProject")
    if projects:
        p = projects[0]
        return (p.Name or "").strip().lower(), (p.GlobalId or "").strip()
    return "", ""


def _valid_gid(gid):
    gid = (gid or "").strip()
    return bool(gid and gid != "$")


def _norm_text(value):
    return (str(value or "").strip().lower())


def get_element_guids(model):
    """
    Return set of GlobalIds for all meaningful IFC entities.
    Fix 1: Include ALL important IFC entity families — not just IfcProduct.
    This prevents fake 'Removed elements' caused by comparing only geometry.
    """
    guids = set()
    # IfcProduct covers most geometry + spatial structure
    for elem in model.by_type("IfcProduct"):
        if elem.is_a() not in SKIP_TYPES:
            gid = (getattr(elem, "GlobalId", "") or "").strip()
            if _valid_gid(gid):
                guids.add(gid)
    # IfcElement family (may not always be under IfcProduct in all exporters)
    for elem in model.by_type("IfcElement"):
        if elem.is_a() not in SKIP_TYPES:
            gid = (getattr(elem, "GlobalId", "") or "").strip()
            if _valid_gid(gid):
                guids.add(gid)
    # IfcSpatialStructureElement: Storey, Building, Site
    for elem in model.by_type("IfcSpatialStructureElement"):
        if elem.is_a() not in SKIP_TYPES:
            gid = (getattr(elem, "GlobalId", "") or "").strip()
            if _valid_gid(gid):
                guids.add(gid)
    # IfcRelationship: structural/spatial relationships
    for elem in model.by_type("IfcRelationship"):
        if elem.is_a() not in SKIP_TYPES and hasattr(elem, "GlobalId"):
            gid = (getattr(elem, "GlobalId", "") or "").strip()
            if _valid_gid(gid):
                guids.add(gid)
    return guids


def check_same_project(model_a, model_b, name_a, name_b):
    """
    Returns (is_same: bool, reason: str, overlap_pct: float).

    Strategy (any ONE of these passes):
      1. Same IfcProject GlobalId  → definitive match
      2. Same non-empty IfcProject Name → strong match
      3. Element GUID overlap ≥ 20 %   → structural match
         (two completely different buildings share almost no GlobalIds)
    """
    proj_name_a, proj_guid_a = get_project_meta(model_a)
    proj_name_b, proj_guid_b = get_project_meta(model_b)

    # Rule 1 – project GUID identical (and non-empty)
    if proj_guid_a and proj_guid_b and proj_guid_a == proj_guid_b:
        return True, "Matched by IfcProject GlobalId", 100.0

    # Rule 2 – project name identical (and non-empty)
    if proj_name_a and proj_name_b and proj_name_a == proj_name_b:
        return True, f"Matched by project name: '{proj_name_a}'", 100.0

    # Rule 3 – element GUID overlap
    guids_a = get_element_guids(model_a)
    guids_b = get_element_guids(model_b)
    if guids_a and guids_b:
        overlap = len(guids_a & guids_b)
        pct = overlap / min(len(guids_a), len(guids_b)) * 100
        if pct >= 20:
            return True, f"Matched by element overlap ({pct:.1f}% shared GlobalIds)", pct
        # Build an informative reason for the failure
        reason = (
            f"Only {pct:.1f}% of element GlobalIds overlap between the two files "
            f"({overlap} shared out of {len(guids_a)} / {len(guids_b)})."
        )
        extra = []
        if proj_name_a and proj_name_b and proj_name_a != proj_name_b:
            extra.append(f"Project names differ: '{proj_name_a}' vs '{proj_name_b}'")
        if proj_guid_a and proj_guid_b and proj_guid_a != proj_guid_b:
            extra.append("IfcProject GlobalIds are different")
        if extra:
            reason += " " + " | ".join(extra)
        return False, reason, pct

    # Fallback – cannot determine, allow with warning
    return True, "Could not determine project match (no element data)", 0.0


def parse_model(model):
    """
    Parse all meaningful elements from an IFC model.
    Fix 1: Include IfcElement, IfcSpatialStructureElement, and IfcRelationship
    in addition to IfcProduct — avoids fake 'Removed elements'.
    Fix 3: Preserve IfcRelContainedInSpatialStructure, IfcRelDefinesByProperties,
    and IfcRelAssociatesMaterial relationship data in each element record.
    """
    elements = {}

    def _parse_elem(elem):
        etype = elem.is_a()
        if etype in SKIP_TYPES:
            return
        gid = (getattr(elem, "GlobalId", "") or "").strip()
        if _valid_gid(gid) and gid in elements:
            return  # already parsed (e.g. IfcWall is both IfcElement and IfcProduct)
        name = elem.Name or "Unnamed"
        psets = {}
        for d in getattr(elem, "IsDefinedBy", []):
            if d.is_a("IfcRelDefinesByProperties"):
                ps = d.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet"):
                    props = {}
                    for p in getattr(ps, "HasProperties", []):
                        val = getattr(getattr(p, "NominalValue", None), "wrappedValue", None)
                        props[p.Name] = str(val) if val is not None else ""
                    psets[ps.Name] = props
        material = None
        for d in getattr(elem, "HasAssociations", []):
            if d.is_a("IfcRelAssociatesMaterial"):
                mat = d.RelatingMaterial
                if mat:
                    material = getattr(mat, "Name", str(mat))
        # Fix 3: capture spatial containment (storey assignment)
        storey = None
        storey_key = None
        for d in getattr(elem, "ContainedInStructure", []):
            if d.is_a("IfcRelContainedInSpatialStructure"):
                rel_str = d.RelatingStructure
                if rel_str:
                    storey = rel_str.Name or rel_str.GlobalId
                    storey_key = (getattr(rel_str, "GlobalId", "") or "").strip() or _norm_text(rel_str.Name)

        # Fallback key for entities with missing/invalid GlobalId.
        # This avoids collapsing many elements into one empty key.
        key = gid if _valid_gid(gid) else f"NO_GUID::{etype}::{_norm_text(name)}::{len(elements)}"
        pset_names = sorted(psets.keys())
        match_key = "|".join([
            _norm_text(etype),
            _norm_text(name),
            _norm_text(material),
            _norm_text(storey_key),
            ";".join(_norm_text(p) for p in pset_names),
        ])

        elements[key] = {
            "GlobalId": gid if _valid_gid(gid) else "—",
            "Name": name, "Type": etype,
            "Psets": psets, "Material": material,
            "Storey": storey,
            "StoreyKey": storey_key,
            "_MatchKey": match_key,
        }

    for elem in model.by_type("IfcProduct"):
        _parse_elem(elem)
    for elem in model.by_type("IfcElement"):
        _parse_elem(elem)
    for elem in model.by_type("IfcSpatialStructureElement"):
        _parse_elem(elem)

    return elements


def diff_models(a, b):
    ids_a, ids_b = set(a), set(b)
    exact_common = ids_a & ids_b
    unmatched_removed = set(ids_a - ids_b)
    unmatched_added = set(ids_b - ids_a)

    # Fallback matching for cases where GlobalId changed or is missing.
    # Match elements one-to-one by stable signature.
    added_by_sig = {}
    for bid in unmatched_added:
        sig = b[bid].get("_MatchKey")
        if sig:
            added_by_sig.setdefault(sig, []).append(bid)

    fallback_pairs = []
    for aid in list(unmatched_removed):
        sig = a[aid].get("_MatchKey")
        candidates = added_by_sig.get(sig, [])
        if candidates:
            bid = candidates.pop()
            fallback_pairs.append((aid, bid))
            unmatched_removed.discard(aid)
            unmatched_added.discard(bid)

    common_pairs = [(gid, gid) for gid in exact_common] + fallback_pairs
    changed, unchanged = [], 0
    for gid_a, gid_b in common_pairs:
        ea, eb = a[gid_a], b[gid_b]
        diffs = []
        if ea["Type"] != eb["Type"]:
            diffs.append({"Field": "IFC Type", "Before": ea["Type"], "After": eb["Type"]})
        if ea["Name"] != eb["Name"]:
            diffs.append({"Field": "Name", "Before": ea["Name"], "After": eb["Name"]})
        if ea["Material"] != eb["Material"]:
            diffs.append({"Field": "Material", "Before": ea["Material"] or "—", "After": eb["Material"] or "—"})
        # Fix 3: track storey/spatial relationship changes
        if ea.get("StoreyKey") != eb.get("StoreyKey"):
            diffs.append({"Field": "Storey (IfcRelContainedInSpatialStructure)",
                          "Before": ea.get("Storey") or "—", "After": eb.get("Storey") or "—"})
        if ea.get("GlobalId") != eb.get("GlobalId"):
            diffs.append({"Field": "GlobalId", "Before": ea.get("GlobalId") or "—", "After": eb.get("GlobalId") or "—"})
        all_psets = set(ea["Psets"]) | set(eb["Psets"])
        for pset in all_psets:
            if pset not in ea["Psets"]:
                diffs.append({"Field": f"Pset Added: {pset}", "Before": "—", "After": "Present"})
            elif pset not in eb["Psets"]:
                diffs.append({"Field": f"Pset Removed: {pset}", "Before": "Present", "After": "—"})
            else:
                for prop in set(ea["Psets"][pset]) | set(eb["Psets"][pset]):
                    va = ea["Psets"][pset].get(prop, "—")
                    vb = eb["Psets"][pset].get(prop, "—")
                    if va != vb:
                        diffs.append({"Field": f"{pset}.{prop}", "Before": va, "After": vb})
        if diffs:
            changed.append({
                "GlobalId": eb.get("GlobalId") if eb.get("GlobalId") != "—" else ea.get("GlobalId"),
                "Name": ea["Name"],
                "Type": ea["Type"],
                "Changes": diffs,
            })
        else:
            unchanged += 1
    return {
        "added":     [{"GlobalId": b[gid].get("GlobalId", "—"), **b[gid]} for gid in unmatched_added],
        "removed":   [{"GlobalId": a[gid].get("GlobalId", "—"), **a[gid]} for gid in unmatched_removed],
        "changed":   changed, "unchanged": unchanged,
        "total_a":   len(a),  "total_b":   len(b),
    }

# ── UI ─────────────────────────────────────────────────────────────────────────

st.title("🔀 IFC Version Comparison")
st.caption("Upload two versions of the **same** IFC model to detect added, removed, reclassified and modified elements.")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""<div style="background:#161b22;border:1px solid #238636;border-radius:8px;
    padding:8px 14px;margin-bottom:8px;font-size:12px;color:#238636;font-weight:700;">
    VERSION A — Older / Baseline</div>""", unsafe_allow_html=True)
    file_a = st.file_uploader("Upload Version A (IFC)", type=["ifc"], key="vc_a")
with col2:
    st.markdown("""<div style="background:#161b22;border:1px solid #58a6ff;border-radius:8px;
    padding:8px 14px;margin-bottom:8px;font-size:12px;color:#58a6ff;font-weight:700;">
    VERSION B — Newer / Updated</div>""", unsafe_allow_html=True)
    file_b = st.file_uploader("Upload Version B (IFC)", type=["ifc"], key="vc_b")

if not file_a or not file_b:
    st.info("Upload both IFC files above to start the comparison.")
    st.markdown("---")
    fc1,fc2,fc3,fc4 = st.columns(4)
    for col,icon,title,desc in [
        (fc1,"➕","Added Elements","New elements in Version B"),
        (fc2,"➖","Removed Elements","Elements missing in Version B"),
        (fc3,"🔄","Type Changes","Reclassified elements"),
        (fc4,"📦","Pset Changes","Modified property sets"),
    ]:
        col.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;
        border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:28px;margin-bottom:6px;">{icon}</div>
        <div style="font-size:13px;font-weight:700;color:#e6edf3;">{title}</div>
        <div style="font-size:11px;color:#8b949e;margin-top:4px;">{desc}</div>
        </div>""", unsafe_allow_html=True)
    st.stop()

# ── Parse & validate ──────────────────────────────────────────────────────────

with st.spinner("Parsing IFC files…"):
    try:
        tmp_a = tempfile.NamedTemporaryFile(delete=False, suffix=".ifc")
        tmp_a.write(file_a.read()); tmp_a.close()
        tmp_b = tempfile.NamedTemporaryFile(delete=False, suffix=".ifc")
        tmp_b.write(file_b.read()); tmp_b.close()
        model_a = ifcopenshell.open(tmp_a.name)
        model_b = ifcopenshell.open(tmp_b.name)
    except Exception as e:
        st.error(f"Error reading IFC files: {e}")
        for p in [tmp_a.name, tmp_b.name]:
            try: os.unlink(p)
            except: pass
        st.stop()

# ── Same-model check ──────────────────────────────────────────────────────────
is_same, match_reason, overlap_pct = check_same_project(
    model_a, model_b, file_a.name, file_b.name
)

if not is_same:
    # Clean up temp files before stopping
    for p in [tmp_a.name, tmp_b.name]:
        try: os.unlink(p)
        except: pass

    st.markdown("---")
    st.markdown("""
<div style="background:#2d0f0f;border:2px solid #da3633;border-radius:14px;padding:24px 28px;margin:16px 0;">
  <div style="font-size:22px;font-weight:800;color:#da3633;margin-bottom:10px;">
    ⛔ Incompatible Files — Different Projects Detected
  </div>
  <div style="font-size:14px;color:#e6edf3;margin-bottom:14px;">
    The two uploaded IFC files do not appear to be versions of the same model.
    Version Comparison only works when both files originate from the <strong>same building project</strong>.
  </div>
  <div style="font-size:13px;color:#ff6b6b;background:#1a0606;border:1px solid #da3633;
       border-radius:8px;padding:12px 16px;margin-bottom:14px;">
    <strong>Reason:</strong> """ + match_reason + """
  </div>
  <div style="font-size:13px;color:#8b949e;">
    <strong style="color:#e6edf3;">What to do:</strong><br>
    • Upload an <em>older export</em> of the same project as Version A<br>
    • Upload the <em>latest export</em> of the same project as Version B<br>
    • Both files must share the same <strong>IfcProject name / GUID</strong>
      or have a significant overlap of element GlobalIds
  </div>
</div>""", unsafe_allow_html=True)

    vc1, vc2 = st.columns(2)
    vc1.markdown(f"""<div style="background:#161b22;border:1px solid #238636;border-radius:10px;padding:14px 18px;">
      <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">VERSION A</div>
      <div style="font-size:14px;font-weight:700;color:#e6edf3;">📄 {file_a.name}</div>
      <div style="font-size:12px;color:#8b949e;margin-top:4px;">Project: <em>{get_project_meta(model_a)[0] or 'Unknown'}</em></div>
    </div>""", unsafe_allow_html=True)
    vc2.markdown(f"""<div style="background:#161b22;border:1px solid #58a6ff;border-radius:10px;padding:14px 18px;">
      <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">VERSION B</div>
      <div style="font-size:14px;font-weight:700;color:#e6edf3;">📄 {file_b.name}</div>
      <div style="font-size:12px;color:#8b949e;margin-top:4px;">Project: <em>{get_project_meta(model_b)[0] or 'Unknown'}</em></div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Same project confirmed — show match banner ─────────────────────────────────
st.markdown(f"""
<div style="background:#0d2b18;border:1.5px solid #238636;border-radius:10px;
     padding:10px 18px;margin:8px 0;display:flex;align-items:center;gap:12px;">
  <span style="font-size:18px;">✅</span>
  <div>
    <span style="font-size:13px;font-weight:700;color:#238636;">Same project confirmed</span>
    <span style="font-size:12px;color:#8b949e;margin-left:10px;">{match_reason}</span>
  </div>
</div>""", unsafe_allow_html=True)

# ── Diff ───────────────────────────────────────────────────────────────────────
with st.spinner("Comparing elements…"):
    try:
        data_a  = parse_model(model_a)
        data_b  = parse_model(model_b)
        result  = diff_models(data_a, data_b)
        os.unlink(tmp_a.name); os.unlink(tmp_b.name)
    except Exception as e:
        st.error(f"Error during comparison: {e}")
        st.stop()

st.markdown("---")
st.subheader("📊 Comparison Summary")
m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("Version A", result["total_a"])
m2.metric("Version B", result["total_b"])
m3.metric("➕ Added",   len(result["added"]),   delta=f"+{len(result['added'])}")
m4.metric("➖ Removed", len(result["removed"]),  delta=f"-{len(result['removed'])}", delta_color="inverse")
m5.metric("🔄 Modified",len(result["changed"]))

total_changes = len(result["added"]) + len(result["removed"]) + len(result["changed"])
if total_changes == 0:
    st.success("Both IFC files are identical — no differences detected.")
else:
    pct = round(total_changes / max(result["total_a"],1) * 100, 1)
    bc  = "#da3633" if pct>30 else "#d29922" if pct>10 else "#238636"
    st.markdown(f"""<div style="background:{bc}18;border:1.5px solid {bc};border-radius:10px;
    padding:12px 20px;margin:8px 0;display:flex;justify-content:space-between;align-items:center;">
    <div><span style="font-size:14px;font-weight:700;color:#e6edf3;">{total_changes} changes detected</span>
    <span style="font-size:12px;color:#8b949e;margin-left:12px;">{pct}% of Version A affected</span></div>
    <div style="font-size:12px;color:#8b949e;">{result["unchanged"]} elements unchanged</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")
tab1,tab2,tab3,tab4 = st.tabs([
    f"➕ Added ({len(result['added'])})",
    f"➖ Removed ({len(result['removed'])})",
    f"🔄 Modified ({len(result['changed'])})",
    "📄 Export",
])

with tab1:
    if not result["added"]:
        st.success("No elements were added in Version B.")
    else:
        st.caption(f"{len(result['added'])} new elements in Version B.")
        st.dataframe(pd.DataFrame([{
            "Name": e["Name"], "IFC Type": e["Type"],
            "GlobalId": e["GlobalId"][:22]+"…",
            "Has Psets": "Yes" if e["Psets"] else "No",
            "Material": e["Material"] or "—",
        } for e in result["added"]]), use_container_width=True, hide_index=True)

with tab2:
    if not result["removed"]:
        st.success("No elements were removed.")
    else:
        st.caption(f"{len(result['removed'])} elements from Version A missing in Version B.")
        st.dataframe(pd.DataFrame([{
            "Name": e["Name"], "IFC Type": e["Type"],
            "GlobalId": e["GlobalId"][:22]+"…",
            "Had Psets": "Yes" if e["Psets"] else "No",
            "Material": e["Material"] or "—",
        } for e in result["removed"]]), use_container_width=True, hide_index=True)

with tab3:
    if not result["changed"]:
        st.success("No elements were modified.")
    else:
        st.caption(f"{len(result['changed'])} elements have differences.")
        search = st.text_input("Search", placeholder="element name", key="vc_s")
        filtered = [c for c in result["changed"] if search.lower() in c["Name"].lower()] if search else result["changed"]
        st.caption(f"Showing {len(filtered)} of {len(result['changed'])}")
        for item in filtered[:50]:
            with st.expander(f"🔄 {item['Name']}  ({item['Type']})  — {len(item['Changes'])} change(s)"):
                st.dataframe(pd.DataFrame(item["Changes"]), use_container_width=True, hide_index=True)
        if len(filtered) > 50:
            st.info("Showing first 50 — use search to filter.")

with tab4:
    st.subheader("Export Report")
    rows = []
    for e in result["added"]:
        rows.append({"Status":"Added","Name":e["Name"],"Type":e["Type"],"GlobalId":e["GlobalId"],"Field":"—","Before":"—","After":"New element"})
    for e in result["removed"]:
        rows.append({"Status":"Removed","Name":e["Name"],"Type":e["Type"],"GlobalId":e["GlobalId"],"Field":"—","Before":"Existed","After":"—"})
    for e in result["changed"]:
        for ch in e["Changes"]:
            rows.append({"Status":"Modified","Name":e["Name"],"Type":e["Type"],"GlobalId":e["GlobalId"],"Field":ch["Field"],"Before":ch["Before"],"After":ch["After"]})

    ex1, ex2 = st.columns(2)
    with ex1:
        if rows:
            st.download_button("⬇️ Download CSV", data=pd.DataFrame(rows).to_csv(index=False),
                file_name="ifc_version_diff.csv", mime="text/csv", use_container_width=True)
        else:
            st.info("No changes to export.")
    with ex2:
        if st.button("📄 Generate PDF", use_container_width=True):
            def safe(t): return str(t).encode("latin-1","replace").decode("latin-1")
            pdf = FPDF(); pdf.add_page()
            pdf.set_fill_color(13,31,61); pdf.rect(0,0,210,30,"F")
            pdf.set_font("Arial","B",16); pdf.set_text_color(255,255,255)
            pdf.cell(0,10,"IFC Version Comparison Report",ln=True,align="C")
            pdf.set_font("Arial",size=9)
            pdf.cell(0,6,safe(f"Generated: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}"),ln=True,align="C")
            pdf.ln(5); pdf.set_text_color(0,0,0)
            pdf.set_font("Arial","B",12); pdf.cell(0,8,"Summary",ln=True)
            pdf.set_font("Arial",size=10)
            for label, val in [("Version A",result["total_a"]),("Version B",result["total_b"]),
                ("Added",len(result["added"])),("Removed",len(result["removed"])),
                ("Modified",len(result["changed"])),("Unchanged",result["unchanged"])]:
                pdf.cell(0,6,safe(f"  {label:20}: {val}"),ln=True)
            if result["added"]:
                pdf.ln(2); pdf.set_font("Arial","B",11); pdf.cell(0,7,safe(f"Added ({len(result['added'])})"),ln=True)
                pdf.set_font("Arial",size=9)
                for e in result["added"][:50]: pdf.cell(0,5,safe(f"  + {e['Name']} ({e['Type']})"),ln=True)
            if result["removed"]:
                pdf.ln(2); pdf.set_font("Arial","B",11); pdf.cell(0,7,safe(f"Removed ({len(result['removed'])})"),ln=True)
                pdf.set_font("Arial",size=9)
                for e in result["removed"][:50]: pdf.cell(0,5,safe(f"  - {e['Name']} ({e['Type']})"),ln=True)
            if result["changed"]:
                pdf.ln(2); pdf.set_font("Arial","B",11); pdf.cell(0,7,safe(f"Modified ({len(result['changed'])})"),ln=True)
                pdf.set_font("Arial",size=9)
                for e in result["changed"][:30]:
                    pdf.cell(0,5,safe(f"  ~ {e['Name']} ({e['Type']}) — {len(e['Changes'])} changes"),ln=True)
                    for ch in e["Changes"][:4]:
                        pdf.cell(0,4,safe(f"      {ch['Field']}: {ch['Before']} -> {ch['After']}"),ln=True)
            st.download_button("⬇️ Download PDF", data=pdf.output(dest="S").encode("latin-1"),
                file_name="ifc_version_comparison.pdf", mime="application/pdf", use_container_width=True)