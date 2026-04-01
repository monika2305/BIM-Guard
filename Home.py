import streamlit as st
import ifcopenshell
import pandas as pd
from fpdf import FPDF
import json
import datetime

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BIMGuard",
    page_icon="🛡️",
    layout="wide",
)

# ── Session state ──────────────────────────────────────────────────────────────
if "logged_in"    not in st.session_state: st.session_state.logged_in    = False
if "user_context" not in st.session_state: st.session_state.user_context = {}
if "model_loaded" not in st.session_state: st.session_state.model_loaded = False
if "analysis"     not in st.session_state: st.session_state.analysis     = {}
if "last_file_id" not in st.session_state: st.session_state.last_file_id = None

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
[data-testid="stTabs"] [data-baseweb="tab-list"] { background-color: #161b22 !important; border-bottom: 2px solid #30363d !important; }
[data-testid="stTabs"] [data-baseweb="tab"] { background-color: #0d1117 !important; color: #8b949e !important; }
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] { color: #58a6ff !important; border-bottom: 2px solid #58a6ff !important; }
h1,h2,h3,h4,h5,h6,p,span,label { color: #e6edf3 !important; }
[data-testid="stCaptionContainer"] p, .stCaption, small { color: #8b949e !important; }
hr { border: none !important; border-top: 1px solid #30363d !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    st.title("🛡️ BIMGuard: IFC Integrity Platform")
    st.markdown("---")
    st.subheader("Login")
    st.caption("Please fill in all fields to continue.")

    name   = st.text_input("Your Name *", placeholder="e.g. Moni")
    role   = st.selectbox("Your Role *", [
        "— Select —", "Architect", "Structural Engineer",
        "BIM Manager", "Contractor", "Facility Manager", "Student / Researcher"
    ])
    domain = st.selectbox("Project Domain *", [
        "— Select —", "Architecture", "Structural",
        "MEP", "Infrastructure", "Facility Management"
    ])
    purpose = st.selectbox("Purpose of IFC *", [
        "— Select —", "Design coordination", "Compliance",
        "Construction", "Handover / FM", "Academic / Research"
    ])

    # Check completeness live
    _name_ok    = bool(name.strip())
    _role_ok    = role    != "— Select —"
    _domain_ok  = domain  != "— Select —"
    _purpose_ok = purpose != "— Select —"
    _all_ok     = _name_ok and _role_ok and _domain_ok and _purpose_ok

    # Show what is still missing
    _missing = []
    if not _name_ok:    _missing.append("Name")
    if not _role_ok:    _missing.append("Role")
    if not _domain_ok:  _missing.append("Project Domain")
    if not _purpose_ok: _missing.append("Purpose of IFC")

    if _missing:
        st.warning(f"⚠️ Please fill in: **{', '.join(_missing)}**")

    if st.button("Continue →", disabled=not _all_ok, type="primary", use_container_width=True):
        if _all_ok:
            st.session_state.user_context = {
                "name": name.strip(), "role": role,
                "domain": domain, "purpose": purpose
            }
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Please fill in all required fields.")

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
context = st.session_state.user_context

st.title("🛡️ BIMGuard: IFC Integrity Platform")
c1, c2, c3 = st.columns(3)
c1.write(f"**Role:** {context['role']}")
c2.write(f"**Domain:** {context['domain']}")
c3.write(f"**Purpose:** {context['purpose']}")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗂️ Dashboards")
    st.markdown(
        "After uploading your IFC file, visit the dedicated pages:\n\n"
        "- **🔎 Proxy Classification** — valid / invalid / unknown\n"
        "- **📦 Pset Analysis** — property set completeness\n"
        "- **🧊 3D BIM Viewer** — interactive 3D model\n"
        "- **🔥 Issue Heatmap** — 2D floor plan density map\n"
        "- **🏢 Storey Quality Score** — floor-wise BIM scores\n"
        "- **📏 Rule Validation** — 17+ BIM compliance rules\n"
        "- **🏛️ NBC 2016 Compliance** — Indian building code\n"
        "- **🛠️ Correction Suggestions** — step-by-step fix guide\n"
        "- **📊 Model Score** — overall quality score\n"
        "- **🔀 Version Comparison** — compare IFC versions\n"
        "- **📋 BCF Generator** — export issues as BCF 2.1"
    )
    st.markdown("---")
    if st.session_state.model_loaded:
        st.success("✅ Model loaded — dashboards ready")
    else:
        st.info("Upload an IFC file to enable dashboards")

# ── File upload ────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload IFC file",
    type=["ifc"],
    help="Supports files up to 800 MB. Large files may take 60–120 seconds to process."
)

# ── On fresh upload: parse IFC and store ALL results in session_state ──────────
# Detect new file by comparing file id — forces re-analysis on every new upload
if uploaded_file:
    current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if current_file_id != st.session_state.last_file_id:
        st.session_state.model_loaded = False   # force re-analysis
        st.session_state.last_file_id = current_file_id
        st.session_state.analysis     = {}

if uploaded_file and not st.session_state.model_loaded:
    pass  # processed below

if uploaded_file:
    file_size_mb = uploaded_file.size / (1024 * 1024)

    # ── Size warning ──────────────────────────────────────────────────────────
    if file_size_mb > 400:
        st.info(f"📦 Large file detected ({file_size_mb:.1f} MB) — using optimised streaming parser. Please wait...")
    elif file_size_mb > 100:
        st.info(f"📂 File size: {file_size_mb:.1f} MB — processing with chunked writer.")

    prog_bar = st.progress(0, text=f"📥 Receiving {file_size_mb:.1f} MB...")

    # ── Stream directly to disk — never loads full file into RAM ──────────────
    CHUNK = 16 * 1024 * 1024  # 16 MB chunks
    bytes_written = 0
    total_bytes   = uploaded_file.size

    with open("temp.ifc", "wb") as f:
        # getbuffer() gives a memoryview — slice without copying
        buf = uploaded_file.getbuffer()
        for i in range(0, total_bytes, CHUNK):
            f.write(buf[i : i + CHUNK])
            bytes_written = min(i + CHUNK, total_bytes)
            pct = int(bytes_written / total_bytes * 35)
            mb_done = bytes_written / (1024 * 1024)
            prog_bar.progress(pct, text=f"📥 Writing {mb_done:.0f} / {file_size_mb:.0f} MB...")
        del buf   # free memoryview immediately

    prog_bar.progress(38, text="🔍 Opening IFC model (streaming parser)...")

    # ── Open with ifcopenshell — it reads from disk, not RAM ──────────────────
    import gc
    gc.collect()   # free any leftover memory before parsing
    model = ifcopenshell.open("temp.ifc")

    prog_bar.progress(40, text="🔍 Detecting IFC export source...")

    # ── Export Source Risk Prediction ─────────────────────────────────────────
    def detect_export_source(ifc_model):
        """Read IFC header metadata to identify the exporting software."""
        try:
            header = ifc_model.header
            desc   = str(getattr(header, "file_description", "")).lower()
            name   = str(getattr(header, "file_name",        "")).lower()
            schema = str(getattr(header, "file_schema",      "")).upper()

            combined = desc + " " + name

            if any(k in combined for k in ["revit", "autodesk"]):
                tool = "Autodesk Revit"
                risks = [
                    ("⚠️ RPC trees/furniture export as IfcBuildingElementProxy",   "High"),
                    ("⚠️ FireRating property often missing in Pset_WallCommon",     "High"),
                    ("⚠️ Material classification may be lost during export",        "Medium"),
                    ("⚠️ Some custom Psets may not transfer correctly",             "Medium"),
                    ("⚠️ IfcWallStandardCase may appear instead of IfcWall",        "Low"),
                ]
            elif any(k in combined for k in ["archicad", "graphisoft"]):
                tool = "Graphisoft ArchiCAD"
                risks = [
                    ("⚠️ Morph elements may export as generic proxies",            "High"),
                    ("⚠️ Complex roof shapes may lose semantic type",              "High"),
                    ("⚠️ Object-level Psets may be partially mapped",             "Medium"),
                    ("⚠️ Stair components may lose sub-element classification",   "Low"),
                ]
            elif any(k in combined for k in ["tekla", "trimble"]):
                tool = "Tekla Structures"
                risks = [
                    ("⚠️ Custom component assemblies may become proxy objects",    "High"),
                    ("⚠️ Rebar and reinforcement data may not transfer",          "High"),
                    ("⚠️ Steel connection details may lose classification",        "Medium"),
                ]
            elif any(k in combined for k in ["navisworks", "navis"]):
                tool = "Autodesk Navisworks"
                risks = [
                    ("⚠️ Navisworks re-export often strips all Pset data",        "Critical"),
                    ("⚠️ Nearly all elements may become IfcBuildingElementProxy", "Critical"),
                    ("⚠️ GlobalIds may be regenerated — losing element tracking", "High"),
                ]
            elif any(k in combined for k in ["vectorworks"]):
                tool = "Vectorworks"
                risks = [
                    ("⚠️ Space objects may not export correctly",                 "Medium"),
                    ("⚠️ Some parametric objects may lose type information",      "Medium"),
                ]
            elif any(k in combined for k in ["sketchup", "sketch up"]):
                tool = "SketchUp"
                risks = [
                    ("⚠️ Most elements export as generic proxies",               "Critical"),
                    ("⚠️ No Pset data exported by default",                      "Critical"),
                    ("⚠️ No floor/storey assignment preserved",                  "High"),
                ]
            elif any(k in combined for k in ["allplan"]):
                tool = "Nemetschek Allplan"
                risks = [
                    ("⚠️ Reinforcement elements may lose classification",         "Medium"),
                    ("⚠️ Some Psets may use non-standard names",                  "Low"),
                ]
            else:
                tool = "Unknown / Generic IFC Exporter"
                risks = [
                    ("ℹ️ Export source not detected from header metadata",        "Info"),
                    ("ℹ️ Run full validation to identify actual issues",          "Info"),
                ]

            # Extract IFC schema version
            ifc_version = "Unknown"
            if "IFC4" in schema:   ifc_version = "IFC4"
            elif "IFC2X3" in schema: ifc_version = "IFC2X3 (Legacy)"
            elif "IFC2" in schema:   ifc_version = "IFC2.x (Old)"

            return tool, ifc_version, risks
        except Exception:
            return "Unknown", "Unknown", [("ℹ️ Could not read IFC header metadata", "Info")]

    export_tool, ifc_version, export_risks = detect_export_source(model)
    st.session_state["export_source"] = {
        "tool":    export_tool,
        "version": ifc_version,
        "risks":   export_risks,
    }

    prog_bar.progress(42, text="📊 Scanning elements (optimised for large files)...")

    # ── Single pass — collect everything at once ──────────────────────────────
    # Use frozenset for O(1) lookup — critical for 500 MB files with 50k+ elements
    SKIP_TYPES = frozenset({
        "IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
        "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject",
        "IfcRelAggregates","IfcZone","IfcSpatialZone","IfcRelContainedInSpatialStructure",
    })
    walls          = []
    standard_walls = []
    doors          = []
    windows        = []
    proxies        = []
    all_elements   = []

    # Count total for progress
    all_products = model.by_type("IfcProduct")
    total_products = len(all_products)
    UPDATE_EVERY = max(1, total_products // 20)   # update bar every 5%

    for idx, elem in enumerate(all_products):
        t = elem.is_a()
        if t in SKIP_TYPES:
            continue
        all_elements.append(elem)
        if   t == "IfcWall":                    walls.append(elem)
        elif t == "IfcWallStandardCase":        standard_walls.append(elem)
        elif t == "IfcDoor":                    doors.append(elem)
        elif t == "IfcWindow":                  windows.append(elem)
        elif t == "IfcBuildingElementProxy":    proxies.append(elem)

        # Update progress bar every 5% to avoid UI overhead
        if idx % UPDATE_EVERY == 0:
            pct = 42 + int(idx / total_products * 25)
            prog_bar.progress(pct, text=f"📊 Scanning elements... {idx:,} / {total_products:,}")

    del all_products   # free list reference

    total_elements    = len(all_elements)
    total_walls       = len(walls) + len(standard_walls)
    proxy_elements    = len(proxies)
    # Semantic = ALL typed elements that are NOT proxy
    # This means after reclassification, score improves correctly
    semantic_elements = total_elements - proxy_elements
    other_semantic    = max(semantic_elements - total_walls - len(doors) - len(windows), 0)
    # Each category is a separate slice — all must add to 100%
    # Walls + Doors + Windows + Proxy + Other = Total  →  sum = 100%
    walls_pct  = (total_walls          / total_elements) * 100 if total_elements else 0
    doors_pct  = (len(doors)           / total_elements) * 100 if total_elements else 0
    windows_pct= (len(windows)         / total_elements) * 100 if total_elements else 0
    proxy_pct  = (proxy_elements       / total_elements) * 100 if total_elements else 0
    other_pct  = (other_semantic       / total_elements) * 100 if total_elements else 0
    # semantic_pct = everything except proxy (used for score formula)
    semantic_pct = 100 - proxy_pct if total_elements else 0

    if proxy_pct <= 10:  severity = "LOW"
    elif proxy_pct < 20: severity = "MEDIUM"
    elif proxy_pct < 50: severity = "HIGH"
    else:                severity = "CRITICAL"

    # ── Model Quality Score (0–100) ────────────────────────────────────────────
    prog_bar.progress(68, text="📋 Checking property sets...")

    # Check Psets for ALL element types — not just walls
    # Any IfcPropertySet counts — covers Wall, Door, Pipe, Light etc.
    STANDARD_PSETS = {
        "Pset_WallCommon", "Pset_DoorCommon", "Pset_WindowCommon",
        "Pset_SlabCommon", "Pset_ColumnCommon", "Pset_BeamCommon",
        "Pset_RoofCommon", "Pset_StairCommon", "Pset_RailingCommon",
        "Pset_PipeSegmentTypeCommon", "Pset_PipeFittingTypeCommon",
        "Pset_FlowSegmentTypeCommon", "Pset_FlowTerminalTypeCommon",
        "Pset_LightFixtureTypeCommon", "Pset_ElectricalDeviceCommon",
        "Pset_EnergyConversionDeviceCommon", "Pset_ManufacturerTypeInformation",
        "Pset_DistributionSystemCommon", "Pset_PlantCommon",
        "Pset_BuildingElementCommon",
    }

    _total_walls_q   = len(walls) + len(standard_walls)

    # ── Pset requirement map — every type that should have a Pset ────────────
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

    _walls_with_pset = 0
    walls_missing_pset_set = set()
    missing_pset_all = []   # all elements missing their required pset

    # Count walls missing Pset_WallCommon (backward compat)
    for _w in walls:
        _has = False
        for _d in getattr(_w, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcPropertySet") and _ps.Name == "Pset_WallCommon":
                    _has = True; break
        if _has:
            _walls_with_pset += 1
        else:
            walls_missing_pset_set.add(_w.GlobalId)

    # Check ALL elements for their required Pset
    _elems_with_pset = 0
    for _elem in all_elements:
        _etype    = _elem.is_a()
        _req_pset = ELEM_PSET_MAP.get(_etype)
        _has_any  = False
        _has_req  = False
        for _d in getattr(_elem, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcPropertySet"):
                    _has_any = True
                    if _req_pset and _ps.Name == _req_pset:
                        _has_req = True; break
        if _req_pset:
            if _has_req:
                _elems_with_pset += 1
            else:
                missing_pset_all.append({
                    "Element Name": _elem.Name or "Unnamed",
                    "GlobalId":     _elem.GlobalId,
                    "IFC Type":     _etype,
                    "Required Pset":_req_pset,
                    "Issue":        f"Missing {_req_pset}",
                })
        else:
            # Type has no standard pset requirement — count as ok
            _elems_with_pset += 1



    # Score uses pset coverage among elements that REQUIRE a pset
    _elems_requiring_pset = _elems_with_pset + len(missing_pset_all)
    _pset_score  = (_elems_with_pset / _elems_requiring_pset * 40) if _elems_requiring_pset else 40
    _pset_pct    = round(_elems_with_pset / _elems_requiring_pset * 100, 1) if _elems_requiring_pset else 100
    # Note: _sem_score, _proxy_score, quality_score calculated after 4-level detection below

    # ── 4-Level Data Loss Detection ──────────────────────────────────────────
    prog_bar.progress(75, text="🔗 Checking relationships and geometry...")

    # Level 1 — Type Loss (proxy)
    _type_loss_count  = proxy_elements
    _type_loss_pct    = round(proxy_pct, 1)

    # Level 2 — Property Loss (missing psets)
    _prop_loss_count  = len(missing_pset_all)
    _prop_loss_pct    = round(_prop_loss_count / _elems_requiring_pset * 100, 1) if _elems_requiring_pset else 0

    # Level 3 — Relationship Loss
    _rel_loss = []
    for _elem in all_elements:
        _etype = _elem.is_a()
        if _etype in ("IfcBuildingElementProxy",): continue
        # Check storey assignment
        _in_storey = any(
            r.is_a("IfcRelContainedInSpatialStructure") and
            getattr(r, "RelatingStructure", None) and
            r.RelatingStructure.is_a("IfcBuildingStorey")
            for r in getattr(_elem, "ContainedInStructure", [])
        )
        if not _in_storey:
            _rel_loss.append({"Name": _elem.Name or "Unnamed", "GlobalId": _elem.GlobalId,
                               "IFC Type": _etype, "Issue": "Not assigned to any storey"})
        # Check door/window hosted in wall
        if _etype in ("IfcDoor", "IfcWindow"):
            _hosted = any(r.is_a("IfcRelFillsElement")
                          for r in getattr(_elem, "FillsVoids", []))
            if not _hosted:
                _rel_loss.append({"Name": _elem.Name or "Unnamed", "GlobalId": _elem.GlobalId,
                                   "IFC Type": _etype, "Issue": "Not hosted in any wall opening"})
    _rel_loss_count = len(_rel_loss)
    _rel_loss_pct   = round(_rel_loss_count / max(total_elements, 1) * 100, 1)

    # Level 4 — Geometry Loss
    _geo_loss = []
    for _elem in all_elements:
        if not getattr(_elem, "Representation", None):
            _geo_loss.append({"Name": _elem.Name or "Unnamed", "GlobalId": _elem.GlobalId,
                               "IFC Type": _elem.is_a(), "Issue": "No geometry representation"})
    _geo_loss_count = len(_geo_loss)
    _geo_loss_pct   = round(_geo_loss_count / max(total_elements, 1) * 100, 1)

    # Level 5 — Quantity Loss (missing IfcElementQuantity / BaseQuantities)
    _qty_loss = []
    QTY_TYPES = {"IfcWall","IfcWallStandardCase","IfcSlab","IfcColumn","IfcBeam",
                 "IfcRoof","IfcDoor","IfcWindow","IfcStair"}
    for _elem in all_elements:
        _etype = _elem.is_a()
        if _etype not in QTY_TYPES:
            continue
        _has_qty = False
        for _d in getattr(_elem, "IsDefinedBy", []):
            if _d.is_a("IfcRelDefinesByProperties"):
                _ps = _d.RelatingPropertyDefinition
                if _ps and _ps.is_a("IfcElementQuantity"):
                    _has_qty = True; break
        if not _has_qty:
            _qty_loss.append({
                "Name":     _elem.Name or "Unnamed",
                "GlobalId": _elem.GlobalId,
                "IFC Type": _etype,
                "Issue":    "Missing IfcElementQuantity (no area/volume/length data)",
            })
    _qty_loss_count = len(_qty_loss)
    _qty_loss_pct   = round(_qty_loss_count / max(total_elements, 1) * 100, 1)

    # Relationship summary for dashboard + PDF report
    _relationship_catalog = [
        ("IfcRelContainedInSpatialStructure", "Element -> Storey assignment"),
        ("IfcRelDefinesByProperties",         "Element -> Property Sets (Psets)"),
        ("IfcRelAssociatesMaterial",          "Element -> Material"),
        ("IfcRelConnectsElements",            "Element <-> Element connection"),
        ("IfcRelFillsElement",                "Door/Window -> Wall opening"),
        ("IfcRelAggregates",                  "Element -> Parent assembly"),
        ("IfcRelAssociatesClassification",    "Element -> Classification system"),
    ]
    _relationship_summary = []
    for _rel_type, _meaning in _relationship_catalog:
        try:
            _count = len(model.by_type(_rel_type))
        except Exception:
            _count = 0
        if _count > 0:
            _relationship_summary.append({
                "Relationship": _rel_type,
                "Meaning": _meaning,
                "Count": _count,
            })

    # ── Weighted 5-level data loss score (new formula) ──────────────────────
    # Total Loss % = (0.30 × Semantic) + (0.20 × Property) + (0.15 × Quantity)
    #              + (0.25 × Relationship) + (0.10 × Geometry)
    _data_loss_score = round(
        (_type_loss_pct  / 100) * 30 +
        (_prop_loss_pct  / 100) * 20 +
        (_qty_loss_pct   / 100) * 15 +
        (_rel_loss_pct   / 100) * 25 +
        (_geo_loss_pct   / 100) * 10,
    1)
    _data_integrity = round(100 - _data_loss_score, 1)

    # ── Quality score (calculated BEFORE score_breakdown) ────────────────────
    _sem_score   = semantic_pct / 100 * 60
    _proxy_score = (proxy_pct / 100) * 30
    quality_score = round(min(100, max(0, _sem_score - _proxy_score + _pset_score)), 1)
    if   quality_score >= 85: quality_grade, quality_color = "Excellent", "#238636"
    elif quality_score >= 70: quality_grade, quality_color = "Good",      "#58a6ff"
    elif quality_score >= 50: quality_grade, quality_color = "Fair",      "#3ab8d9"
    else:                     quality_grade, quality_color = "Poor",      "#ff7070"
    if   proxy_pct <= 10: severity = "LOW"
    elif proxy_pct < 20:  severity = "MEDIUM"
    elif proxy_pct < 50:  severity = "HIGH"
    else:                 severity = "CRITICAL"

    _score_breakdown = {
        "sem_score":      round(_sem_score, 1),
        "proxy_score":    round(_proxy_score, 1),
        "pset_score":     round(_pset_score, 1),
        "sem_pct":        round(semantic_pct, 1),
        "proxy_pct":      round(proxy_pct, 1),
        "pset_pct":       _pset_pct,
        "elems_requiring_pset": _elems_requiring_pset,
        "walls_total":    _total_walls_q,
        "walls_with_pset":_walls_with_pset,
        "elems_with_pset":_elems_with_pset,
    }
    if   quality_score >= 85: quality_grade, quality_color = "Excellent", "#238636"
    elif quality_score >= 70: quality_grade, quality_color = "Good",      "#58a6ff"
    elif quality_score >= 50: quality_grade, quality_color = "Fair",      "#3ab8d9"
    else:                     quality_grade, quality_color = "Poor",      "#ff7070"

    prog_bar.progress(85, text="🧮 Building analysis data...")
    # walls_missing_pset already computed above in single pass
    walls_missing_pset = [w for w in walls if w.GlobalId in walls_missing_pset_set]
    # missing_pset_all already built in pset loop above

    # Store everything — persists across page switches
    prog_bar.progress(98, text="✅ Almost done...")
    st.session_state.model_loaded = True
    st.session_state.analysis = {
        "total_elements":    total_elements,
        "total_walls":       total_walls,
        "doors":             len(doors),
        "windows":           len(windows),
        "proxy_elements":    proxy_elements,
        "other_semantic":    other_semantic,
        "semantic_elements": semantic_elements,
        "semantic_pct":      semantic_pct,
        "proxy_pct":         proxy_pct,
        "other_pct":         other_pct,
        "walls_pct":         walls_pct,
        "doors_pct":         doors_pct,
        "windows_pct":       windows_pct,
        "severity":          severity,
        "quality_score":     quality_score,
        "quality_grade":     quality_grade,
        "quality_color":     quality_color,
        "score_breakdown":   _score_breakdown,
        # Cap at 500 entries for large models — show count always
        "proxy_list": [{
            "Name":     p.Name or "Unnamed",
            "GlobalId": p.GlobalId,
            "IFC Type": p.is_a(),
            "Issue":    "Semantic meaning lost (generic proxy)",
        } for p in proxies[:500]],
        "proxy_list_total":   len(proxies),
        "missing_pset_list":     missing_pset_all[:500],
        "missing_pset_count":    len(missing_pset_all),
        "rel_loss_list":         _rel_loss[:500],
        "rel_loss_count":        _rel_loss_count,
        "rel_loss_pct":          _rel_loss_pct,
        "geo_loss_list":         _geo_loss[:500],
        "geo_loss_count":        _geo_loss_count,
        "geo_loss_pct":          _geo_loss_pct,
        "qty_loss_list":         _qty_loss[:500],
        "qty_loss_count":        _qty_loss_count,
        "qty_loss_pct":          _qty_loss_pct,
        "type_loss_count":       _type_loss_count,
        "prop_loss_count":       _prop_loss_count,
        "prop_loss_pct":         _prop_loss_pct,
        "rel_loss_count":        _rel_loss_count,
        "rel_loss_pct":          _rel_loss_pct,
        "geo_loss_count":        _geo_loss_count,
        "geo_loss_pct":          _geo_loss_pct,
        "data_loss_score":       _data_loss_score,
        "data_integrity":        _data_integrity,
        "relationship_summary":  _relationship_summary,
        "type_loss_pct":         _type_loss_pct,
        "prop_loss_count":       _prop_loss_count,
        "prop_loss_pct":         _prop_loss_pct,
        "walls_missing_pset":    [{"Wall Name": w.Name or "Unnamed",
                                   "GlobalId": w.GlobalId,
                                   "Issue": "Pset_WallCommon missing"}
                                   for w in walls_missing_pset[:500]],
    }
    prog_bar.progress(100, text=f"✅ Done! {total_elements} elements loaded from {file_size_mb:.1f} MB file.")
    st.success(f"✅ IFC file analysed — {total_elements} elements, {proxy_elements} proxies")

# ══════════════════════════════════════════════════════════════════════════════
# RENDER ANALYSIS
# Reads from session_state → works on fresh upload AND when returning from
# another page (3D Viewer / Heatmap) without re-uploading the file.
# ══════════════════════════════════════════════════════════════════════════════
an = st.session_state.analysis

if an:
    # ── Export Source Risk Prediction (shown FIRST) ───────────────────────────
    src = st.session_state.get("export_source", {})
    if src:
        st.markdown("---")
        st.subheader("🔍 IFC Export Source Analysis")
        tool    = src.get("tool", "Unknown")
        version = src.get("version", "Unknown")
        risks   = src.get("risks", [])

        sev_color = {"Critical":"#ff7070","High":"#3ab8d9","Medium":"#58a6ff","Low":"#238636","Info":"#8b949e"}

        tc1, tc2 = st.columns([1, 2])
        with tc1:
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:16px;">
  <div style="font-size:11px;color:#8b949e;letter-spacing:1px;margin-bottom:8px;">EXPORT TOOL DETECTED</div>
  <div style="font-size:16px;font-weight:800;color:#f0f4f8;margin-bottom:8px;">🏗️ {tool}</div>
  <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">IFC Schema Version</div>
  <div style="font-size:13px;font-weight:700;color:#58a6ff;">{version}</div>
</div>""", unsafe_allow_html=True)

        with tc2:
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:16px;">
  <div style="font-size:11px;color:#8b949e;letter-spacing:1px;margin-bottom:10px;">PREDICTED SEMANTIC LOSS RISKS</div>
""" + "".join([
    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">'
    f'<span style="background:{sev_color.get(sev,"#8b949e")}22;color:{sev_color.get(sev,"#8b949e")};'
    f'border:1px solid {sev_color.get(sev,"#8b949e")};border-radius:4px;padding:1px 7px;'
    f'font-size:10px;font-weight:700;flex-shrink:0;">{sev}</span>'
    f'<span style="font-size:12px;color:#f0f4f8;">{risk}</span></div>'
    for risk, sev in risks
]) + "</div>", unsafe_allow_html=True)

        # Prediction vs Reality
        actual_issues = an.get("proxy_elements", 0) + an.get("missing_pset_count", 0)
        high_risk_count = sum(1 for _, sev in risks if sev in ("Critical","High"))
        match_color = "#238636" if high_risk_count > 0 and actual_issues > 0 else "#8b949e"
        st.markdown(f"""
<div style="background:{match_color}18;border:1px solid {match_color};border-radius:8px;
padding:10px 16px;margin-top:8px;display:flex;gap:24px;flex-wrap:wrap;">
  <div><span style="color:#8b949e;font-size:11px;">PREDICTED RISKS</span><br>
  <strong style="color:{match_color};font-size:16px;">{high_risk_count} High/Critical</strong></div>
  <div><span style="color:#8b949e;font-size:11px;">ACTUAL ISSUES DETECTED</span><br>
  <strong style="color:{match_color};font-size:16px;">{actual_issues} Issues Found</strong></div>
  <div style="flex:1;min-width:180px;"><span style="color:#8b949e;font-size:11px;">VERDICT</span><br>
  <strong style="color:{match_color};font-size:13px;">
  {"✅ Prediction confirmed — issues match known risks for " + tool
   if high_risk_count > 0 and actual_issues > 0
   else "✅ Model is cleaner than typical " + tool + " exports"
   if actual_issues == 0
   else "ℹ️ Issues detected — check validation results"}</strong></div>
</div>""", unsafe_allow_html=True)

    # ── Summary metrics — 3 clean cards ────────────────────────────────────────
    st.markdown("---")
    st.header("📊 Summary Metrics")

    # Always use original upload data — corrections do not update Summary Metrics
    total_e   = an["total_elements"]
    sem_count = an["semantic_elements"]
    prx_count = an["proxy_elements"]
    prx_pct   = an["proxy_pct"]
    sem_pct   = round(sem_count / total_e * 100, 1) if total_e else 0

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("📦 Total Elements",   total_e,
               help="All IfcProduct entities excluding spaces, openings and annotations")
    mc2.metric("✅ Semantic",         f"{sem_count}  ({sem_pct:.1f}%)",
               help="Correctly typed elements — walls, doors, columns, pipes etc. (not proxy)")
    mc3.metric("🔴 Proxy",            f"{prx_count}  ({prx_pct:.1f}%)",
               help="IfcBuildingElementProxy — lost semantic type during export")

    # ── STEP Syntax Validation ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔎 STEP Syntax Validation")
    st.caption("Verifies that the IFC file is a structurally valid STEP/P21 file at the parsing level.")

    # Always validate the original upload — corrections are not reflected here
    _step_model_label = "original upload"
    try:
        _step_model = ifcopenshell.open("temp.ifc")
    except Exception:
        _step_model = None
        _step_model_label = "unavailable (original model could not be read)"

    # Run validation checks against the chosen model
    _step_checks = []

    # Check 1 — File parseable
    if _step_model is not None:
        _step_checks.append({
            "check":   "File Parseable",
            "status":  "pass",
            "detail":  f"ifcopenshell opened the {_step_model_label} without errors — STEP/P21 syntax is valid.",
        })
    else:
        _step_checks.append({
            "check":   "File Parseable",
            "status":  "fail",
            "detail":  "Could not open the original IFC model for STEP validation.",
        })

    # Check 2 — Schema version declared
    try:
        _schema = _step_model.schema
        if _schema:
            _step_checks.append({
                "check":  "Schema Version Declared",
                "status": "pass",
                "detail": f"Schema: {_schema}",
            })
        else:
            _step_checks.append({
                "check":  "Schema Version Declared",
                "status": "warn",
                "detail": "Schema string is empty or None in file header.",
            })
    except Exception:
        _step_checks.append({
            "check":  "Schema Version Declared",
            "status": "warn",
            "detail": "Could not read schema from model header.",
        })

    # Check 3 — IfcProject entity present (mandatory root entity)
    try:
        _projects = _step_model.by_type("IfcProject")
        if _projects:
            _proj_name = getattr(_projects[0], "Name", None) or "Unnamed"
            _step_checks.append({
                "check":  "IfcProject Entity Present",
                "status": "pass",
                "detail": f"Found IfcProject: '{_proj_name}'",
            })
        else:
            _step_checks.append({
                "check":  "IfcProject Entity Present",
                "status": "fail",
                "detail": "No IfcProject entity found — file may be a partial/fragment export.",
            })
    except Exception as _e:
        _step_checks.append({
            "check":  "IfcProject Entity Present",
            "status": "fail",
            "detail": f"Error checking IfcProject: {_e}",
        })

    # Check 4 — OwnerHistory present (traceability)
    try:
        _oh = _step_model.by_type("IfcOwnerHistory")
        if _oh:
            _step_checks.append({
                "check":  "OwnerHistory Present",
                "status": "pass",
                "detail": f"{len(_oh)} IfcOwnerHistory record(s) — authorship metadata intact.",
            })
        else:
            _step_checks.append({
                "check":  "OwnerHistory Present",
                "status": "warn",
                "detail": "No IfcOwnerHistory found — file traceability is missing.",
            })
    except Exception:
        _step_checks.append({
            "check":  "OwnerHistory Present",
            "status": "warn",
            "detail": "Could not check IfcOwnerHistory.",
        })

    # Check 5 — No duplicate GlobalIds
    try:
        _all_gids = [e.GlobalId for e in _step_model.by_type("IfcRoot") if hasattr(e, "GlobalId")]
        _dup_count = len(_all_gids) - len(set(_all_gids))
        if _dup_count == 0:
            _step_checks.append({
                "check":  "GlobalId Uniqueness",
                "status": "pass",
                "detail": f"All {len(_all_gids)} GlobalIds are unique.",
            })
        else:
            _step_checks.append({
                "check":  "GlobalId Uniqueness",
                "status": "fail",
                "detail": f"{_dup_count} duplicate GlobalId(s) detected — element tracking will be unreliable.",
            })
    except Exception as _e:
        _step_checks.append({
            "check":  "GlobalId Uniqueness",
            "status": "warn",
            "detail": f"Could not verify GlobalIds: {_e}",
        })

    # Check 6 — IfcUnits / unit assignment
    try:
        _units = _step_model.by_type("IfcUnitAssignment")
        if _units:
            _step_checks.append({
                "check":  "Unit Assignment",
                "status": "pass",
                "detail": f"IfcUnitAssignment found with {len(getattr(_units[0], 'Units', []))} unit(s) defined.",
            })
        else:
            _step_checks.append({
                "check":  "Unit Assignment",
                "status": "warn",
                "detail": "No IfcUnitAssignment — unit interpretation (mm/m/ft) is ambiguous.",
            })
    except Exception:
        _step_checks.append({
            "check":  "Unit Assignment",
            "status": "warn",
            "detail": "Could not check IfcUnitAssignment.",
        })

    # Check 7 — At least one geometric representation context
    try:
        _ctx = _step_model.by_type("IfcGeometricRepresentationContext")
        if _ctx:
            _step_checks.append({
                "check":  "Geometry Context",
                "status": "pass",
                "detail": f"{len(_ctx)} IfcGeometricRepresentationContext(s) — coordinate system defined.",
            })
        else:
            _step_checks.append({
                "check":  "Geometry Context",
                "status": "fail",
                "detail": "No IfcGeometricRepresentationContext — all geometry placements may be invalid.",
            })
    except Exception:
        _step_checks.append({
            "check":  "Geometry Context",
            "status": "warn",
            "detail": "Could not check geometry context.",
        })

    # ── Render results ─────────────────────────────────────────────────────────
    _pass  = sum(1 for c in _step_checks if c["status"] == "pass")
    _warn  = sum(1 for c in _step_checks if c["status"] == "warn")
    _fail  = sum(1 for c in _step_checks if c["status"] == "fail")
    _total = len(_step_checks)

    # Overall verdict banner
    if _fail == 0 and _warn == 0:
        _verdict_col, _verdict_icon, _verdict_text = "#238636", "✅", "STEP Valid — All checks passed"
    elif _fail == 0:
        _verdict_col, _verdict_icon, _verdict_text = "#d29922", "⚠️", f"STEP Valid with {_warn} warning(s)"
    else:
        _verdict_col, _verdict_icon, _verdict_text = "#da3633", "❌", f"STEP Issues — {_fail} check(s) failed"

    st.markdown(f"""
<div style="background:{_verdict_col}18;border:2px solid {_verdict_col};border-radius:10px;
padding:12px 20px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
  <div>
    <span style="font-size:18px;font-weight:800;color:{_verdict_col};">{_verdict_icon} {_verdict_text}</span>
    <div style="font-size:12px;color:#8b949e;margin-top:3px;">
      {_pass} passed · {_warn} warnings · {_fail} failed · {_total} checks total
    </div>
  </div>
  <div style="display:flex;gap:16px;">
    <div style="text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#238636;">{_pass}</div>
      <div style="font-size:10px;color:#8b949e;">PASS</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#d29922;">{_warn}</div>
      <div style="font-size:10px;color:#8b949e;">WARN</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:20px;font-weight:800;color:#da3633;">{_fail}</div>
      <div style="font-size:10px;color:#8b949e;">FAIL</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # Per-check rows — inside a dropdown
    _STATUS_CFG = {
        "pass": ("#238636", "✅", "PASS"),
        "warn": ("#d29922", "⚠️", "WARN"),
        "fail": ("#da3633", "❌", "FAIL"),
    }
    _expander_label = f"View {_total} checks — {_pass} passed · {_warn} warnings · {_fail} failed"
    with st.expander(_expander_label, expanded=False):
        for _c in _step_checks:
            _col, _ico, _lbl = _STATUS_CFG[_c["status"]]
            st.markdown(f"""
<div style="background:#161b22;border:1px solid {'#30363d' if _c['status']=='pass' else _col};
border-radius:8px;padding:10px 16px;margin-bottom:6px;
display:flex;align-items:center;gap:14px;">
  <span style="background:{_col}22;color:{_col};border:1px solid {_col};
  border-radius:4px;padding:2px 10px;font-size:11px;font-weight:700;white-space:nowrap;">
    {_ico} {_lbl}
  </span>
  <div style="flex:1;">
    <div style="font-size:13px;font-weight:700;color:#e6edf3;">{_c['check']}</div>
    <div style="font-size:11px;color:#8b949e;margin-top:2px;">{_c['detail']}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── 5-Level Data Loss Dashboard ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔬 5-Level Data Loss Analysis")
    st.caption("Semantic · Property · Quantity · Relationship · Geometry — all 5 levels of IFC data integrity.")

    l1  = an.get("type_loss_pct",   prx_pct)
    l2  = an.get("prop_loss_pct",   0)
    l3  = an.get("qty_loss_pct",    0)
    l4  = an.get("rel_loss_pct",    0)
    l5  = an.get("geo_loss_pct",    0)
    l1c = an.get("type_loss_count", prx_count)
    l2c = an.get("prop_loss_count", an.get("missing_pset_count",0))
    l3c = an.get("qty_loss_count",  0)
    l4c = an.get("rel_loss_count",  0)
    l5c = an.get("geo_loss_count",  0)

    def loss_col(pct):
        if pct == 0:    return "#238636"
        if pct <= 10:   return "#d29922"
        if pct <= 30:   return "#ff7070"
        return "#da3633"

    lc1, lc2, lc3, lc4, lc5 = st.columns(5)
    for col, lvl, label, pct, cnt, sub, weight in [
        (lc1,"L1","Semantic Loss",    l1, l1c, "IfcBuildingElementProxy","30%"),
        (lc2,"L2","Property Loss",    l2, l2c, "Missing Psets",          "20%"),
        (lc3,"L3","Quantity Loss",    l3, l3c, "No area/vol/length",     "15%"),
        (lc4,"L4","Relationship Loss",l4, l4c, "No storey/wall host",    "25%"),
        (lc5,"L5","Geometry Loss",    l5, l5c, "Invisible in viewer",    "10%"),
    ]:
        c = loss_col(pct)
        col.markdown(f"""
<div style="background:#161b22;border:1px solid {c};border-radius:10px;padding:12px;text-align:center;">
  <div style="font-size:9px;color:#8b949e;letter-spacing:1px;margin-bottom:2px;">{lvl} · Weight {weight}</div>
  <div style="font-size:11px;color:#e6edf3;font-weight:700;margin-bottom:6px;">{label}</div>
  <div style="font-size:22px;font-weight:800;color:{c};">{pct:.1f}%</div>
  <div style="font-size:11px;color:#8b949e;">{cnt} elements</div>
  <div style="font-size:10px;color:#8b949e;margin-top:4px;">{sub}</div>
</div>""", unsafe_allow_html=True)

    # ── Total Loss % and Model Score ──────────────────────────────────────────
    _total_loss_pct = round(
        (l1/100)*30 + (l2/100)*20 + (l3/100)*15 + (l4/100)*25 + (l5/100)*10, 1
    )
    _model_score = round(100 - _total_loss_pct * 100 / 100, 1)  # same as 100 - total_loss_pct (already a %)
    _model_score = max(0, min(100, round(100 - _total_loss_pct, 1)))
    _ms_col = "#238636" if _model_score>=85 else "#58a6ff" if _model_score>=70 else "#d29922" if _model_score>=50 else "#da3633"
    _ms_grade = "Excellent" if _model_score>=85 else "Good" if _model_score>=70 else "Fair" if _model_score>=50 else "Poor"

    st.markdown(f"""
<div style="background:#161b22;border:2px solid {_ms_col};border-radius:12px;
padding:16px 24px;margin-top:12px;display:flex;justify-content:space-between;
align-items:center;flex-wrap:wrap;gap:12px;">
  <div>
    <div style="font-size:10px;color:#8b949e;letter-spacing:1px;margin-bottom:4px;">MODEL INTEGRITY SCORE</div>
    <div style="font-size:32px;font-weight:900;color:{_ms_col};">{_model_score}/100 — {_ms_grade}</div>
    <div style="font-size:12px;color:#8b949e;margin-top:4px;">
      Score = 100 − Total Loss% &nbsp;|&nbsp;
      Total Loss = 0.30×Semantic + 0.20×Property + 0.15×Quantity + 0.25×Relationship + 0.10×Geometry
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">Total Loss %</div>
    <div style="font-size:24px;font-weight:800;color:{_ms_col};">{_total_loss_pct}%</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("🧠 Automated Conclusion")
    if an["proxy_pct"] <= 10:
        st.success("The IFC model preserves semantic representation across all analyzed elements. No semantic degradation detected.")
    elif an["proxy_pct"] < 20:
        st.info("The IFC model largely preserves semantic meaning, with minor semantic degradation observed in a small subset of elements.")
    elif an["proxy_pct"] < 50:
        st.warning("The IFC model exhibits mixed semantic representation. Several building components are represented as proxy elements.")
    else:
        st.error("The IFC model shows significant semantic degradation. A large portion of elements are represented as generic proxy objects.")

    # Score moved to dedicated Model Score page
    q_col   = an.get("quality_color", "#8b949e")
    q_score = an.get("quality_score", "—")
    q_grade = an.get("quality_grade", "—")
    st.markdown(f"""
<div style="background:{q_col}18;border:1.5px solid {q_col};border-radius:10px;
padding:12px 20px;display:flex;justify-content:space-between;align-items:center;margin-top:10px;">
  <div>
    <span style="font-size:24px;font-weight:800;color:{q_col};">{q_score}/100</span>
    <span style="font-size:14px;color:{q_col};font-weight:700;margin-left:8px;">{q_grade}</span>
  </div>
  <div style="font-size:12px;color:#8b949e;">See full score breakdown in <strong style="color:{q_col};">📊 Model Score</strong> page</div>
</div>""", unsafe_allow_html=True)

    # ── Proxy element tracing ──────────────────────────────────────────────────
    st.subheader("🔍 Element‑Level Tracing (Proxy Elements)")
    proxy_total = an.get("proxy_list_total", len(an.get("proxy_list",[])))
    if an["proxy_list"]:
        if proxy_total > 500:
            st.warning(f"⚠️ Large model — showing first 500 of {proxy_total} proxy elements.")
        st.dataframe(pd.DataFrame(an["proxy_list"]), use_container_width=True)
    else:
        st.markdown('<p style="color:#8b949e">No proxy elements detected.</p>', unsafe_allow_html=True)

    # ── IFC Relationships ──────────────────────────────────────────────────────
    st.subheader("🔗 IFC Relationships")
    _rel_rows = an.get("relationship_summary", [])
    if not _rel_rows:
        try:
            _m = ifcopenshell.open("temp.ifc")
            _fallback_catalog = [
                ("IfcRelContainedInSpatialStructure", "Element -> Storey assignment"),
                ("IfcRelDefinesByProperties",         "Element -> Property Sets (Psets)"),
                ("IfcRelAssociatesMaterial",          "Element -> Material"),
                ("IfcRelConnectsElements",            "Element <-> Element connection"),
                ("IfcRelFillsElement",                "Door/Window -> Wall opening"),
                ("IfcRelAggregates",                  "Element -> Parent assembly"),
                ("IfcRelAssociatesClassification",    "Element -> Classification system"),
            ]
            for _rel_type, _meaning in _fallback_catalog:
                try:
                    _count = len(_m.by_type(_rel_type))
                except Exception:
                    _count = 0
                if _count > 0:
                    _rel_rows.append({
                        "Relationship": _rel_type,
                        "Meaning": _meaning,
                        "Count": _count,
                    })
        except Exception:
            _rel_rows = []

    if _rel_rows:
        st.dataframe(pd.DataFrame(_rel_rows), use_container_width=True, hide_index=True)
        st.caption(f"{len(_rel_rows)} relationship types found in this model.")
    else:
        st.info("No relationships found in this IFC model.")




    # ── PDF report ─────────────────────────────────────────────────────────────
    st.markdown("---")
    def generate_pdf(file_path="IFC_Analysis_Report.pdf"):
        def _safe(text):
            """FPDF default font is latin-1; replace unsupported chars."""
            return str(text).encode("latin-1", "replace").decode("latin-1")

        def _line(pdf_obj, text, h=7):
            pdf_obj.multi_cell(0, h, _safe(text))

        def _section(pdf_obj, title):
            pdf_obj.ln(3)
            pdf_obj.set_font("Arial", "B", 12)
            _line(pdf_obj, title, 8)
            pdf_obj.set_font("Arial", size=11)

        _total_loss_pct = an.get("data_loss_score", 0)
        _model_score = an.get("data_integrity", max(0, round(100 - _total_loss_pct, 1)))

        _l1 = an.get("type_loss_pct", an.get("proxy_pct", 0))
        _l2 = an.get("prop_loss_pct", 0)
        _l3 = an.get("qty_loss_pct", 0)
        _l4 = an.get("rel_loss_pct", 0)
        _l5 = an.get("geo_loss_pct", 0)

        _l1c = an.get("type_loss_count", an.get("proxy_elements", 0))
        _l2c = an.get("prop_loss_count", an.get("missing_pset_count", 0))
        _l3c = an.get("qty_loss_count", 0)
        _l4c = an.get("rel_loss_count", 0)
        _l5c = an.get("geo_loss_count", 0)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        _line(pdf, "IFC Home Dashboard Report", 10)
        pdf.set_font("Arial", size=11)
        _line(pdf, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        _line(pdf, f"User Name: {context.get('name', 'N/A')}")
        _line(pdf, f"Role: {context.get('role', 'N/A')} | Domain: {context.get('domain', 'N/A')} | Purpose: {context.get('purpose', 'N/A')}")

        _section(pdf, "1) Summary Metrics")
        _line(pdf, f"Total Elements: {an.get('total_elements', 0)}")
        _line(pdf, f"Semantic Elements: {an.get('semantic_elements', 0)} ({an.get('semantic_pct', 0):.1f}%)")
        _line(pdf, f"Proxy Elements: {an.get('proxy_elements', 0)} ({an.get('proxy_pct', 0):.1f}%)")
        _line(pdf, f"Other Semantic Elements: {an.get('other_semantic', 0)} ({an.get('other_pct', 0):.1f}%)")
        _line(pdf, f"Severity Level: {an.get('severity', 'N/A')}")

        _section(pdf, "2) 5-Level Data Loss Analysis + Model Score")
        _line(pdf, f"L1 Semantic Loss (30%): {_l1:.1f}% | {_l1c} elements")
        _line(pdf, f"L2 Property Loss (20%): {_l2:.1f}% | {_l2c} elements")
        _line(pdf, f"L3 Quantity Loss (15%): {_l3:.1f}% | {_l3c} elements")
        _line(pdf, f"L4 Relationship Loss (25%): {_l4:.1f}% | {_l4c} elements")
        _line(pdf, f"L5 Geometry Loss (10%): {_l5:.1f}% | {_l5c} elements")
        _line(pdf, f"Total Loss: {_total_loss_pct:.1f}%")
        _line(pdf, f"Model Integrity Score: {_model_score:.1f}/100")

        _section(pdf, "3) Element-Level Tracking")
        _proxy_rows = an.get("proxy_list", [])
        _line(pdf, f"Proxy tracking: showing {min(len(_proxy_rows), 50)} of {an.get('proxy_list_total', len(_proxy_rows))} entries")
        for i, p in enumerate(_proxy_rows[:50], 1):
            _line(pdf, f"{i}. {p.get('Name', 'Unnamed')} | {p.get('IFC Type', 'N/A')} | {p.get('GlobalId', 'N/A')}")

        _missing_rows = an.get("missing_pset_list", [])
        _line(pdf, "")
        _line(pdf, f"Missing Pset tracking: showing {min(len(_missing_rows), 50)} of {an.get('missing_pset_count', len(_missing_rows))} entries")
        for i, r in enumerate(_missing_rows[:50], 1):
            _line(pdf, f"{i}. {r.get('Element Name', 'Unnamed')} | {r.get('IFC Type', 'N/A')} | {r.get('GlobalId', 'N/A')} | {r.get('Issue', 'N/A')}")

        _section(pdf, "4) IFC Relationships")
        _rel_rows = an.get("relationship_summary", [])
        if not _rel_rows:
            try:
                _m = ifcopenshell.open("temp.ifc")
                _fallback_catalog = [
                    ("IfcRelContainedInSpatialStructure", "Element -> Storey assignment"),
                    ("IfcRelDefinesByProperties",         "Element -> Property Sets (Psets)"),
                    ("IfcRelAssociatesMaterial",          "Element -> Material"),
                    ("IfcRelConnectsElements",            "Element <-> Element connection"),
                    ("IfcRelFillsElement",                "Door/Window -> Wall opening"),
                    ("IfcRelAggregates",                  "Element -> Parent assembly"),
                    ("IfcRelAssociatesClassification",    "Element -> Classification system"),
                ]
                for _rel_type, _meaning in _fallback_catalog:
                    try:
                        _count = len(_m.by_type(_rel_type))
                    except Exception:
                        _count = 0
                    if _count > 0:
                        _rel_rows.append({
                            "Relationship": _rel_type,
                            "Meaning": _meaning,
                            "Count": _count,
                        })
            except Exception:
                _rel_rows = []
        if _rel_rows:
            for r in _rel_rows:
                _line(pdf, f"{r.get('Relationship', 'N/A')}: {r.get('Count', 0)} ({r.get('Meaning', 'N/A')})")
        else:
            _line(pdf, "No IFC relationships found in this model.")

        _section(pdf, "5) Additional Scores")
        _line(pdf, f"Model Quality Score: {an.get('quality_score', 'N/A')} / 100 ({an.get('quality_grade', 'N/A')})")
        pdf.output(file_path)
        return file_path

    if st.button("📄 Download PDF Report"):
        pdf_path = generate_pdf()
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="⬇️ Click to download PDF",
                data=f,
                file_name="IFC_Analysis_Report.pdf",
                mime="application/pdf",
            )

    # ── Dashboard navigation cards ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📐 Visual Dashboards")
    st.caption("Click a card to open the dashboard instantly.")

    # Row 1 — 4 cards
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    with r1c1:
        if st.button("🔎 **Proxy Classification**\n→ Open", key="nav_proxy_cls", use_container_width=True):
            st.switch_page("pages/1_🔎_Proxy_Classification.py")
    with r1c2:
        if st.button("📦 **Pset Analysis**\n→ Open", key="nav_pset", use_container_width=True):
            st.switch_page("pages/2_📦_Pset_Analysis.py")
    with r1c3:
        if st.button("🧊 **3D BIM Viewer**\n→ Open", key="nav_3d", use_container_width=True):
            st.switch_page("pages/3_🧊_3D_BIM_Viewer.py")
    with r1c4:
        if st.button("🔥 **Issue Heatmap**\n→ Open", key="nav_heat", use_container_width=True):
            st.switch_page("pages/4_🔥_Issue_Heatmap.py")

    # Row 2 — 4 cards
    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    with r2c1:
        if st.button("🏢 **Storey Quality Score**\n→ Open", key="nav_storey", use_container_width=True):
            st.switch_page("pages/5_🏢_Storey_Quality.py")
    with r2c2:
        if st.button("📏 **Rule Validation**\n→ Open", key="nav_rules", use_container_width=True):
            st.switch_page("pages/6_📏_Rule_Validation.py")
    with r2c3:
        if st.button("🏛️ **NBC 2016 Compliance**\n→ Open", key="nav_nbc", use_container_width=True):
            st.switch_page("pages/7_🏛️_NBC_Compliance.py")
    with r2c4:
        if st.button("🛠️ **Correction Suggestions**\n→ Open", key="nav_fix", use_container_width=True):
            st.switch_page("pages/8_🛠️_Correction_Suggestions.py")

    # Row 3 — Model Score + Version Comparison
    r3c1, r3c2, r3c3 = st.columns(3)
    with r3c1:
        if st.button("📊 **Model Score**\n→ Open", key="nav_score", use_container_width=True):
            st.switch_page("pages/9_📊_Model_Score.py")
    with r3c2:
        if st.button("📋 **BCF Generator**\n→ Open", key="nav_bcf", use_container_width=True):
            st.switch_page("pages/10_📋_BCF_Generator.py")
    with r3c3:
        if st.button("🔀 **Version Comparison**\n→ Open", key="nav_compare", use_container_width=True):
            st.switch_page("pages/11_🔀_Version_Comparison.py")

    # ── 📲 PUBLISH DEMO — Save snapshot + show QR ─────────────────────────────
    st.markdown("---")
    st.subheader("📲 Publish Demo for Audience")
    st.caption(
        "Saves your current analysis results to the server so anyone on the same Wi-Fi "
        "can scan the QR code and browse the full interactive dashboard on their phone."
    )

    if st.button("🚀 Publish Demo & Show QR Code", use_container_width=True, type="primary"):
        import json, socket, datetime

        # ── Collect everything from session_state.analysis ────────────────────
        _an  = st.session_state.get("analysis", {})
        _src = st.session_state.get("export_source", {})
        _ctx = st.session_state.get("user_context", {})

        # Storey data — scan model directly (lightweight)
        _storey_data = []
        try:
            _m2 = ifcopenshell.open("temp.ifc")
            for _storey in _m2.by_type("IfcBuildingStorey"):
                _sname = _storey.Name or "Unnamed Storey"
                _elems_in = []
                for _rel in getattr(_storey, "ContainsElements", []):
                    if _rel.is_a("IfcRelContainedInSpatialStructure"):
                        _elems_in.extend(_rel.RelatedElements)
                _s_total   = len(_elems_in)
                _s_proxies = sum(1 for e in _elems_in if e.is_a("IfcBuildingElementProxy"))
                _PSET_MAP_S = {
                    "IfcWall":"Pset_WallCommon","IfcWallStandardCase":"Pset_WallCommon",
                    "IfcDoor":"Pset_DoorCommon","IfcWindow":"Pset_WindowCommon",
                    "IfcSlab":"Pset_SlabCommon","IfcColumn":"Pset_ColumnCommon",
                    "IfcBeam":"Pset_BeamCommon","IfcRoof":"Pset_RoofCommon",
                }
                _s_missing_pset = 0
                for _e in _elems_in:
                    _req = _PSET_MAP_S.get(_e.is_a())
                    if not _req:
                        continue
                    _has = any(
                        d.is_a("IfcRelDefinesByProperties") and
                        getattr(d.RelatingPropertyDefinition, "Name", "") == _req
                        for d in getattr(_e, "IsDefinedBy", [])
                    )
                    if not _has:
                        _s_missing_pset += 1
                # Score: penalise proxy% and missing pset%
                _s_proxy_pct   = (_s_proxies / _s_total * 100) if _s_total else 0
                _s_pset_pen    = (_s_missing_pset / max(_s_total, 1) * 100)
                _s_score       = max(0, round(100 - _s_proxy_pct * 0.6 - _s_pset_pen * 0.4))
                _storey_data.append({
                    "Storey":      _sname,
                    "Elements":    _s_total,
                    "Proxies":     _s_proxies,
                    "MissingPset": _s_missing_pset,
                    "Score":       _s_score,
                })
        except Exception:
            pass

        # Rule validation — lightweight re-check
        _rules_data = []
        try:
            _m3 = ifcopenshell.open("temp.ifc")
            _all_e  = [e for e in _m3.by_type("IfcProduct")
                       if e.is_a() not in {"IfcSpace","IfcOpeningElement","IfcVirtualElement",
                                           "IfcAnnotation","IfcSite","IfcBuilding",
                                           "IfcBuildingStorey","IfcProject"}]
            _walls3 = _m3.by_type("IfcWall") + _m3.by_type("IfcWallStandardCase")
            _doors3 = _m3.by_type("IfcDoor")
            _wins3  = _m3.by_type("IfcWindow")

            def _has_pset(elem, pset_name):
                for d in getattr(elem, "IsDefinedBy", []):
                    if d.is_a("IfcRelDefinesByProperties"):
                        ps = d.RelatingPropertyDefinition
                        if ps and ps.is_a("IfcPropertySet") and ps.Name == pset_name:
                            return True
                return False

            def _has_prop(elem, pset_name, prop_name):
                for d in getattr(elem, "IsDefinedBy", []):
                    if d.is_a("IfcRelDefinesByProperties"):
                        ps = d.RelatingPropertyDefinition
                        if ps and ps.is_a("IfcPropertySet") and ps.Name == pset_name:
                            for p in getattr(ps, "HasProperties", []):
                                if p.Name == prop_name:
                                    return True
                return False

            _walls_no_fire   = [w for w in _walls3 if not _has_prop(w, "Pset_WallCommon", "FireRating")]
            _doors_no_pset   = [d for d in _doors3 if not _has_pset(d, "Pset_DoorCommon")]
            _wins_no_thermal = [w for w in _wins3  if not _has_prop(w, "Pset_WindowCommon", "ThermalTransmittance")]
            _proxies3        = _m3.by_type("IfcBuildingElementProxy")
            _doors_no_host   = [d for d in _doors3 if not any(r.is_a("IfcRelFillsElement") for r in getattr(d, "FillsVoids", []))]
            _no_storey       = [e for e in _all_e  if not any(
                r.is_a("IfcRelContainedInSpatialStructure") and
                getattr(r,"RelatingStructure",None) and r.RelatingStructure.is_a("IfcBuildingStorey")
                for r in getattr(e,"ContainedInStructure",[])
            )]
            _guids = [e.GlobalId for e in _all_e]
            _unique_guids = len(_guids) == len(set(_guids))
            _has_site = len(_m3.by_type("IfcSite")) > 0
            _schema   = str(getattr(_m3.header, "file_schema", "")).upper()
            _is_ifc4  = "IFC4" in _schema

            _rules_data = [
                {"Rule": "All walls have FireRating",           "Status": "✅ PASS" if not _walls_no_fire   else "❌ FAIL", "Affected": len(_walls_no_fire)},
                {"Rule": "All doors have Pset_DoorCommon",      "Status": "✅ PASS" if not _doors_no_pset   else "❌ FAIL", "Affected": len(_doors_no_pset)},
                {"Rule": "No IfcBuildingElementProxy",          "Status": "✅ PASS" if not _proxies3        else "⚠️ WARN", "Affected": len(_proxies3)},
                {"Rule": "All elements assigned to a storey",   "Status": "✅ PASS" if not _no_storey       else "⚠️ WARN", "Affected": len(_no_storey)},
                {"Rule": "All doors hosted in walls",           "Status": "✅ PASS" if not _doors_no_host   else "⚠️ WARN", "Affected": len(_doors_no_host)},
                {"Rule": "All windows have ThermalTransmittance","Status":"✅ PASS" if not _wins_no_thermal  else "❌ FAIL", "Affected": len(_wins_no_thermal)},
                {"Rule": "GlobalIds are unique",                "Status": "✅ PASS" if _unique_guids        else "❌ FAIL", "Affected": 0 if _unique_guids else len(_guids)-len(set(_guids))},
                {"Rule": "Project has IfcSite defined",         "Status": "✅ PASS" if _has_site            else "❌ FAIL", "Affected": 0},
                {"Rule": "IFC schema version is IFC4",          "Status": "✅ PASS" if _is_ifc4             else "⚠️ WARN", "Affected": 0},
            ]
        except Exception:
            pass

        # Relationship summary
        _rels_data = []
        try:
            _m4 = ifcopenshell.open("temp.ifc")
            for _rt, _meaning in [
                ("IfcRelContainedInSpatialStructure", "Element → Storey"),
                ("IfcRelDefinesByProperties",         "Element → Psets"),
                ("IfcRelAssociatesMaterial",          "Element → Material"),
                ("IfcRelConnectsElements",            "Element ↔ Element"),
                ("IfcRelFillsElement",                "Door/Window → Wall"),
                ("IfcRelAggregates",                  "Element → Assembly"),
            ]:
                try:
                    _c = len(_m4.by_type(_rt))
                except Exception:
                    _c = 0
                _rels_data.append({"Relationship": _rt, "Count": _c, "Meaning": _meaning})
        except Exception:
            pass

        # ── Build snapshot dict ───────────────────────────────────────────────
        snapshot = {
            "published_at":   datetime.datetime.now().strftime("%d %b %Y, %H:%M"),
            "published_by":   _ctx.get("name", "Presenter"),
            "file_name":      st.session_state.get("last_file_id", "model.ifc").split("_")[0] if st.session_state.get("last_file_id") else "model.ifc",
            "export_tool":    _src.get("tool", "Unknown"),
            "ifc_version":    _src.get("version", "Unknown"),
            "analysis":       {k: v for k, v in _an.items() if isinstance(v, (int, float, str, list, dict, bool, type(None)))},
            "storeys":        _storey_data,
            "rules":          _rules_data,
            "relationships":  _rels_data,
            "user_context":   _ctx,
        }

        # ── Save to disk ──────────────────────────────────────────────────────
        import pathlib
        _snap_path = pathlib.Path("demo_snapshot.json")
        with open(_snap_path, "w", encoding="utf-8") as _f:
            json.dump(snapshot, _f, ensure_ascii=False, default=str)

        # ── Detect local IP and store demo URL ────────────────────────────────
        try:
            _s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            _s.connect(("8.8.8.8", 80))
            _local_ip = _s.getsockname()[0]
            _s.close()
        except Exception:
            _local_ip = "localhost"

        # Streamlit slug rule: strip leading digits+underscores from filename
        # "12_Demo_QR.py" → /Demo_QR
        _demo_url = f"http://{_local_ip}:8501/Demo_QR"

        # ── Generate QR code ──────────────────────────────────────────────────
        import io as _io
        _qr_bytes = None
        try:
            import qrcode
            _qr = qrcode.QRCode(version=2, box_size=8, border=3,
                                error_correction=qrcode.constants.ERROR_CORRECT_H)
            _qr.add_data(_demo_url)
            _qr.make(fit=True)
            _qr_img = _qr.make_image(fill_color="#e6edf3", back_color="#0d1117")
            _qr_buf = _io.BytesIO()
            _qr_img.save(_qr_buf, format="PNG")
            _qr_bytes = _qr_buf.getvalue()
        except Exception:
            pass

        st.session_state["demo_published"]   = True
        st.session_state["demo_url"]         = _demo_url
        st.session_state["demo_qr_bytes"]    = _qr_bytes
        st.session_state["demo_published_at"]= snapshot["published_at"]
        st.rerun()

    # ── Show QR on Home page after publish ────────────────────────────────────
    if st.session_state.get("demo_published"):
        _url  = st.session_state.get("demo_url", "")
        _at   = st.session_state.get("demo_published_at", "")
        _qrb  = st.session_state.get("demo_qr_bytes")

        _qr_col, _info_col = st.columns([1, 2])
        with _qr_col:
            if _qrb:
                st.image(_qrb, caption="Scan to open demo on phone", width=220)
            else:
                st.info("Install `qrcode` and `Pillow` to generate QR.")
        with _info_col:
            st.markdown(f"""
<div style="background:#0d2b0d;border:2px solid #238636;border-radius:14px;
padding:20px 24px;height:100%;box-sizing:border-box;">
  <div style="font-size:18px;font-weight:800;color:#3fb950;margin-bottom:6px;">✅ Demo Published!</div>
  <div style="font-size:13px;color:#8b949e;margin-bottom:10px;">Published at {_at}</div>
  <div style="font-size:12px;color:#8b949e;margin-bottom:8px;">
    📱 Ask audience to connect to <strong style="color:#e6edf3;">the same Wi-Fi</strong>, then scan the QR.
  </div>
  <div style="background:#111827;border:1px solid #1e3a5f;border-radius:8px;
  padding:10px 14px;font-family:monospace;font-size:13px;color:#58a6ff;
  word-break:break-all;">{_url}</div>
</div>""", unsafe_allow_html=True)