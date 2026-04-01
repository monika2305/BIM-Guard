import streamlit as st
import ifcopenshell
import pandas as pd
import json
import re
from fpdf import FPDF
from io import BytesIO
from datetime import datetime

st.set_page_config(
    page_title="Rule Validation",
    page_icon="📏",
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


# ── Guards ─────────────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in"):
    st.warning("Please log in from the Home page first.")
    st.stop()

try:
    model = ifcopenshell.open("temp.ifc")
except Exception:
    st.warning("⚠️ No IFC file found. Please upload a file on the **Home** page first.")
    st.stop()

an = st.session_state.get("analysis", {})
if "custom_rules" not in st.session_state:
    st.session_state.custom_rules = []

# ══════════════════════════════════════════════════════════════════════════════
# BUILT-IN RULE LIBRARY
# Each rule: id, name, category, description, severity, check_fn
# ══════════════════════════════════════════════════════════════════════════════

def get_pset_value(elem, pset_name, prop_name):
    """Safely extract a property set value from an IFC element."""
    try:
        for defn in getattr(elem, "IsDefinedBy", []):
            if defn.is_a("IfcRelDefinesByProperties"):
                ps = defn.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet") and ps.Name == pset_name:
                    for prop in ps.HasProperties:
                        if prop.Name == prop_name:
                            val = getattr(prop, "NominalValue", None)
                            if val:
                                return val.wrappedValue
    except Exception:
        pass
    return None

def get_all_psets(elem):
    """Return dict of {pset_name: {prop_name: value}}."""
    result = {}
    try:
        for defn in getattr(elem, "IsDefinedBy", []):
            if defn.is_a("IfcRelDefinesByProperties"):
                ps = defn.RelatingPropertyDefinition
                if ps and ps.is_a("IfcPropertySet"):
                    props = {}
                    for prop in getattr(ps, "HasProperties", []):
                        val = getattr(prop, "NominalValue", None)
                        props[prop.Name] = val.wrappedValue if val else None
                    result[ps.Name] = props
    except Exception:
        pass
    return result

def has_pset(elem, pset_name):
    return pset_name in get_all_psets(elem)

def elem_name(elem):
    return getattr(elem, "Name", None) or "Unnamed"

def elem_type_name(elem):
    try:
        for rel in getattr(elem, "IsTypedBy", []):
            t = getattr(rel, "RelatingType", None)
            if t:
                return getattr(t, "Name", None) or getattr(t, "is_a", lambda: "")()
    except Exception:
        pass
    return None

# ── Rule definitions ───────────────────────────────────────────────────────────
BUILTIN_RULES = [

    # ── NAMING ────────────────────────────────────────────────────────────────
    {
        "id": "NM01", "category": "Naming",
        "name": "Elements must have a Name",
        "description": "Every physical element must have a non-empty Name attribute.",
        "severity": "High",
        "applies_to": None,   # all elements
        "check": lambda elem: bool(getattr(elem, "Name", None) and str(elem.Name).strip()),
        "fail_msg": lambda elem: f"Name is missing or empty",
    },
    {
        "id": "NM02", "category": "Naming",
        "name": "No 'Unnamed' placeholders",
        "description": "Element names must not contain 'Unnamed', 'Unknown' or 'Generic'.",
        "severity": "Medium",
        "applies_to": None,
        "check": lambda elem: not any(
            kw in (getattr(elem, "Name", "") or "").lower()
            for kw in ["unnamed", "unknown", "generic", "undefined"]
        ),
        "fail_msg": lambda elem: f"Name '{elem_name(elem)}' contains a placeholder keyword",
    },
    {
        "id": "NM03", "category": "Naming",
        "name": "GlobalId must be unique",
        "description": "Every element's GlobalId must be unique within the model.",
        "severity": "Critical",
        "applies_to": None,
        "check": None,   # handled separately via batch check
        "fail_msg": lambda elem: f"Duplicate GlobalId detected",
    },

    # ── CLASSIFICATION ─────────────────────────────────────────────────────────
    {
        "id": "CL01", "category": "Classification",
        "name": "No IfcBuildingElementProxy",
        "description": "Generic proxies indicate lost semantic meaning. All elements should have a specific IFC type.",
        "severity": "High",
        "applies_to": "IfcBuildingElementProxy",
        "check": lambda elem: False,   # any proxy is a failure
        "fail_msg": lambda elem: f"'{elem_name(elem)}' is an unclassified proxy element",
    },
    {
        "id": "CL02", "category": "Classification",
        "name": "Elements must be typed",
        "description": "Physical elements should reference an IfcElementType for consistent properties.",
        "severity": "Medium",
        "applies_to": None,
        "check": lambda elem: elem_type_name(elem) is not None,
        "fail_msg": lambda elem: f"'{elem_name(elem)}' has no element type assigned",
    },

    # ── PROPERTY SETS ─────────────────────────────────────────────────────────
    {
        "id": "PS01", "category": "Property Sets",
        "name": "Walls must have Pset_WallCommon",
        "description": "All IfcWall elements must include Pset_WallCommon with fire rating, load bearing status etc.",
        "severity": "High",
        "applies_to": "IfcWall",
        "check": lambda elem: has_pset(elem, "Pset_WallCommon"),
        "fail_msg": lambda elem: f"Wall '{elem_name(elem)}' is missing Pset_WallCommon",
    },
    {
        "id": "PS02", "category": "Property Sets",
        "name": "Doors must have Pset_DoorCommon",
        "description": "All IfcDoor elements must include Pset_DoorCommon.",
        "severity": "High",
        "applies_to": "IfcDoor",
        "check": lambda elem: has_pset(elem, "Pset_DoorCommon"),
        "fail_msg": lambda elem: f"Door '{elem_name(elem)}' is missing Pset_DoorCommon",
    },
    {
        "id": "PS03", "category": "Property Sets",
        "name": "Windows must have Pset_WindowCommon",
        "description": "All IfcWindow elements must include Pset_WindowCommon.",
        "severity": "High",
        "applies_to": "IfcWindow",
        "check": lambda elem: has_pset(elem, "Pset_WindowCommon"),
        "fail_msg": lambda elem: f"Window '{elem_name(elem)}' is missing Pset_WindowCommon",
    },
    {
        "id": "PS04", "category": "Property Sets",
        "name": "Slabs must have Pset_SlabCommon",
        "description": "All IfcSlab elements must include Pset_SlabCommon.",
        "severity": "Medium",
        "applies_to": "IfcSlab",
        "check": lambda elem: has_pset(elem, "Pset_SlabCommon"),
        "fail_msg": lambda elem: f"Slab '{elem_name(elem)}' is missing Pset_SlabCommon",
    },
    {
        "id": "PS05", "category": "Property Sets",
        "name": "Walls: IsExternal must be defined",
        "description": "Pset_WallCommon.IsExternal must be explicitly set (True or False).",
        "severity": "Medium",
        "applies_to": "IfcWall",
        "check": lambda elem: get_pset_value(elem, "Pset_WallCommon", "IsExternal") is not None,
        "fail_msg": lambda elem: f"Wall '{elem_name(elem)}' — IsExternal not defined in Pset_WallCommon",
    },
    {
        "id": "PS06", "category": "Property Sets",
        "name": "Walls: FireRating must be defined",
        "description": "Pset_WallCommon.FireRating must be explicitly set for fire safety compliance.",
        "severity": "High",
        "applies_to": "IfcWall",
        "check": lambda elem: get_pset_value(elem, "Pset_WallCommon", "FireRating") is not None,
        "fail_msg": lambda elem: f"Wall '{elem_name(elem)}' — FireRating not set in Pset_WallCommon",
    },
    {
        "id": "PS07", "category": "Property Sets",
        "name": "Columns must have Pset_ColumnCommon",
        "description": "All IfcColumn elements must include Pset_ColumnCommon.",
        "severity": "Medium",
        "applies_to": "IfcColumn",
        "check": lambda elem: has_pset(elem, "Pset_ColumnCommon"),
        "fail_msg": lambda elem: f"Column '{elem_name(elem)}' is missing Pset_ColumnCommon",
    },

    # ── GEOMETRY ──────────────────────────────────────────────────────────────
    {
        "id": "GM01", "category": "Geometry",
        "name": "Elements must have placement",
        "description": "Every physical element must have an ObjectPlacement defined.",
        "severity": "High",
        "applies_to": None,
        "check": lambda elem: getattr(elem, "ObjectPlacement", None) is not None,
        "fail_msg": lambda elem: f"'{elem_name(elem)}' has no ObjectPlacement",
    },
    {
        "id": "GM02", "category": "Geometry",
        "name": "Elements must have geometry",
        "description": "Every physical element must have a Representation (geometry).",
        "severity": "High",
        "applies_to": None,
        "check": lambda elem: getattr(elem, "Representation", None) is not None,
        "fail_msg": lambda elem: f"'{elem_name(elem)}' has no geometric representation",
    },

    # ── MATERIALS ─────────────────────────────────────────────────────────────
    {
        "id": "MT01", "category": "Materials",
        "name": "Elements must have material assigned",
        "description": "Every physical element should have at least one material association.",
        "severity": "Medium",
        "applies_to": None,
        "check": lambda elem: any(
            rel.is_a("IfcRelAssociatesMaterial")
            for rel in getattr(elem, "HasAssociations", [])
        ),
        "fail_msg": lambda elem: f"'{elem_name(elem)}' has no material assigned",
    },

    # ── IFC COMPLIANCE ────────────────────────────────────────────────────────
    {
        "id": "IC01", "category": "IFC Compliance",
        "name": "No deprecated IfcWallStandardCase",
        "description": "IfcWallStandardCase is deprecated in IFC4. Use IfcWall instead.",
        "severity": "Low",
        "applies_to": "IfcWallStandardCase",
        "check": lambda elem: False,
        "fail_msg": lambda elem: f"'{elem_name(elem)}' uses deprecated IfcWallStandardCase",
    },
    {
        "id": "IC02", "category": "IFC Compliance",
        "name": "Elements must belong to a storey",
        "description": "Every physical element should be contained in an IfcBuildingStorey.",
        "severity": "Medium",
        "applies_to": None,
        "check": lambda elem: any(
            rel.is_a("IfcRelContainedInSpatialStructure") and
            rel.RelatingStructure.is_a("IfcBuildingStorey")
            for rel in getattr(elem, "ContainedInStructure", [])
        ),
        "fail_msg": lambda elem: f"'{elem_name(elem)}' is not assigned to a building storey",
    },
]

SKIP_TYPES = {
    "IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
    "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject",
    "IfcRelAggregates","IfcZone","IfcSpatialZone","IfcRelContainedInSpatialStructure",
}

all_builtin_ids = [r["id"] for r in BUILTIN_RULES]
if "selected_builtin_rule_ids" not in st.session_state:
    st.session_state.selected_builtin_rule_ids = set(all_builtin_ids)
if "selected_custom_rule_ids" not in st.session_state:
    st.session_state.selected_custom_rule_ids = set()




# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — rule selector + summary
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📏 Rule Validation")
    st.markdown("---")
    categories = sorted(set(r["category"] for r in BUILTIN_RULES))
    cat_filters = {cat: True for cat in categories}
    sev_filters = {"Critical":True,"High":True,"Medium":True,"Low":True}

    if an:
        st.markdown("**📊 Model Summary**")
        st.metric("Total Elements", an.get("total_elements","—"))
        st.metric("Proxy Elements", an.get("proxy_elements","—"))
        st.metric("Semantic %",     f"{an.get('semantic_pct',0):.1f}%")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("📏 Advanced Rule-Based Validation")
st.caption("Validate your IFC model against BIM standards, project rules and IFC compliance checks.")

# ══════════════════════════════════════════════════════════════════════════════
# TABS: Built-in Rules | Custom Rules | Results | Report
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["📋 Rule Library", "✏️ Custom Rules", "✅ Validation Results", "📄 Export Report"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Rule Library
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.caption(f"{len(BUILTIN_RULES)} built-in rules across {len(categories)} categories.")

    SEV_COLORS = {"Critical":"#da3633","High":"#d29922","Medium":"#58a6ff","Low":"#238636"}
    SEV_ICONS  = {"Critical":"🔴","High":"🟠","Medium":"🟡","Low":"🔵"}

    st.markdown("#### 🎛️ Select Built-in Rules To Validate")
    b1, b2, b3 = st.columns([1, 1, 3])
    if b1.button("✅ Select All", key="builtin_select_all", use_container_width=True):
        st.session_state.selected_builtin_rule_ids = set(all_builtin_ids)
        st.rerun()
    if b2.button("🧹 Clear All", key="builtin_clear_all", use_container_width=True):
        st.session_state.selected_builtin_rule_ids = set()
        st.rerun()
    b3.caption("Tip: Toggle Use inside each rule card below.")

    st.caption(
        f"Selected **{len(st.session_state.selected_builtin_rule_ids)}** of **{len(BUILTIN_RULES)}** built-in rules "
        f"| Showing all rules grouped by category"
    )
    st.markdown("")

    # Clean table — one row per rule, collapsed by default per category
    _selected_builtin_next = set()
    for cat in categories:
        cat_rules = [r for r in BUILTIN_RULES if r["category"] == cat]
        if not cat_rules:
            continue
        with st.expander(f"**{cat}** — {len(cat_rules)} rules", expanded=False):
            for r in cat_rules:
                sev_col = SEV_COLORS.get(r["severity"],"#8b949e")
                sev_ico = SEV_ICONS.get(r["severity"],"⚪")
                applies = f"<code style='background:#0d1117;padding:1px 5px;border-radius:3px;font-size:10px;'>{r['applies_to']}</code>" if r.get("applies_to") else "<span style='color:#8b949e;font-size:11px;'>All elements</span>"
                rc1, rc2 = st.columns([8, 1])
                with rc1:
                    st.markdown(
                        f'<div style="border:1px solid #30363d;border-radius:8px;'
                        f'padding:10px 14px;margin-bottom:6px;background:#161b22;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">'
                        f'<div style="flex:1;">'
                        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                        f'<code style="color:#58a6ff;background:#0d1117;padding:1px 7px;border-radius:4px;font-size:11px;font-weight:700;">{r["id"]}</code>'
                        f'<span style="font-size:13px;font-weight:700;color:#e6edf3;">{r["name"]}</span>'
                        f'</div>'
                        f'<div style="font-size:12px;color:#8b949e;margin-bottom:4px;">{r["description"]}</div>'
                        f'<div style="font-size:11px;color:#8b949e;">Applies to: {applies}</div>'
                        f'</div>'
                        f'<div style="flex-shrink:0;">'
                        f'<span style="font-size:11px;font-weight:700;color:{sev_col};'
                        f'background:{sev_col}18;padding:3px 12px;border-radius:10px;'
                        f'border:1px solid {sev_col}44;white-space:nowrap;">{sev_ico} {r["severity"]}</span>'
                        f'</div>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with rc2:
                    _use_builtin = st.checkbox(
                        f"Use built-in {r['id']}",
                        value=(r["id"] in st.session_state.selected_builtin_rule_ids),
                        label_visibility="collapsed",
                    )
                    if _use_builtin:
                        _selected_builtin_next.add(r["id"])

    st.session_state.selected_builtin_rule_ids = _selected_builtin_next

    active_rules = [
        r for r in BUILTIN_RULES
        if r["id"] in st.session_state.selected_builtin_rule_ids
    ]



# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Custom Rules
# ─────────────────────────────────────────────────────────────────────────────
if "disabled_rules" not in st.session_state:
    st.session_state.disabled_rules = set()

with tab2:
    st.markdown("### ✏️ Add Custom Validation Rules")
    st.caption("Define your own project-specific rules. Custom rules are combined with built-in rules during validation.")

    with st.form("custom_rule_form", clear_on_submit=True):
        st.markdown("**New Custom Rule**")
        fc1, fc2 = st.columns([2,1])
        rule_name = fc1.text_input("Rule Name", placeholder="e.g. External walls must have U-value")
        rule_sev  = fc2.selectbox("Severity", ["Critical","High","Medium","Low"], index=1)

        fd1, fd2 = st.columns([2,1])
        rule_desc = fd1.text_input("Description", placeholder="Explain what this rule checks")
        rule_cat  = fd2.selectbox("Category", categories + ["Custom"], index=len(categories))

        fe1, fe2 = st.columns([2,1])
        rule_type = fe1.selectbox(
            "Applies To (IFC Type)",
            ["All Elements","IfcWall","IfcDoor","IfcWindow","IfcSlab","IfcColumn",
             "IfcBeam","IfcStair","IfcRoof","IfcBuildingElementProxy"],
            index=0,
        )
        rule_pset = fe2.text_input("Required Pset Name", placeholder="e.g. Pset_WallCommon")

        ff1, ff2 = st.columns(2)
        rule_prop  = ff1.text_input("Required Property", placeholder="e.g. ThermalTransmittance")
        rule_value = ff2.text_input("Expected Value (optional)", placeholder="e.g. <= 0.3")

        submitted = st.form_submit_button("➕ Add Rule", use_container_width=True)
        if submitted:
            if rule_name and rule_desc:
                new_rule = {
                    "id":          f"CR{len(st.session_state.custom_rules)+1:02d}",
                    "category":    rule_cat,
                    "name":        rule_name,
                    "description": rule_desc,
                    "severity":    rule_sev,
                    "applies_to":  None if rule_type=="All Elements" else rule_type,
                    "pset":        rule_pset or None,
                    "prop":        rule_prop or None,
                    "value":       rule_value or None,
                    "custom":      True,
                }
                st.session_state.custom_rules.append(new_rule)
                st.session_state.selected_custom_rule_ids.add(new_rule["id"])
                st.success(f"✅ Rule **{rule_name}** added!")
            else:
                st.error("Please fill in Rule Name and Description.")

    # Show existing custom rules
    if st.session_state.custom_rules:
        st.markdown(f"**{len(st.session_state.custom_rules)} Custom Rules**")
        _selected_custom_next = set()
        for i, r in enumerate(st.session_state.custom_rules):
            sev_col = SEV_COLORS.get(r["severity"],"#8b949e")
            c0, c1, c2 = st.columns([1,8,1])
            with c0:
                _use_custom = st.checkbox(
                    f"Use custom {r['id']}",
                    value=(r["id"] in st.session_state.selected_custom_rule_ids),
                    label_visibility="collapsed",
                )
                if _use_custom:
                    _selected_custom_next.add(r["id"])
            with c1:
                pset_snippet = (
                    '<div style="color:#8b949e;font-size:11px;margin-top:3px">Requires: <code>'
                    + r["pset"] + "." + (r.get("prop") or "") + "</code></div>"
                ) if r.get("pset") else ""
                cr_id   = r["id"]
                cr_name = r["name"]
                cr_desc = r["description"]
                cr_sev  = r["severity"]
                st.markdown(
                    f'<div style="border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;'
                    f'margin-bottom:6px;background:rgba(255,255,255,0.06);">'
                    f'<span style="font-weight:700;color:#f0f4f8">'
                    f'<code style="color:#8ee8ff;background:#0B1E3D;padding:1px 6px;border-radius:4px;font-size:11px">{cr_id}</code>'
                    f'&nbsp;{cr_name}</span>'
                    f'<span style="float:right;font-size:11px;font-weight:700;color:{sev_col};'
                    f'background:{sev_col}22;padding:2px 8px;border-radius:10px">{cr_sev}</span>'
                    f'<div style="color:#8b949e;font-size:12px;margin-top:4px">{cr_desc}</div>'
                    f'{pset_snippet}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("🗑", key=f"del_cr_{i}", help="Delete this rule"):
                    deleted_id = st.session_state.custom_rules[i]["id"]
                    st.session_state.custom_rules.pop(i)
                    st.session_state.selected_custom_rule_ids.discard(deleted_id)
                    st.rerun()

        st.session_state.selected_custom_rule_ids = _selected_custom_next
    else:
        st.info("No custom rules yet. Add one above.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Validation Results
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### ✅ Run Validation")

    valid_custom_ids = {r["id"] for r in st.session_state.get("custom_rules", [])}
    st.session_state.selected_custom_rule_ids = {
        rid for rid in st.session_state.selected_custom_rule_ids
        if rid in valid_custom_ids
    }

    selected_custom_rules = [
        r for r in st.session_state.get("custom_rules", [])
        if r["id"] in st.session_state.selected_custom_rule_ids
    ]

    col_run, col_info = st.columns([2,5])
    with col_run:
        run_btn = st.button("▶ Run Validation Now", type="primary", use_container_width=True)
    with col_info:
        total_rules = len(active_rules) + len(selected_custom_rules)
        st.markdown(f"**{total_rules} selected rules** will be checked against your IFC model.")

    if run_btn and total_rules == 0:
        st.warning("Please select at least one rule from the sidebar before running validation.")
        run_btn = False

    if run_btn or st.session_state.get("last_validation_results"):

        if run_btn:
            # ── Run all checks ─────────────────────────────────────────────────
            results   = []   # {rule_id, rule_name, category, severity, elem_id, elem_name, elem_type, message, status}
            pass_count= 0
            fail_count= 0

            all_products = [
                e for e in model.by_type("IfcProduct")
                if e.is_a() not in SKIP_TYPES
            ]

            # Batch: check GlobalId uniqueness
            gid_seen = {}
            for elem in all_products:
                gid = elem.GlobalId
                if gid in gid_seen:
                    gid_seen[gid].append(elem)
                else:
                    gid_seen[gid] = [elem]
            duplicate_gids = {gid for gid, elems in gid_seen.items() if len(elems) > 1}

            with st.spinner("🔍 Validating elements…"):
                for rule in active_rules:
                    rid = rule["id"]

                    # Special batch rule
                    if rid == "NM03":
                        for gid, elems in gid_seen.items():
                            if len(elems) > 1:
                                for elem in elems:
                                    results.append({
                                        "Rule ID":   rid,
                                        "Rule":      rule["name"],
                                        "Category":  rule["category"],
                                        "Severity":  rule["severity"],
                                        "Status":    "❌ FAIL",
                                        "Element":   elem_name(elem),
                                        "IFC Type":  elem.is_a(),
                                        "GlobalId":  elem.GlobalId,
                                        "Message":   f"Duplicate GlobalId: {gid}",
                                    })
                                    fail_count += 1
                        continue

                    # Normal rules
                    applies = rule.get("applies_to")
                    if applies:
                        elems_to_check = model.by_type(applies)
                    else:
                        elems_to_check = all_products

                    chk = rule.get("check")
                    if chk is None:
                        continue

                    for elem in elems_to_check:
                        if elem.is_a() in SKIP_TYPES:
                            continue
                        try:
                            passed = chk(elem)
                        except Exception:
                            passed = True   # skip on error
                        if passed:
                            pass_count += 1
                        else:
                            fail_count += 1
                            try:
                                msg = rule["fail_msg"](elem)
                            except Exception:
                                msg = "Validation failed"
                            results.append({
                                "Rule ID":   rid,
                                "Rule":      rule["name"],
                                "Category":  rule["category"],
                                "Severity":  rule["severity"],
                                "Status":    "❌ FAIL",
                                "Element":   elem_name(elem),
                                "IFC Type":  elem.is_a(),
                                "GlobalId":  elem.GlobalId,
                                "Message":   msg,
                            })

                # ── Custom rules ───────────────────────────────────────────────
                for rule in selected_custom_rules:
                    applies = rule.get("applies_to")
                    elems_to_check = model.by_type(applies) if applies else all_products
                    pset_req = rule.get("pset")
                    prop_req = rule.get("prop")
                    val_req  = rule.get("value")

                    for elem in elems_to_check:
                        if elem.is_a() in SKIP_TYPES:
                            continue
                        passed = True
                        msg    = ""
                        try:
                            if pset_req:
                                if not has_pset(elem, pset_req):
                                    passed = False
                                    msg = f"Missing required Pset: {pset_req}"
                                elif prop_req:
                                    val = get_pset_value(elem, pset_req, prop_req)
                                    if val is None:
                                        passed = False
                                        msg = f"{pset_req}.{prop_req} not defined"
                                    elif val_req:
                                        # Simple value comparison
                                        try:
                                            v = float(val)
                                            vr = val_req.strip()
                                            if vr.startswith("<=") and not v <= float(vr[2:]):
                                                passed=False; msg=f"{prop_req}={v} but required {vr}"
                                            elif vr.startswith(">=") and not v >= float(vr[2:]):
                                                passed=False; msg=f"{prop_req}={v} but required {vr}"
                                            elif vr.startswith("<") and not v < float(vr[1:]):
                                                passed=False; msg=f"{prop_req}={v} but required {vr}"
                                            elif vr.startswith(">") and not v > float(vr[1:]):
                                                passed=False; msg=f"{prop_req}={v} but required {vr}"
                                            elif vr.startswith("=") and str(val) != vr[1:].strip():
                                                passed=False; msg=f"{prop_req}={val} but required {vr}"
                                        except (ValueError, TypeError):
                                            if str(val).lower() != val_req.lower():
                                                passed=False; msg=f"{prop_req}='{val}' but expected '{val_req}'"
                        except Exception:
                            passed = True

                        if passed:
                            pass_count += 1
                        else:
                            fail_count += 1
                            results.append({
                                "Rule ID":  rule["id"],
                                "Rule":     rule["name"],
                                "Category": rule["category"],
                                "Severity": rule["severity"],
                                "Status":   "❌ FAIL",
                                "Element":  elem_name(elem),
                                "IFC Type": elem.is_a(),
                                "GlobalId": elem.GlobalId,
                                "Message":  msg or f"Failed custom rule: {rule['name']}",
                            })

            st.session_state.last_validation_results = results
            st.session_state.last_pass_count = pass_count
            st.session_state.last_fail_count = fail_count

        # ── Display Results ────────────────────────────────────────────────────
        results    = st.session_state.get("last_validation_results", [])
        pass_count = st.session_state.get("last_pass_count", 0)
        fail_count = st.session_state.get("last_fail_count", 0)
        total_checks = pass_count + fail_count
        pass_pct     = round(pass_count / total_checks * 100, 1) if total_checks else 0

        st.markdown("---")
        st.markdown("### 📊 Validation Summary")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Checks",   total_checks)
        m2.metric("✅ Passed",       pass_count,  delta=f"{pass_pct}%", delta_color="normal")
        m3.metric("❌ Failed",       fail_count,  delta=f"-{round(100-pass_pct,1)}%" if fail_count else None, delta_color="inverse")

        # Overall health score
        health = pass_pct
        h_color = "#238636" if health>=90 else "#d29922" if health>=70 else "#da3633"
        m4.markdown(
            f'<div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;'
            f'padding:12px;text-align:center;">'
            f'<div style="color:#8b949e;font-size:12px;margin-bottom:4px">Health Score</div>'
            f'<div style="font-size:26px;font-weight:700;color:{h_color}">{health:.0f}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Severity breakdown
        st.markdown("#### Failures by Severity")
        sv_cols = st.columns(4)
        for i, (sev, ico) in enumerate([("Critical","🔴"),("High","🟠"),("Medium","🟡"),("Low","🔵")]):
            cnt = sum(1 for r in results if r["Severity"]==sev)
            sv_cols[i].metric(f"{ico} {sev}", cnt)

        # Category breakdown bar
        st.markdown("#### Failures by Category")
        cat_counts = {}
        for r in results:
            cat_counts[r["Category"]] = cat_counts.get(r["Category"],0) + 1
        if cat_counts:
            cat_df = pd.DataFrame({"Category":list(cat_counts.keys()),"Failures":list(cat_counts.values())})
            cat_df = cat_df.sort_values("Failures", ascending=False)
            st.bar_chart(cat_df.set_index("Category"))
        else:
            st.success("🎉 All checks passed! No failures to display.")

        # ── Detailed failure table ─────────────────────────────────────────────
        if results:
            st.markdown("---")
            st.markdown("### 🔍 Failure Details")

            # Filters
            f1, f2, f3, f4 = st.columns(4)
            filt_cat  = f1.selectbox("Category",  ["All"] + categories + ["Custom"], key="res_cat")
            filt_sev  = f2.selectbox("Severity",  ["All","Critical","High","Medium","Low"], key="res_sev")
            filt_type = f3.selectbox("IFC Type",  ["All"] + sorted(set(r["IFC Type"] for r in results)), key="res_type")
            filt_text = f4.text_input("Search element / message", placeholder="e.g. Wall_001", key="res_search")
            df = pd.DataFrame(results)
            if filt_cat  != "All": df = df[df["Category"]==filt_cat]
            if filt_sev  != "All": df = df[df["Severity"]==filt_sev]
            if filt_type != "All": df = df[df["IFC Type"]==filt_type]
            if filt_text:
                mask = (
                    df["Element"].str.contains(filt_text, case=False, na=False) |
                    df["Message"].str.contains(filt_text, case=False, na=False)
                )
                df = df[mask]

            st.markdown(f"**{len(df)} failures shown**")
            st.dataframe(
                df[["Rule ID","Severity","Category","Rule","Element","IFC Type","Message"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rule ID":  st.column_config.TextColumn(width="small"),
                    "Severity": st.column_config.TextColumn(width="small"),
                    "Category": st.column_config.TextColumn(width="medium"),
                    "Rule":     st.column_config.TextColumn(width="large"),
                    "Element":  st.column_config.TextColumn(width="medium"),
                    "IFC Type": st.column_config.TextColumn(width="medium"),
                    "Message":  st.column_config.TextColumn(width="large"),
                },
            )

            # CSV export
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Download CSV",
                data=csv,
                file_name="IFC_Validation_Results.csv",
                mime="text/csv",
                use_container_width=False,
            )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Export Report
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 📄 Export Validation Report")

    results    = st.session_state.get("last_validation_results")
    pass_count = st.session_state.get("last_pass_count", 0)
    fail_count = st.session_state.get("last_fail_count", 0)

    if not results and fail_count == 0:
        st.info("Run validation first (go to **Validation Results** tab) to generate a report.")
    else:
        total_checks = pass_count + fail_count
        pass_pct = round(pass_count/total_checks*100,1) if total_checks else 0

        if st.button("📄 Generate PDF Report", type="primary", use_container_width=False):
            with st.spinner("Generating PDF…"):
                pdf = FPDF()
                pdf.add_page()

                # Title
                pdf.set_font("Arial","B",20)
                pdf.set_text_color(30,80,140)
                pdf.cell(0,12,"IFC Rule Validation Report",ln=True,align="C")
                pdf.set_font("Arial","",10)
                pdf.set_text_color(100,100,100)
                pdf.cell(0,6,f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",ln=True,align="C")
                pdf.ln(6)

                # Summary box
                pdf.set_fill_color(240,245,255)
                pdf.set_draw_color(100,150,220)
                pdf.set_font("Arial","B",12)
                pdf.set_text_color(30,80,140)
                pdf.cell(0,8,"Validation Summary",ln=True,fill=True)
                pdf.set_font("Arial","",11)
                pdf.set_text_color(40,40,40)

                summary_rows = [
                    ("Total Checks Run",  str(total_checks)),
                    ("Checks Passed",     f"{pass_count}  ({pass_pct}%)"),
                    ("Checks Failed",     str(fail_count)),
                    ("Health Score",      f"{pass_pct:.0f}%"),
                    ("Critical Failures", str(sum(1 for r in (results or []) if r["Severity"]=="Critical"))),
                    ("High Failures",     str(sum(1 for r in (results or []) if r["Severity"]=="High"))),
                ]
                for label, value in summary_rows:
                    pdf.cell(80,7,label,border="B")
                    pdf.cell(0,7,value,ln=True,border="B")
                pdf.ln(8)

                # Failures table
                if results:
                    pdf.set_font("Arial","B",11)
                    pdf.set_text_color(30,80,140)
                    pdf.cell(0,8,"Failure Details",ln=True)
                    pdf.ln(2)

                    pdf.set_font("Arial","B",8)
                    pdf.set_fill_color(220,230,245)
                    pdf.set_text_color(20,20,20)
                    cols = [("ID",12),("Sev",16),("Category",28),("Rule",50),("Element",35),("Message",57)]
                    for (h,w) in cols:
                        pdf.cell(w,6,h,border=1,fill=True)
                    pdf.ln()

                    pdf.set_font("Arial","",7)
                    SEV_RGB = {
                        "Critical":(218,54,51),"High":(210,153,34),
                        "Medium":(31,111,235),  "Low":(35,134,54),
                    }
                    for i, r in enumerate(results[:2000]):  # cap at 2000 rows for large models
                        fill = i%2==0
                        pdf.set_fill_color(248,250,255) if fill else pdf.set_fill_color(255,255,255)
                        sr,sg,sb = SEV_RGB.get(r["Severity"],(60,60,60))
                        pdf.set_text_color(sr,sg,sb)
                        pdf.cell(12,5,r["Rule ID"],border="B",fill=fill)
                        pdf.cell(16,5,r["Severity"],border="B",fill=fill)
                        pdf.set_text_color(40,40,40)
                        pdf.cell(28,5,r["Category"][:18],border="B",fill=fill)
                        pdf.cell(50,5,r["Rule"][:30],border="B",fill=fill)
                        pdf.cell(35,5,(r["Element"] or "")[:20],border="B",fill=fill)
                        pdf.cell(57,5,(r["Message"] or "")[:38],border="B",fill=fill,ln=True)

                    if len(results) > 200:
                        pdf.set_font("Arial","I",8)
                        pdf.set_text_color(120,120,120)
                        pdf.cell(0,6,f"… {len(results)-200} more failures not shown. Download CSV for full list.",ln=True)

                pdf_bytes = bytes(pdf.output())

            st.download_button(
                label="⬇ Download PDF Report",
                data=pdf_bytes,
                file_name="IFC_Validation_Report.pdf",
                mime="application/pdf",
                use_container_width=False,
            )
            st.success("✅ PDF ready! Click the button above to download.")

        # Quick stats preview
        st.markdown("---")
        st.markdown("**Report will include:**")
        st.markdown("""
        - Validation summary (total checks, pass rate, health score)
        - Failure count by severity and category
        - Full failure table with Rule ID, severity, element name, IFC type and message
        - Up to 200 rows inline; full list available via CSV download
        """)