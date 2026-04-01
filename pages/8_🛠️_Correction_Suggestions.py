import streamlit as st
import ifcopenshell
import pandas as pd
from fpdf import FPDF

st.set_page_config(
    page_title="Correction Suggestions",
    page_icon="🛠️",
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
if not an:
    st.warning("⚠️ No analysis data found. Please upload and analyze an IFC file on the **Home** page first.")
    st.stop()


def _schema_supports_class(ifc_model, class_name: str) -> bool:
    """Return True when class_name exists in the active IFC schema."""
    try:
        ifc_model.by_type(class_name)
        return True
    except Exception:
        return False


ACTIVE_SCHEMA = getattr(model, "schema", "Unknown") or "Unknown"

# ══════════════════════════════════════════════════════════════════════════════
# CORRECTION ENGINE
# For each detected issue, generate a specific, actionable suggestion
# ══════════════════════════════════════════════════════════════════════════════

def get_suggested_type(name: str, current_type: str) -> str:
    """Guess the single best IFC type from the element name. Returns None if no strong match."""
    n = (name or "").lower()
    # Structural
    if any(k in n for k in ["wall", "wand", "mur", "muur"]):                  return "IfcWall"
    if any(k in n for k in ["door", "tur", "porte", "deur"]):                 return "IfcDoor"
    if any(k in n for k in ["window", "fenster", "fenetre", "raam"]):         return "IfcWindow"
    if any(k in n for k in ["slab", "floor", "dalle", "platte"]):             return "IfcSlab"
    if any(k in n for k in ["column", "col", "stutze", "pilier", "pillar"]):  return "IfcColumn"
    if any(k in n for k in ["beam", "trager", "poutre", "balk", "girder"]):   return "IfcBeam"
    if any(k in n for k in ["stair", "treppe", "escalier", "step"]):          return "IfcStair"
    if any(k in n for k in ["roof", "dach", "toit", "dak"]):                  return "IfcRoof"
    if any(k in n for k in ["rail", "gelander", "garde", "handrail"]):        return "IfcRailing"
    # Energy generation
    if any(k in n for k in ["solar", "photovoltaic", "pv panel", "solar panel", "pv module"]): return "IfcSolarDevice"
    # Heating appliances
    if any(k in n for k in ["fireplace", "fire place", "fire hang", "hearth", "space heater", "radiator"]): return "IfcSpaceHeater"
    # MEP — pipes (water without glass/cup context = pipe)
    if any(k in n for k in ["pipe", "rohr", "tuyau", "drain", "plumb"]):      return "IfcPipeSegment"
    if "water" in n and not any(k in n for k in ["glass", "cup", "bottle", "jug", "mug"]): return "IfcPipeSegment"
    if any(k in n for k in ["fitting", "elbow", "tee", "coupling"]):          return "IfcPipeFitting"
    if any(k in n for k in ["duct", "kanal", "gaine", "hvac"]):               return "IfcFlowSegment"
    # Cooking appliances → IfcCookingAppliance
    if any(k in n for k in ["cooktop", "cook top", "oven", "hob", "stove"]):
        return "IfcCookingAppliance"
    # Electric appliances → IfcElectricAppliance
    if any(k in n for k in [
        "microwave", "fridge", "freezer", "refrigerator",
        "dishwasher", "dish washer", "washing machine", "washing",
        "tumble dryer", "dryer", "appliance",
    ]):
        return "IfcElectricAppliance"
    # Rangehood / extraction → IfcFlowTerminal (acceptable)
    if any(k in n for k in ["rangehood", "range hood", "extractor"]):
        return "IfcFlowTerminal"
    # Sanitary terminals
    if any(k in n for k in [
        "toilet", "sink", "basin", "bath", "shower", "sanit",
        "terminal", "outlet", "inlet", "diffuser", "grille",
    ]):
        return "IfcFlowTerminal"
    # Electrical
    if any(k in n for k in ["light", "lamp", "luminaire", "fixture"]):        return "IfcLightFixture"
    if any(k in n for k in ["electric", "cable", "wire", "switch", "socket", "panel"]): return "IfcElectricalElement"
    # Mechanical
    if any(k in n for k in ["pump", "fan", "motor", "compressor", "boiler", "chiller"]): return "IfcMechanicalEquipment"
    if any(k in n for k in ["heater", "cooler", "exchanger", "condenser"]):   return "IfcEnergyConversionDevice"
    # Site / Landscape
    if any(k in n for k in ["tree", "plant", "shrub", "bush", "hedge", "grass"]): return "IfcPlant"
    if any(k in n for k in ["site", "terrain", "ground", "earth"]):           return "IfcSite"
    # Glassware / tableware → IfcFurnishingElement
    if any(k in n for k in ["water glass", "glass", "cup", "mug", "jug"]):    return "IfcFurnishingElement"
    # Furniture
    if any(k in n for k in ["chair", "table", "desk", "sofa", "bed", "cabinet",
                              "shelf", "furn", "seat", "bench", "wardrobe"]):  return "IfcFurnishingElement"
    # No strong match — ask user
    return None

# Classes that are too generic/vague — never auto-suggest these
GENERIC_CLASSES = {"IfcDistributionElement", "IfcBuildingElement", "IfcElement"}

# ── Smart multi-suggestion engine ─────────────────────────────────────────────
_SMART_RULES = [
    # (keywords, ifc_class, human-readable reason)
    (["solar","photovoltaic","pv panel","solar panel","pv module"],
        "IfcSolarDevice",          "Photovoltaic / solar energy device — best match"),
    (["fireplace","fire place","fire hang","hearth"],
        "IfcSpaceHeater",          "Fireplace / heating appliance → IfcSpaceHeater"),
    (["space heater","radiator"],
        "IfcSpaceHeater",          "Space heater / radiator → IfcSpaceHeater"),
    (["cooktop","cook top","oven","hob","stove"],
        "IfcCookingAppliance",     "Cooking appliance — best IFC class for hobs/ovens"),
    (["microwave","fridge","freezer","refrigerator","dishwasher","dish washer",
       "washing machine","washing","tumble dryer","dryer"],
        "IfcElectricAppliance",    "Electric domestic appliance — best IFC class"),
    (["rangehood","range hood","extractor"],
        "IfcFlowTerminal",         "Rangehood / extraction — IfcFlowTerminal (acceptable)"),
    (["water glass","glass","cup","mug","jug"],
        "IfcFurnishingElement",    "Glassware / tableware → IfcFurnishingElement"),
    (["wall","wand","mur"],        "IfcWall",                "Structural wall element"),
    (["door","tur","porte"],       "IfcDoor",                "Door element"),
    (["window","fenster"],         "IfcWindow",              "Window element"),
    (["slab","floor","dalle"],     "IfcSlab",                "Floor / slab element"),
    (["beam","trager","girder"],   "IfcBeam",                "Structural beam / girder"),
    (["column","col","pillar"],    "IfcColumn",              "Structural column"),
    (["stair","step"],             "IfcStair",               "Stair element"),
    (["roof","dach"],              "IfcRoof",                "Roof element"),
    (["pipe","rohr","drain","plumb"], "IfcPipeSegment",      "Pipe / plumbing segment"),
    (["water"],                    "IfcPipeSegment",         "Water system — pipe assumed (safe default)"),
    (["duct","hvac"],              "IfcFlowSegment",         "HVAC duct segment"),
    (["light","lamp","luminaire"], "IfcLightFixture",        "Lighting fixture"),
    (["electric","switch","socket"],"IfcElectricalElement",  "Electrical device"),
    (["pump","fan","motor","boiler","chiller"], "IfcMechanicalEquipment", "Mechanical equipment"),
    (["heater","cooler","exchanger"],"IfcEnergyConversionDevice","Energy conversion device"),
    (["tree","plant","shrub","bush","hedge"], "IfcPlant",    "Landscape planting element"),
    (["chair","table","desk","sofa","bed","furn","cabinet","shelf","wardrobe"],
        "IfcFurnishingElement",    "Furniture / furnishing element"),
    (["toilet","sink","basin","bath","shower"], "IfcFlowTerminal", "Sanitary terminal"),
    (["terminal","outlet","inlet","diffuser"],  "IfcFlowTerminal", "Flow terminal / endpoint"),
]

def get_smart_suggestions(name: str) -> list:
    """
    Return top-5 (IFC class, score 0-100, reason) tuples for this element name.
    Best match first.  Score 97 = exact/leading match, 92 = strong hit, 78 = partial match.
    """
    n = (name or "").lower()
    seen    = {}  # class → best score
    reasons = {}  # class → reason

    for keywords, cls, reason in _SMART_RULES:
        for kw in keywords:
            if kw in n:
                if n == kw or n.startswith(kw + " ") or n.startswith(kw + ":"):
                    score = 97   # exact / leading match
                elif " " + kw in n or ":" + kw in n:
                    score = 92   # strong interior match
                else:
                    score = 78   # partial / substring match

                # Confidence penalty: if another class already scored higher
                # for this name, this class scores at most 5 pts below the best.
                current_best = max(seen.values()) if seen else 0
                if score >= current_best and cls not in seen:
                    # First class to claim this score — allow it
                    pass
                elif cls in seen and score <= seen[cls]:
                    continue  # already have a better score for this class

                # If a different class already holds 97, cap newcomers at 92
                other_best = max((v for c, v in seen.items() if c != cls), default=0)
                if other_best == 97 and score == 97:
                    score = 92

                if score > seen.get(cls, -1):
                    seen[cls]    = score
                    reasons[cls] = reason

    ranked = sorted(seen.items(), key=lambda x: -x[1])[:5]
    return [(cls, score, reasons[cls]) for cls, score in ranked]

def confidence_score(name: str, suggested: str) -> int:
    """Return 0-100 confidence that the suggestion is correct."""
    if not suggested or suggested in GENERIC_CLASSES:
        return 0
    n = (name or "").lower()
    exact_map = {
        "IfcWall":                ["wall","wand","mur"],
        "IfcDoor":                ["door","tur","porte"],
        "IfcWindow":              ["window","fenster"],
        "IfcSlab":                ["slab","floor","dalle"],
        "IfcColumn":              ["column","col","stütze"],
        "IfcBeam":                ["beam","träger","poutre","girder"],
        "IfcStair":               ["stair","treppe"],
        "IfcRoof":                ["roof","dach"],
        "IfcFurnishingElement":   ["chair","table","desk","sofa","bed","furn"],
        "IfcPipeSegment":         ["pipe","water","drain","plumb"],
        "IfcFlowSegment":         ["duct","hvac"],
        "IfcCookingAppliance":    ["cooktop","cook top","oven","hob","stove"],
        "IfcElectricAppliance":   ["microwave","fridge","freezer","refrigerator","dishwasher","washing","dryer"],
        "IfcFlowTerminal":        ["terminal","outlet","rangehood","toilet","sink","basin","bath","shower"],
        "IfcLightFixture":        ["light","lamp","luminaire"],
        "IfcMechanicalEquipment": ["pump","fan","motor","compressor","boiler","chiller"],
    }
    keywords = exact_map.get(suggested, [])
    if any(k in n for k in keywords): return 97
    # Unknown/generic name — low confidence, do NOT auto-apply
    if not n or n in ("unnamed", "generic model", "object", "element", "component", "model"): return 20
    return 60

def pset_suggestions(ifc_type: str) -> list:
    """Return recommended Psets for a given IFC type."""
    pset_map = {
        "IfcWall":    ["Pset_WallCommon",    "Pset_ConcreteElementGeneral"],
        "IfcDoor":    ["Pset_DoorCommon",    "Pset_DoorWindowGlazingType"],
        "IfcWindow":  ["Pset_WindowCommon",  "Pset_DoorWindowGlazingType"],
        "IfcSlab":    ["Pset_SlabCommon",    "Pset_ConcreteElementGeneral"],
        "IfcColumn":  ["Pset_ColumnCommon",  "Pset_ConcreteElementGeneral"],
        "IfcBeam":    ["Pset_BeamCommon",    "Pset_ConcreteElementGeneral"],
        "IfcStair":   ["Pset_StairCommon"],
        "IfcRoof":    ["Pset_RoofCommon"],
        "IfcRailing": ["Pset_RailingCommon"],
    }
    return pset_map.get(ifc_type, ["Pset_BuildingElementCommon"])

def ifc_correction_steps(current: str, suggested: str) -> str:
    """Return IFC file edit instruction."""
    return (
        f"In the IFC file, locate the entity `#{current}` and change "
        f"`{current}` -> `{suggested}`. "
        f"Ensure the ObjectType and PredefinedType attributes are updated accordingly."
    )

# ── Build correction list ──────────────────────────────────────────────────────
corrections = []

# ── Valid / reference proxies — DO NOT CHANGE these ──────────────────────────
# Non-engineering elements: entourage, RPC people/cars, décor, vessels
VALID_PROXY_KEYWORDS_CS = [
    "rpc", "entourage", "geo", "georeference", "geo-reference", "survey", "origin", "basepoint",
    "car", "vehicle", "truck", "bus", "people", "person", "human", "pedestrian",
    # Décor & vessels — non-engineering, keep as IfcBuildingElementProxy or IfcFurnishingElement
    "vase", "bottle", "plate", "decor", "decoration", "ornament", "art", "sculpture",
    "pot", "bowl", "jar", "planter", "flower", "wine",
]
def is_valid_reference_proxy(name):
    n = (name or "").lower()
    return any(k in n for k in VALID_PROXY_KEYWORDS_CS)

# 1. Proxy element corrections — enforce rules from correction guide
for item in an.get("proxy_list", []):
    name = item["Name"]
    gid  = item["GlobalId"]

    # Rule: Valid reference proxies (décor, entourage, RPC) — DO NOT CHANGE
    if is_valid_reference_proxy(name):
        continue

    suggested = get_suggested_type(name, "IfcBuildingElementProxy")
    conf      = confidence_score(name, suggested) if suggested else 0

    # Rule: Generic/vague class suggestion — DO NOT USE, ask user instead
    if suggested in GENERIC_CLASSES:
        suggested = None
        conf      = 0

    # Rule: skip suggestions that are not available in current schema (e.g. IFC2X3 vs IFC4).
    if suggested and not _schema_supports_class(model, suggested):
        suggested = None
        conf      = 0

    # Rule: Low confidence (<60%) — do NOT auto-apply, ask user / show options
    if conf < 60 or not suggested:
        corrections.append({
            "GlobalId":        gid,
            "Element Name":    name,
            "Current Type":    "IfcBuildingElementProxy",
            "Suggested Type":  "—",
            "Confidence":      conf,
            "Issue":           "Unknown proxy — unclear element type",
            "Action":          "⚠️ No auto-fix. Select IFC class manually.",
            "Add Psets":       "—",
            "IFC Edit":        "Select the correct IFC class manually in the Interactive Correction Engine.",
            "category":        "proxy",
            "warn":            "low_confidence",
        })
    else:
        psets = pset_suggestions(suggested)
        corrections.append({
            "GlobalId":        gid,
            "Element Name":    name,
            "Current Type":    "IfcBuildingElementProxy",
            "Suggested Type":  suggested,
            "Confidence":      conf,
            "Issue":           "Generic proxy — semantic type lost",
            "Action":          f"Reclassify to {suggested}",
            "Add Psets":       ", ".join(psets),
            "IFC Edit":        ifc_correction_steps("IfcBuildingElementProxy", suggested),
            "category":        "proxy",
            "warn":            None,
        })

# 2. Elements missing required Pset corrections
for item in an.get("missing_pset_list", []):
    name      = item.get("Element Name") or item.get("Wall Name") or "Unnamed"
    gid       = item.get("GlobalId", "")
    ifc_type  = item.get("IFC Type", "IfcWall")
    req_pset  = item.get("Required Pset") or item.get("Issue", "Pset_WallCommon missing").replace(" missing","")
    corrections.append({
        "GlobalId":       gid,
        "Element Name":   name,
        "Current Type":   ifc_type,
        "Suggested Type": ifc_type,
        "Confidence":     100,
        "Issue":          f"Missing {req_pset}",
        "Action":         f"Add {req_pset} with required properties",
        "Add Psets":      req_pset,
        "IFC Edit":       f"Add a new IfcPropertySet named '{req_pset}' and link via IfcRelDefinesByProperties.",
        "category":       "missing_pset",
    })

# 3. Quantity loss corrections
for item in an.get("qty_loss_list", []):
    corrections.append({
        "GlobalId":       item.get("GlobalId",""),
        "Element Name":   item.get("Name","Unnamed"),
        "Current Type":   item.get("IFC Type",""),
        "Suggested Type": item.get("IFC Type",""),
        "Confidence":     100,
        "Issue":          item.get("Issue","Missing IfcElementQuantity"),
        "Action":         "Add IfcElementQuantity (BaseQuantities) with area, volume, length",
        "Add Psets":      "IfcElementQuantity (BaseQuantities)",
        "IFC Edit":       "Add IfcElementQuantity linked via IfcRelDefinesByProperties.",
        "category":       "quantity_loss",
    })

# 4. Relationship loss corrections
for item in an.get("rel_loss_list", []):
    issue = item.get("Issue","")
    if "storey" in issue.lower():
        action = "Assign element to correct IfcBuildingStorey via IfcRelContainedInSpatialStructure"
        ifc_edit = "Create IfcRelContainedInSpatialStructure linking this element to its storey."
    else:
        action = "Host door/window in wall opening via IfcRelFillsElement"
        ifc_edit = "Create IfcRelFillsElement linking this door/window to its wall opening."
    corrections.append({
        "GlobalId":       item.get("GlobalId",""),
        "Element Name":   item.get("Name","Unnamed"),
        "Current Type":   item.get("IFC Type",""),
        "Suggested Type": item.get("IFC Type",""),
        "Confidence":     100,
        "Issue":          issue,
        "Action":         action,
        "Add Psets":      "—",
        "IFC Edit":       ifc_edit,
        "category":       "relationship_loss",
    })

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛠️ Correction Summary")
    proxy_fixes   = sum(1 for c in corrections if c["category"] == "proxy")
    pset_fixes_s  = sum(1 for c in corrections if c["category"] == "missing_pset")
    qty_fixes     = sum(1 for c in corrections if c["category"] == "quantity_loss")
    rel_fixes     = sum(1 for c in corrections if c["category"] == "relationship_loss")
    high_conf     = sum(1 for c in corrections if c["Confidence"] >= 80)
    med_conf      = sum(1 for c in corrections if 50 <= c["Confidence"] < 80)
    low_conf      = sum(1 for c in corrections if c["Confidence"] < 50)

    st.metric("Total Suggestions",        len(corrections))
    st.metric("🔴 Proxy Reclassifications", proxy_fixes)
    st.metric("🟠 Pset Additions",          pset_fixes_s)
    st.metric("📐 Quantity Loss",           qty_fixes)
    st.metric("🔗 Relationship Loss",       rel_fixes)
    st.markdown("---")
    st.markdown("**Confidence Breakdown**")
    st.markdown(f"🟢 High (≥80%)     : **{high_conf}**")
    st.markdown(f"🟡 Medium (50–79%) : **{med_conf}**")
    st.markdown(f"🔴 Low (<50%)      : **{low_conf}**")

# ── Page header ────────────────────────────────────────────────────────────────
st.title("🛠️ Automated Correction Suggestions")
st.caption(
    "For every detected semantic issue, the system recommends the correct IFC classification "
    "and missing property sets — with confidence scores and step-by-step fix instructions."
)

if not corrections:
    st.success("✅ No issues detected — your IFC model is semantically clean!")
    st.stop()

# ── Top summary cards ──────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Issues",             len(corrections))
col2.metric("Proxy Reclassifications",  proxy_fixes)
col3.metric("Missing Pset Fixes",       pset_fixes_s)
col4.metric("Quantity Loss",            qty_fixes)
col5.metric("Relationship Loss",        rel_fixes)

st.markdown("---")

# ── Filter bar ─────────────────────────────────────────────────────────────────
st.subheader("🔍 Filter & Explore Suggestions")
fcol1, fcol2, fcol3 = st.columns(3)
with fcol1:
    filter_type = st.selectbox("Issue Type", ["All","Proxy Reclassification","Missing Pset","Quantity Loss","Relationship Loss"])
with fcol2:
    filter_conf = st.selectbox("Confidence", ["All","High (≥80%)","Medium (50–79%)","Low (<50%)"])
with fcol3:
    search_term = st.text_input("Search by name or GlobalId", placeholder="e.g. Wall_001 or 0A3...")

# Apply filters
filtered = corrections[:]
if filter_type == "Proxy Reclassification":  filtered = [c for c in filtered if c["category"]=="proxy"]
elif filter_type == "Missing Pset":          filtered = [c for c in filtered if c["category"]=="missing_pset"]
elif filter_type == "Quantity Loss":         filtered = [c for c in filtered if c["category"]=="quantity_loss"]
elif filter_type == "Relationship Loss":     filtered = [c for c in filtered if c["category"]=="relationship_loss"]

if filter_conf == "High (≥80%)":
    filtered = [c for c in filtered if c["Confidence"] >= 80]
elif filter_conf == "Medium (50–79%)":
    filtered = [c for c in filtered if 50 <= c["Confidence"] < 80]
elif filter_conf == "Low (<50%)":
    filtered = [c for c in filtered if c["Confidence"] < 50]

if search_term:
    s = search_term.lower()
    filtered = [c for c in filtered if s in c["Element Name"].lower() or s in c["GlobalId"].lower()]

st.caption(f"Showing **{len(filtered)}** of **{len(corrections)}** suggestions")

# ── Main table ─────────────────────────────────────────────────────────────────
st.subheader("📋 Correction Table")

if filtered:
    display_df = pd.DataFrame([{
        "Element Name":   c["Element Name"],
        "GlobalId":       c["GlobalId"],
        "Current Type":   c["Current Type"],
        "Suggested Type": c["Suggested Type"],
        "Confidence %":   c["Confidence"],
        "Issue":          c["Issue"],
        "Action":         c["Action"],
        "Add Psets":      c["Add Psets"],
    } for c in filtered])

    # Colour-code confidence with pandas Styler
    def colour_conf(val):
        if val >= 80:   return "background-color:#1a3a1a;color:#66cc66"
        elif val >= 50: return "background-color:#3a3a1a;color:#cccc66"
        else:           return "background-color:#3a1a1a;color:#cc6666"

    try:
        styled = display_df.style.map(colour_conf, subset=["Confidence %"])
    except AttributeError:
        styled = display_df.style.applymap(colour_conf, subset=["Confidence %"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("No suggestions match the current filters.")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE IFC CORRECTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🔧 Interactive IFC Correction Engine")

IFC_CLASSES = [
    "— Select IFC Class —",
    # Structural
    "IfcWall", "IfcDoor", "IfcWindow", "IfcSlab", "IfcRoof",
    "IfcBeam", "IfcColumn", "IfcStair", "IfcRailing",
    # Furnishing
    "IfcFurnishingElement",
    # Appliances
    "IfcCookingAppliance", "IfcElectricAppliance",
    # Energy
    "IfcSolarDevice", "IfcSpaceHeater",
    # MEP — specific classes only (IfcDistributionElement removed — too vague)
    "IfcPipeSegment", "IfcPipeFitting", "IfcFlowTerminal", "IfcFlowSegment",
    "IfcMechanicalEquipment", "IfcEnergyConversionDevice",
    "IfcElectricalElement", "IfcLightFixture",
    # Site / Landscape
    "IfcPlant", "IfcSite",
    "Keep as reference — no class needed",
]

# Allow only classes that exist in the active schema to avoid invalid IFC output.
IFC_CLASSES = [
    c for c in IFC_CLASSES
    if c in ("— Select IFC Class —", "Keep as reference — no class needed")
    or _schema_supports_class(model, c)
]

proxy_corrections    = [c for c in corrections if c["category"] == "proxy"]
pset_corrections     = [c for c in corrections if c["category"] == "missing_pset"]
qty_corrections      = [c for c in corrections if c["category"] == "quantity_loss"]
rel_corrections      = [c for c in corrections if c["category"] == "relationship_loss"]

if "user_class_selections" not in st.session_state: st.session_state.user_class_selections = {}
if "applied_fixes"          not in st.session_state: st.session_state.applied_fixes = set()
if "pset_fixes"             not in st.session_state: st.session_state.pset_fixes = {}
if "removed_proxies"        not in st.session_state: st.session_state.removed_proxies = set()
if "pset_class_selections"  not in st.session_state: st.session_state.pset_class_selections = {}

eng_tab1, eng_tab2, eng_tab3, eng_tab4 = st.tabs([
    f"🔴 Proxy Reclassification ({len(proxy_corrections)})",
    f"🟠 Pset Addition ({len(pset_corrections)})",
    f"📐 Quantity Loss ({len(qty_corrections)})",
    f"🔗 Relationship Loss ({len(rel_corrections)})",
])

# ── TAB 1: PROXY RECLASSIFICATION ─────────────────────────────────────────────
with eng_tab1:
    if not proxy_corrections:
        st.success("✅ No proxy elements to correct.")
    else:
        st.caption("Review each proxy element, confirm or change the suggested IFC class, then apply fixes.")
        col_aa, col_ra, col_info_aa = st.columns([1, 1, 2])
        with col_aa:
            if st.button("⚡ Apply All Suggestions", use_container_width=True, type="primary", key="apply_all_proxy"):
                skipped = 0
                for c in proxy_corrections:
                    gid  = c["GlobalId"]
                    sug  = c["Suggested Type"]
                    conf = c["Confidence"]
                    # Rule: do NOT auto-apply low-confidence or no-suggestion items
                    if conf < 60 or not sug or sug == "—" or sug not in IFC_CLASSES:
                        skipped += 1
                        continue
                    st.session_state.user_class_selections[gid] = sug
                    st.session_state.applied_fixes.add(gid)
                    st.session_state.removed_proxies.discard(gid)
                if skipped:
                    st.toast(f"⚠️ {skipped} low-confidence items skipped — review manually.", icon="⚠️")
                st.rerun()
        with col_ra:
            if st.button("🗑️ Remove All Suggestions", use_container_width=True, key="remove_all_proxy"):
                for c in proxy_corrections:
                    gid = c["GlobalId"]
                    st.session_state.removed_proxies.add(gid)
                    st.session_state.applied_fixes.discard(gid)
                    if gid in st.session_state.user_class_selections:
                        del st.session_state.user_class_selections[gid]
                st.rerun()
        with col_info_aa:
            applied_count = len([g for g in st.session_state.applied_fixes
                                  if g not in st.session_state.removed_proxies])
            removed_count = len(st.session_state.removed_proxies)
            removed_suffix = f"  ·  <strong style='color:#da3633;'>{removed_count}</strong> removed" if removed_count else ""
            st.markdown(
                f"<div style='padding:8px 14px;background:#161b22;border:1px solid #30363d;"
                f"<strong style='color:#e6edf3;'>{applied_count}</strong> / "
                f"{len(proxy_corrections)} elements corrected"
                f"{removed_suffix}"
                f"</div>",
                unsafe_allow_html=True
            )
        st.markdown("<br>", unsafe_allow_html=True)

        for c in proxy_corrections:
            gid        = c["GlobalId"]
            name       = c["Element Name"]
            suggested  = c["Suggested Type"]
            conf       = c["Confidence"]
            is_applied = gid in st.session_state.applied_fixes
            is_removed = gid in st.session_state.removed_proxies

            warn        = c.get("warn")
            badge_col   = "#238636" if conf >= 80 else "#d29922" if conf >= 60 else "#da3633"
            badge_lbl   = "HIGH" if conf >= 80 else "MEDIUM" if conf >= 60 else "⚠️ LOW — CHOOSE MANUALLY"
            card_border = "#8b949e" if is_removed else "#238636" if is_applied else ("#d29922" if warn == "low_confidence" else "#30363d")
            card_bg     = "#1a1a2a" if is_removed else "#0d2a0d" if is_applied else ("#1a1500" if warn == "low_confidence" else "#161b22")

            st.markdown(
                f'<div style="background:{card_bg};border:1px solid {card_border};'
                f'border-radius:10px;padding:14px 18px;margin-bottom:10px;">',
                unsafe_allow_html=True
            )
            r1, r2, r3, r4 = st.columns([3, 2, 3, 1])
            with r1:
                st.markdown("**Element**")
                st.markdown(
                    f"<span style='color:#e6edf3;font-size:13px;font-weight:600;'>{name}</span><br>"
                    f"<span style='color:#8b949e;font-size:11px;font-family:monospace;'>{gid[:24]}…</span>",
                    unsafe_allow_html=True
                )
            with r2:
                st.markdown("**Current Class**")
                st.markdown(
                    "<span style='background:#da363322;color:#ff6b6b;border:1px solid #da3633;"
                    "border-radius:4px;padding:2px 8px;font-size:11px;'>"
                    "IfcBuildingElementProxy</span>",
                    unsafe_allow_html=True
                )
            with r3:
                # ── Smart suggestions (top 3–5) ───────────────────────────
                smart = [s for s in get_smart_suggestions(name) if _schema_supports_class(model, s[0])]
                if smart:
                    best_cls, best_score, best_reason = smart[0]
                    hint_col  = "#238636" if best_score >= 90 else "#d29922" if best_score >= 75 else "#da3633"
                    hint_lbl  = "BEST MATCH" if best_score >= 90 else "LIKELY" if best_score >= 75 else "POSSIBLE"
                    st.markdown(
                        f"<div style='margin-bottom:6px;'>"
                        f"<span style='font-size:11px;font-weight:700;color:#8b949e;'>💡 SMART SUGGESTIONS</span></div>",
                        unsafe_allow_html=True
                    )
                    for i, (cls, score, reason) in enumerate(smart):
                        is_best = i == 0
                        sc = "#238636" if score >= 90 else "#d29922" if score >= 75 else "#8b949e"
                        lbl = "⭐ Best" if is_best else f"#{i+1}"
                        st.markdown(
                            f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:3px;'>"
                            f"<span style='background:{sc}22;color:{sc};border:1px solid {sc};"
                            f"border-radius:3px;padding:0 5px;font-size:10px;font-weight:700;"
                            f"white-space:nowrap;'>{lbl}</span>"
                            f"<span style='font-size:12px;font-weight:{'700' if is_best else '400'};"
                            f"color:{'#e6edf3' if is_best else '#c9d1d9'};'>{cls}</span>"
                            f"<span style='font-size:10px;color:#8b949e;'>({score}%)</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    # One-click apply best suggestion button
                    if st.button(f"✅ Apply Best: {smart[0][0]}", key=f"best_{gid}",
                                 use_container_width=True):
                        st.session_state.user_class_selections[gid] = smart[0][0]
                        st.session_state.applied_fixes.add(gid)
                        st.session_state.removed_proxies.discard(gid)
                        st.rerun()
                else:
                    st.markdown(
                        "<span style='font-size:11px;color:#8b949e;'>⚠️ No smart suggestion — choose manually below</span>",
                        unsafe_allow_html=True
                    )

                # ── Advanced: show all classes toggle ─────────────────────
                show_all = st.toggle("Show all IFC classes", key=f"show_all_{gid}", value=False)
                if show_all:
                    current_sel = st.session_state.user_class_selections.get(gid, "— Select IFC Class —")
                    default_idx = IFC_CLASSES.index(current_sel) if current_sel in IFC_CLASSES else 0
                    chosen = st.selectbox(f"class_{gid}", IFC_CLASSES, index=default_idx,
                                          key=f"sel_{gid}", label_visibility="collapsed")
                    if chosen == "Keep as reference — no class needed":
                        st.session_state.removed_proxies.add(gid)
                        if gid in st.session_state.applied_fixes:
                            st.session_state.applied_fixes.discard(gid)
                        if gid in st.session_state.user_class_selections:
                            del st.session_state.user_class_selections[gid]
                    elif chosen != "— Select IFC Class —":
                        st.session_state.user_class_selections[gid] = chosen
                        st.session_state.removed_proxies.discard(gid)
                else:
                    # Hidden — keep session state in sync without rendering selectbox
                    chosen = st.session_state.user_class_selections.get(gid, "— Select IFC Class —")
            with r4:
                st.markdown("**Action**")
                if is_applied and not is_removed:
                    # After fix applied — show Remove
                    if st.button("🗑️ Remove", key=f"fix_{gid}", use_container_width=True):
                        st.session_state.applied_fixes.discard(gid)
                        st.session_state.removed_proxies.add(gid)
                        if gid in st.session_state.user_class_selections:
                            del st.session_state.user_class_selections[gid]
                        st.rerun()
                elif is_removed:
                    # After removed — show Apply to re-apply
                    apply_disabled = chosen == "— Select IFC Class —"
                    if st.button("✅ Apply", key=f"fix_{gid}", use_container_width=True,
                                 disabled=apply_disabled):
                        if chosen not in ("— Select IFC Class —", "Keep as reference — no class needed"):
                            st.session_state.applied_fixes.add(gid)
                            st.session_state.removed_proxies.discard(gid)
                            st.session_state.user_class_selections[gid] = chosen
                            st.rerun()
                else:
                    # Default — show Apply (disabled until a class is chosen)
                    apply_disabled = chosen == "— Select IFC Class —"
                    if st.button("✅ Apply", key=f"fix_{gid}", use_container_width=True,
                                 disabled=apply_disabled):
                        if chosen not in ("— Select IFC Class —", "Keep as reference — no class needed"):
                            st.session_state.applied_fixes.add(gid)
                            st.session_state.user_class_selections[gid] = chosen
                            st.rerun()
                    # Warn if low confidence — user must manually pick
                    if warn == "low_confidence" and chosen == "— Select IFC Class —":
                        st.markdown(
                            "<div style='font-size:10px;color:#d29922;margin-top:3px;'>"
                            "⚠️ Select a class manually</div>",
                            unsafe_allow_html=True
                        )
            st.markdown("</div>", unsafe_allow_html=True)

# ── TAB 2: PSET ADDITION ──────────────────────────────────────────────────────
with eng_tab2:
    # Map IFC class → its standard required pset
    PSET_FOR_CLASS = {
        "IfcWall":                   "Pset_WallCommon",
        "IfcWallStandardCase":       "Pset_WallCommon",
        "IfcDoor":                   "Pset_DoorCommon",
        "IfcWindow":                 "Pset_WindowCommon",
        "IfcSlab":                   "Pset_SlabCommon",
        "IfcColumn":                 "Pset_ColumnCommon",
        "IfcBeam":                   "Pset_BeamCommon",
        "IfcRoof":                   "Pset_RoofCommon",
        "IfcStair":                  "Pset_StairCommon",
        "IfcRailing":                "Pset_RailingCommon",
        "IfcPipeSegment":            "Pset_PipeSegmentTypeCommon",
        "IfcPipeFitting":            "Pset_PipeFittingTypeCommon",
        "IfcFlowSegment":            "Pset_FlowSegmentTypeCommon",
        "IfcFlowTerminal":           "Pset_FlowTerminalTypeCommon",
        "IfcCookingAppliance":       "Pset_CookingApplianceTypeCommon",
        "IfcElectricAppliance":      "Pset_ElectricApplianceTypeCommon",
        "IfcMechanicalEquipment":    "Pset_ManufacturerTypeInformation",
        "IfcEnergyConversionDevice": "Pset_EnergyConversionDeviceCommon",
        "IfcElectricalElement":      "Pset_ElectricalDeviceCommon",
        "IfcLightFixture":           "Pset_LightFixtureTypeCommon",
        "IfcDistributionElement":    "Pset_DistributionSystemCommon",
        "IfcPlant":                  "Pset_PlantCommon",
        "IfcFurnishingElement":      "Pset_BuildingElementCommon",
    }
    PSET_FOR_CLASS = {
        _cls: _ps for _cls, _ps in PSET_FOR_CLASS.items()
        if _schema_supports_class(model, _cls)
    }
    PSET_IFC_CLASSES = ["— Select IFC Class —"] + sorted(PSET_FOR_CLASS.keys())

    if not pset_corrections:
        st.success("✅ All elements have their required property sets.")
    else:
        st.caption(
            f"{len(pset_corrections)} elements are missing a Pset. "
            "Select the correct IFC class for each element — the required Pset will be shown automatically."
        )
        pa1, pa2 = st.columns(2)
        with pa1:
            if st.button("📦 Apply All Pset Fixes", use_container_width=True, type="primary", key="queue_all_psets"):
                applied_count = 0
                for c in pset_corrections:
                    gid = c["GlobalId"]
                    if not gid:
                        continue
                    # Use user-selected class if available, else fall back to current type
                    chosen_class = st.session_state.pset_class_selections.get(gid, c["Current Type"])
                    req_pset = PSET_FOR_CLASS.get(chosen_class)
                    if req_pset:
                        st.session_state.pset_fixes[gid] = {
                            "GlobalId": gid, "IFCType": chosen_class,
                            "PsetName": req_pset, "Name": c["Element Name"],
                        }
                        applied_count += 1
                st.success(f"✅ {applied_count} Pset fixes applied — click Validate Now to preview, then Download.")
        with pa2:
            if st.button("🗑️ Remove All Pset Fixes", use_container_width=True, key="remove_all_psets"):
                st.session_state.pset_fixes.clear()
                st.session_state.pset_class_selections.clear()
                st.rerun()

        pset_queued = set(st.session_state.pset_fixes.keys())
        for c in pset_corrections[:200]:
            gid        = c["GlobalId"]
            is_applied = gid in pset_queued
            cur_type   = c["Current Type"]

            # Resolve which class is selected for this element
            chosen_class = st.session_state.pset_class_selections.get(gid, cur_type)
            resolved_pset = PSET_FOR_CLASS.get(chosen_class)

            bc   = "#0d1a30" if is_applied else "#161b22"
            bord = "#58a6ff" if is_applied else "#30363d"
            st.markdown(
                f'<div style="background:{bc};border:1px solid {bord};border-radius:10px;'
                f'padding:12px 16px;margin-bottom:8px;">',
                unsafe_allow_html=True
            )
            row1, row2 = st.columns([4, 1])
            with row1:
                st.markdown(
                    f"<span style='color:#e6edf3;font-weight:600;font-size:14px;'>{c['Element Name']}</span>"
                    f"<span style='color:#8b949e;font-size:11px;margin-left:10px;font-family:monospace;'>"
                    f"{gid[:24]}…</span>",
                    unsafe_allow_html=True
                )
            with row2:
                # Apply / Remove button
                if is_applied:
                    if st.button("🗑️ Remove", key=f"pset_q_{gid}", use_container_width=True):
                        del st.session_state.pset_fixes[gid]
                        st.rerun()
                else:
                    apply_disabled = resolved_pset is None
                    if st.button("✅ Apply", key=f"pset_q_{gid}", use_container_width=True,
                                 disabled=apply_disabled):
                        st.session_state.pset_fixes[gid] = {
                            "GlobalId": gid, "IFCType": chosen_class,
                            "PsetName": resolved_pset, "Name": c["Element Name"],
                        }
                        st.rerun()

            # Row 2: IFC class selector + resolved pset display
            sel1, sel2 = st.columns([2, 2])
            with sel1:
                st.markdown("<span style='font-size:11px;color:#8b949e;'>IFC Class</span>", unsafe_allow_html=True)
                default_idx = PSET_IFC_CLASSES.index(chosen_class) if chosen_class in PSET_IFC_CLASSES else 0
                new_class = st.selectbox(
                    f"ifc_class_pset_{gid}", PSET_IFC_CLASSES,
                    index=default_idx, key=f"pset_cls_{gid}",
                    label_visibility="collapsed"
                )
                if new_class != "— Select IFC Class —":
                    st.session_state.pset_class_selections[gid] = new_class
                elif gid in st.session_state.pset_class_selections:
                    del st.session_state.pset_class_selections[gid]

            with sel2:
                st.markdown("<span style='font-size:11px;color:#8b949e;'>Required Pset</span>", unsafe_allow_html=True)
                display_pset = PSET_FOR_CLASS.get(new_class) if new_class != "— Select IFC Class —" else None
                if display_pset:
                    st.markdown(
                        f"<div style='background:#d2992222;color:#d29922;border:1px solid #d29922;"
                        f"border-radius:6px;padding:6px 10px;font-size:12px;margin-top:2px;'>"
                        f"📦 {display_pset}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div style='background:#21262d;color:#8b949e;border:1px solid #30363d;"
                        "border-radius:6px;padding:6px 10px;font-size:12px;margin-top:2px;'>"
                        "Select a class to see the required Pset</div>",
                        unsafe_allow_html=True
                    )

            if is_applied:
                applied_pset = st.session_state.pset_fixes[gid].get("PsetName","")
                st.markdown(
                    f"<div style='font-size:11px;color:#58a6ff;margin-top:4px;'>"
                    f"✅ Applied: {applied_pset}</div>",
                    unsafe_allow_html=True
                )

            st.markdown("</div>", unsafe_allow_html=True)

        if len(pset_corrections) > 200:
            st.info(f"Showing first 200 of {len(pset_corrections)}. Use 'Apply All' to fix all at once.")
        pset_total_queued = len(st.session_state.pset_fixes)
        if pset_total_queued:
            st.markdown(
                f"<div style='background:#0d1a30;border:1px solid #58a6ff;border-radius:8px;"
                f"padding:10px 16px;margin-top:8px;font-size:13px;color:#79c0ff;'>"
                f"📦 <strong>{pset_total_queued} Pset fixes applied</strong> — included in Validate preview and injected on Download.</div>",
                unsafe_allow_html=True
            )

# ── TAB 3: QUANTITY LOSS ──────────────────────────────────────────────────────
with eng_tab3:
    if not qty_corrections:
        st.success("✅ All elements have quantity data (IfcElementQuantity).")
    else:
        st.caption(
            f"{len(qty_corrections)} elements missing IfcElementQuantity. "
            "Quantity data (area, volume, length) is required for BOQ, cost estimation and energy analysis."
        )
        st.info(
            "**How to fix:** In your authoring tool, ensure 'Export Quantities' / 'Base Quantities' is enabled "
            "in the IFC export settings. In Revit: IFC Export → Additional Content → Export Base Quantities ✓. "
            "In ArchiCAD: IFC Translator → Geometry → Export IFC Base Quantities ✓."
        )
        st.dataframe(pd.DataFrame([{
            "Element Name": c["Element Name"],
            "IFC Type":     c["Current Type"],
            "Issue":        c["Issue"],
            "Fix":          c["Action"],
            "GlobalId":     c["GlobalId"][:22]+"…",
        } for c in qty_corrections[:300]]), use_container_width=True, hide_index=True, height=400)
        if len(qty_corrections) > 300:
            st.info(f"Showing first 300 of {len(qty_corrections)}.")

# ── TAB 4: RELATIONSHIP LOSS ──────────────────────────────────────────────────
with eng_tab4:
    if not rel_corrections:
        st.success("✅ No relationship data loss detected.")
    else:
        st.caption(f"{len(rel_corrections)} elements with missing or broken IFC relationships.")

        # Group by issue type
        storey_issues = [c for c in rel_corrections if "storey" in c["Issue"].lower()]
        host_issues   = [c for c in rel_corrections if "hosted" in c["Issue"].lower() or "wall" in c["Issue"].lower()]

        rel_type_groups = {}
        for c in rel_corrections:
            key = c["Issue"]
            rel_type_groups.setdefault(key, []).append(c)

        for issue_label, items in rel_type_groups.items():
            # Case 1 vs Case 2 distinction
            # Case 1: No such element type exists at all in model
            # Case 2: Element exists but relationship is missing
            with st.expander(f"🔗 **{issue_label}** — {len(items)} element(s)", expanded=True):
                st.caption(f"**Case 2: Element exists but relationship is missing** ({len(items)} elements) — the element is present in the IFC file but not linked to its required spatial/host structure.")
                if "storey" in issue_label.lower():
                    st.markdown(
                        "**How to fix:** In your authoring tool, ensure each element is placed on a level/storey. "
                        "In Revit: select element → Properties → Level → assign correct level. "
                        "Re-export with 'Include Spatial Container' enabled in IFC settings."
                    )
                elif "hosted" in issue_label.lower() or "wall" in issue_label.lower():
                    st.markdown(
                        "**How to fix:** In Revit/ArchiCAD, ensure doors and windows are placed inside walls "
                        "as hosted components, not as standalone objects."
                    )
                st.dataframe(pd.DataFrame([{
                    "Element Name": c["Element Name"],
                    "IFC Type":     c["Current Type"],
                    "GlobalId":     c["GlobalId"][:22]+"…",
                    "Fix":          c["Action"],
                } for c in items[:200]]), use_container_width=True, hide_index=True)
                if len(items) > 200:
                    st.info(f"Showing first 200 of {len(items)}.")

# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD CORRECTED IFC — outside all tabs, always visible
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📥 Download Corrected IFC")

applied_ids  = st.session_state.get("applied_fixes", set())
removed_ids  = st.session_state.get("removed_proxies", set())
pset_fixes_q = st.session_state.get("pset_fixes", {})
total_actions = len(applied_ids) + len(pset_fixes_q)

if total_actions == 0:
    st.info("Apply proxy fixes (Tab 1) or queue Pset fixes (Tab 2) above, then download the corrected file.")
else:
    proxy_reclassify_count = len(applied_ids)
    pset_inject_count      = len(pset_fixes_q)
    st.markdown(
        f"<div style='background:#0d1a30;border:1px solid #58a6ff;border-radius:10px;"
        f"padding:14px 20px;margin-bottom:12px;display:flex;gap:24px;flex-wrap:wrap;'>"
        f"<div><div style='font-size:10px;color:#8b949e;'>PROXY FIXES</div>"
        f"<div style='font-size:22px;font-weight:800;color:#58a6ff;'>{proxy_reclassify_count}</div></div>"
        f"<div><div style='font-size:10px;color:#8b949e;'>PSET INJECTIONS</div>"
        f"<div style='font-size:22px;font-weight:800;color:#d29922;'>{pset_inject_count}</div></div>"
        f"<div style='flex:1;font-size:12px;color:#8b949e;align-self:center;'>"
        f"GlobalId · Placement · Existing Relationships all preserved — only class and Psets change.</div>"
        f"</div>",
        unsafe_allow_html=True
    )
    st.markdown("""
<div style="background:#1a1200;border:1px solid #d29922;border-radius:8px;padding:12px 16px;margin-bottom:10px;font-size:12px;">
  <strong style="color:#d29922;">⚠️ What changes and what stays the same</strong><br>
  <span style="color:#c9d1d9;">
  ✅ <strong>Changed:</strong> IFC class keyword only (e.g. IFCBUILDINGELEMENTPROXY → IFCFLOWTERMINAL)<br>
  ✅ <strong>Added:</strong> New Pset entities and their IfcRelDefinesByProperties link<br>
  ❌ <strong>NOT changed:</strong> Materials — existing material assignments (IfcMaterialLayerSet, IfcMaterialConstituentSet, etc.) are fully preserved<br>
  ❌ <strong>NOT changed:</strong> Geometry, placement, name, GlobalId, relationships, any other data<br><br>
  💡 <strong>If Version Comparison shows elements as "Removed":</strong> Those elements (IfcDistributionPort, IfcMember, IfcBuildingStorey, etc.) were 
  present in Version A but not scanned by the comparison (it only scans IfcProduct entities with geometry). 
  They still exist in the corrected file — the comparison is not showing data loss.
  </span>
</div>""", unsafe_allow_html=True)

# ── Helper: build corrected IFC text in memory ─────────────────────────
# Pset definitions — what properties to inject per IFC type
PSET_DEFINITIONS = {
    # ── Structural ────────────────────────────────────────────────────
    "IfcWall": {
        "pset_name": "Pset_WallCommon",
        "props": [
            ("IsExternal",           "IFCBOOLEAN(.F.)"),
            ("LoadBearing",          "IFCBOOLEAN(.F.)"),
            ("FireRating",           "IFCLABEL('')"),
            ("AcousticRating",       "IFCLABEL('')"),
            ("ThermalTransmittance", "IFCTHERMALTRANSMITTANCEMEASURE(0)"),
            ("ExtendToStructure",    "IFCBOOLEAN(.F.)"),
        ],
    },
    "IfcDoor": {
        "pset_name": "Pset_DoorCommon",
        "props": [
            ("FireRating",        "IFCLABEL('')"),
            ("AcousticRating",    "IFCLABEL('')"),
            ("IsExternal",        "IFCBOOLEAN(.F.)"),
            ("HandicapAccessible","IFCBOOLEAN(.F.)"),
        ],
    },
    "IfcWindow": {
        "pset_name": "Pset_WindowCommon",
        "props": [
            ("FireRating",           "IFCLABEL('')"),
            ("AcousticRating",       "IFCLABEL('')"),
            ("IsExternal",           "IFCBOOLEAN(.T.)"),
            ("ThermalTransmittance", "IFCTHERMALTRANSMITTANCEMEASURE(0)"),
        ],
    },
    "IfcSlab": {
        "pset_name": "Pset_SlabCommon",
        "props": [
            ("LoadBearing",  "IFCBOOLEAN(.T.)"),
            ("IsExternal",   "IFCBOOLEAN(.F.)"),
            ("FireRating",   "IFCLABEL('')"),
            ("PitchAngle",   "IFCPLANEANGLEMEASURE(0)"),
        ],
    },
    "IfcColumn": {
        "pset_name": "Pset_ColumnCommon",
        "props": [
            ("LoadBearing",  "IFCBOOLEAN(.T.)"),
            ("IsExternal",   "IFCBOOLEAN(.F.)"),
            ("FireRating",   "IFCLABEL('')"),
        ],
    },
    "IfcBeam": {
        "pset_name": "Pset_BeamCommon",
        "props": [
            ("LoadBearing",  "IFCBOOLEAN(.T.)"),
            ("IsExternal",   "IFCBOOLEAN(.F.)"),
            ("FireRating",   "IFCLABEL('')"),
            ("Span",         "IFCPOSITIVELENGTHMEASURE(0)"),
        ],
    },
    "IfcRoof": {
        "pset_name": "Pset_RoofCommon",
        "props": [
            ("FireRating",   "IFCLABEL('')"),
            ("IsExternal",   "IFCBOOLEAN(.T.)"),
        ],
    },
    "IfcStair": {
        "pset_name": "Pset_StairCommon",
        "props": [
            ("FireRating",        "IFCLABEL('')"),
            ("HandicapAccessible","IFCBOOLEAN(.F.)"),
            ("NumberOfRiser",     "IFCINTEGER(0)"),
            ("NumberOfTreads",    "IFCINTEGER(0)"),
        ],
    },
    "IfcRailing": {
        "pset_name": "Pset_RailingCommon",
        "props": [
            ("IsExternal",   "IFCBOOLEAN(.F.)"),
        ],
    },
    # ── MEP / Plumbing ────────────────────────────────────────────────
    "IfcPipeSegment": {
        "pset_name": "Pset_PipeSegmentTypeCommon",
        "props": [
            ("Status",           "IFCLABEL('NEW')"),
            ("NominalDiameter",  "IFCPOSITIVELENGTHMEASURE(0)"),
            ("NominalLength",    "IFCPOSITIVELENGTHMEASURE(0)"),
            ("WorkingPressure",  "IFCPRESSSUREMEASURE(0)"),
        ],
    },
    "IfcPipeFitting": {
        "pset_name": "Pset_PipeFittingTypeCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
            ("NominalDiameter", "IFCPOSITIVELENGTHMEASURE(0)"),
            ("WorkingPressure", "IFCPRESSSUREMEASURE(0)"),
        ],
    },
    "IfcFlowSegment": {
        "pset_name": "Pset_FlowSegmentTypeCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
            ("NominalLength",   "IFCPOSITIVELENGTHMEASURE(0)"),
        ],
    },
    "IfcFlowTerminal": {
        "pset_name": "Pset_FlowTerminalTypeCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
        ],
    },
    # ── Mechanical / Electrical ───────────────────────────────────────
    "IfcMechanicalEquipment": {
        "pset_name": "Pset_ManufacturerTypeInformation",
        "props": [
            ("Manufacturer",       "IFCLABEL('')"),
            ("ModelLabel",         "IFCLABEL('')"),
            ("ProductionYear",     "IFCLABEL('')"),
            ("NominalPower",       "IFCPOWERMEASURE(0)"),
        ],
    },
    "IfcEnergyConversionDevice": {
        "pset_name": "Pset_EnergyConversionDeviceCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
        ],
    },
    "IfcElectricalElement": {
        "pset_name": "Pset_ElectricalDeviceCommon",
        "props": [
            ("Status",              "IFCLABEL('NEW')"),
            ("NominalVoltage",      "IFCELECTRICVOLTAGEMEASURE(0)"),
            ("NominalFrequency",    "IFCFREQUENCYMEASURE(0)"),
        ],
    },
    "IfcLightFixture": {
        "pset_name": "Pset_LightFixtureTypeCommon",
        "props": [
            ("Status",              "IFCLABEL('NEW')"),
            ("LightFixtureType",    "IFCLABEL('POINTSOURCE')"),
            ("NumberOfSources",     "IFCINTEGER(1)"),
        ],
    },
    # ── Distribution ──────────────────────────────────────────────────
    "IfcDistributionElement": {
        "pset_name": "Pset_DistributionSystemCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
        ],
    },
    # ── Landscape / Site ──────────────────────────────────────────────
    "IfcPlant": {
        "pset_name": "Pset_PlantCommon",
        "props": [
            ("Status",          "IFCLABEL('NEW')"),
        ],
    },
    "IfcSite": {
        "pset_name": "Pset_SiteCommon",
        "props": [
            ("BuildableArea",       "IFCAREAMEASURE(0)"),
            ("TotalArea",           "IFCAREAMEASURE(0)"),
            ("SiteLandTitleNumber", "IFCLABEL('')"),
        ],
    },
}

# Material defaults per IFC type
MATERIAL_DEFAULTS = {
    "IfcWall":       "Concrete",
    "IfcSlab":       "Concrete",
    "IfcColumn":     "Concrete",
    "IfcBeam":       "Steel",
    "IfcRoof":       "Concrete",
    "IfcStair":      "Concrete",
    "IfcDoor":       "Wood",
    "IfcWindow":     "Aluminium",
    "IfcRailing":    "Steel",
    "IfcPipeSegment":"Steel",
    "IfcPipeFitting":"Steel",
    "IfcFlowSegment":"Steel",
    "IfcFlowTerminal":"Aluminium",
    "IfcCookingAppliance":"Steel",
    "IfcElectricAppliance":"Steel",
    "IfcLightFixture":"Aluminium",
    "IfcElectricalElement":"Copper",
    "IfcMechanicalEquipment":"Steel",
    "IfcEnergyConversionDevice":"Steel",
    "IfcDistributionElement":"Steel",
    "IfcPlant":"Organic",
}

def build_corrected_ifc(selections):
    import re as _re, uuid as _uuid
    with open("temp.ifc", "r", encoding="utf-8", errors="replace") as _f:
        ifc_text = _f.read()
    fix_log  = []
    skip_log = []
    new_entities = []  # all new IFC entities to append before ENDSEC

    # ── Find next available entity # ──────────────────────────────────
    all_ids  = _re.findall(r"^#(\d+)=", ifc_text, _re.MULTILINE)
    next_id  = max(int(i) for i in all_ids) + 1 if all_ids else 9000

    def nid():
        nonlocal next_id
        n = next_id; next_id += 1; return n

    # ── Find OwnerHistory ref ─────────────────────────────────────────
    oh_m      = _re.search(r"(#\d+)=\s*IFCOWNERHISTORY\(", ifc_text, _re.IGNORECASE)
    owner_ref = oh_m.group(1) if oh_m else "$"

    def _inject_pset(elem_ref, ifc_type, pset_name_override=None):
        """Inject the standard Pset for an ifc_type linked to elem_ref.
        Skips injection if a pset with the same name already exists for this element
        — prevents adding wrong/duplicate psets."""
        pdef = PSET_DEFINITIONS.get(ifc_type)
        if not pdef:
            return None
        pname = pset_name_override or pdef["pset_name"]

        # Rule: DO NOT ADD if a pset with this name already exists anywhere in the file
        # (prevents adding e.g. Pset_DistributionSystemCommon to a vase reclassified as IfcFlowTerminal)
        if f"'{pname}'" in ifc_text:
            return None  # already present — skip

        prop_refs = []
        for prop_name, prop_val in pdef["props"]:
            pid = nid()
            new_entities.append(
                f"#{pid}= IFCPROPERTYSINGLEVALUE('{prop_name}',$,{prop_val},$);"
            )
            prop_refs.append(f"#{pid}")
        ps_id  = nid()
        rel_id = nid()
        pg = _uuid.uuid4().hex[:22].upper()
        rg = _uuid.uuid4().hex[:22].upper()
        new_entities.append(
            f"#{ps_id}= IFCPROPERTYSET('{pg}',{owner_ref},'{pname}',$,"
            f"({','.join(prop_refs)}));"
        )
        new_entities.append(
            f"#{rel_id}= IFCRELDEFINESBYPROPERTIES('{rg}',{owner_ref},$,$,"
            f"({elem_ref}),#{ps_id});"
        )
        return pname

    def _inject_material(elem_ref, ifc_type):
        """Inject a default material ONLY if the element has absolutely NO existing material
        assignment of any kind. Handles single-line and multi-line IFC entities.
        Rule: NEVER change or remove existing materials — only ADD if truly absent."""
        import re as _re2

        # Strategy: check ALL IfcRelAssociatesMaterial blocks (may span multiple lines)
        # Use DOTALL so . matches newlines
        rel_mat_blocks = _re2.findall(
            r"IFCRELASSOCIATESMATERIAL\s*\([^;]*?\)\s*;",
            ifc_text, _re2.IGNORECASE | _re2.DOTALL
        )
        escaped_ref = _re2.escape(elem_ref)
        for block in rel_mat_blocks:
            # Check if this element's ref # appears in the RelatedObjects list of this block
            if _re2.search(r'\b' + escaped_ref + r'\b', block, _re2.IGNORECASE):
                return None  # already has a material — do NOT touch it

        # Also check IfcMaterialLayerSetUsage and IfcMaterialProfileSetUsage
        # which can be linked directly via IfcRelAssociatesMaterial
        # (belt-and-suspenders check for complex wall/slab layer sets)
        layer_blocks = _re2.findall(
            r"IFCMATERIALLAYERSETUSAGE\s*\([^;]*?\)\s*;|"
            r"IFCMATERIALPROFILESETUSAGE\s*\([^;]*?\)\s*;|"
            r"IFCMATERIALCONSTITUENTSET\s*\([^;]*?\)\s*;",
            ifc_text, _re2.IGNORECASE | _re2.DOTALL
        )
        # If any of these exist and are linked to our element via any rel, skip injection
        # Simpler: if the element already has a rel_mat, we caught it above.
        # This check is just for files where material is embedded differently.
        # Safe to skip injection if any complex material type is present in the file
        # for this element type — walls, slabs, columns usually always have layer sets.
        COMPLEX_MATERIAL_TYPES = {
            "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcColumn",
            "IfcBeam", "IfcRoof", "IfcWindow", "IfcDoor",
        }
        if ifc_type in COMPLEX_MATERIAL_TYPES and layer_blocks:
            # Complex material structures present — don't risk overwriting, skip
            return None

        mat_name = MATERIAL_DEFAULTS.get(ifc_type)
        if not mat_name:
            return None
        mat_id  = nid()
        matl_id = nid()
        matg    = _uuid.uuid4().hex[:22].upper()
        new_entities.append(f"#{mat_id}= IFCMATERIAL('{mat_name}',$,$);")
        new_entities.append(
            f"#{matl_id}= IFCRELASSOCIATESMATERIAL('{matg}',{owner_ref},$,$,"
            f"({elem_ref}),#{mat_id});"
        )
        return mat_name

    # ══════════════════════════════════════════════════════════════════
    # PASS A — Proxy reclassification
    #
    # Critical rules (Fix #2 & #3):
    #   • MODIFY existing element — NEVER delete or recreate it
    #   • Only swap the IFC class keyword in-place; ALL other attributes
    #     (Name, Description, ObjectType, Placement, Representation,
    #      Tag, GlobalId) stay byte-for-byte identical
    #   • Relationships are NEVER touched:
    #       IfcRelContainedInSpatialStructure  (storey assignment)
    #       IfcRelDefinesByProperties          (existing Psets)
    #       IfcRelAssociatesMaterial           (existing materials)
    #       IfcRelConnectsElements             (element connections)
    #       IfcRelFillsElement                 (door/window hosting)
    #   • New Pset and Material are ADDED (appended) — never overwritten
    # ══════════════════════════════════════════════════════════════════

    # Safety guard: relationship entity names — we must NEVER alter lines for these
    _PROTECTED_PREFIXES = (
        "IFCRELCONTAINEDINSPATIALSTRUCTURE",
        "IFCRELDEFINESBYPROPERTIES",
        "IFCRELASSOCIATESMATERIAL",
        "IFCRELCONNECTSELEMENTS",
        "IFCRELFILLSELEMENT",
        "IFCRELAGGREGATES",
    )

    for _gid, _new_type in selections.items():
        if not _new_type or _new_type in ("IfcBuildingElementProxy", "— Select IFC Class —"):
            skip_log.append(f"Skipped: {_gid[:22]}")
            continue

        if not _schema_supports_class(model, _new_type):
            skip_log.append(f"Schema {ACTIVE_SCHEMA} does not support {_new_type}: {_gid[:22]}")
            continue

        _new_upper = _new_type.upper()
        _escaped   = _re.escape(_gid)

        # Match ONLY the proxy entity line — pattern anchored to the opening paren
        # so relationship lines that happen to reference this GUID are NEVER changed.
        # Pattern: #NNN= IFCBUILDINGELEMENTPROXY('<GUID>'
        _pat = rf"(#\d+=\s*)IFCBUILDINGELEMENTPROXY(\(\s*'{_escaped}')"

        # Verify the match line is NOT a relationship line (belt-and-suspenders)
        _candidate = _re.search(_pat, ifc_text, _re.IGNORECASE)
        if not _candidate:
            skip_log.append(f"Not found in IFC: {_gid[:22]}")
            continue
        _matched_line = ifc_text[max(0, _candidate.start()-5):_candidate.end()+10].upper()
        if any(_matched_line.lstrip("#0123456789= ").startswith(p) for p in _PROTECTED_PREFIXES):
            skip_log.append(f"Protected relationship — skipped: {_gid[:22]}")
            continue

        # Perform class-name swap — only the keyword changes, nothing else
        _new_txt, _n = _re.subn(_pat, rf"\g<1>{_new_upper}\g<2>",
                                 ifc_text, flags=_re.IGNORECASE)
        if _n == 0:
            skip_log.append(f"Swap failed: {_gid[:22]}")
            continue
        ifc_text = _new_txt

        # Find the element ref in the updated text
        em = _re.search(rf"(#\d+)=\s*{_new_upper}\(\s*'{_escaped}'",
                        ifc_text, _re.IGNORECASE)
        elem_ref = em.group(1) if em else None
        if not elem_ref:
            fix_log.append((_gid, _new_type, None, None))
            continue

        # Inject NEW pset and material — existing relationships are untouched
        pset_name = _inject_pset(elem_ref, _new_type)
        mat_name  = _inject_material(elem_ref, _new_type)
        fix_log.append((_gid, _new_type, pset_name, mat_name))


    # ══════════════════════════════════════════════════════════════════
    # PASS B — Pset injection for already-typed elements (AI pset fixes)
    # These are elements that are already e.g. IfcBeam/IfcWall/IfcRoof
    # but are missing their required Pset
    # ══════════════════════════════════════════════════════════════════
    pset_fixes = st.session_state.get("pset_fixes", {})
    pset_fix_log = []
    # Skip any GIDs already handled in Pass A (they got Psets injected above)
    already_fixed = set(selections.keys())
    for _gid, pfix in pset_fixes.items():
        if _gid in already_fixed:
            continue
        ifc_type = pfix.get("IFCType","")
        req_pset = pfix.get("PsetName","")
        if not ifc_type or not req_pset:
            continue
        _escaped   = _re.escape(_gid)
        _ifc_upper = ifc_type.upper()
        # Find entity ref for this element
        em = _re.search(
            rf"(#\d+)=\s*{_ifc_upper}\(\s*'{_escaped}'",
            ifc_text, _re.IGNORECASE
        )
        if not em:
            continue
        elem_ref = em.group(1)
        pset_name = _inject_pset(elem_ref, ifc_type, pset_name_override=req_pset)
        if pset_name:
            pset_fix_log.append((_gid, ifc_type, pset_name))

    # ══════════════════════════════════════════════════════════════════
    # Append all new entities before ENDSEC
    # ══════════════════════════════════════════════════════════════════
    if new_entities:
        block    = chr(10).join(new_entities) + chr(10)
        _endsec  = "ENDSEC;" + chr(10) + "END-ISO-10303-21;"
        ifc_text = _re.sub(
            r"ENDSEC;\s*END-ISO-10303-21;",
            block + _endsec,
            ifc_text
        )

    return ifc_text, fix_log, skip_log, pset_fix_log

# ── VALIDATE NOW — preview score before download ───────────────────────
if st.button("🔍 Validate Now — Preview Improved Score", use_container_width=True):
    with st.spinner("Applying fixes in memory and calculating new score..."):
        try:
            import tempfile, os, re as _re

            # Build corrected text
            selections = {
                gid: st.session_state.user_class_selections.get(gid, "IfcBuildingElementProxy")
                for gid in applied_ids
            }
            ifc_text_corrected, fix_log_v, skip_log_v, pset_fix_log_v = build_corrected_ifc(selections)

            # Write to a temp file so ifcopenshell can parse it
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".ifc",
                encoding="utf-8", delete=False
            ) as _tmp:
                _tmp.write(ifc_text_corrected)
                _tmp_path = _tmp.name

            # Parse corrected model
            corrected_model = ifcopenshell.open(_tmp_path)
            os.unlink(_tmp_path)

            # Count elements
            SKIP = {
                "IfcSpace","IfcOpeningElement","IfcVirtualElement","IfcAnnotation",
                "IfcGrid","IfcSite","IfcBuilding","IfcBuildingStorey","IfcProject",
                "IfcRelAggregates","IfcZone","IfcSpatialZone",
            }
            new_proxies    = len(corrected_model.by_type("IfcBuildingElementProxy"))
            all_elems      = [e for e in corrected_model.by_type("IfcProduct") if e.is_a() not in SKIP]
            new_total      = len(all_elems)
            new_proxy_pct  = new_proxies / new_total * 100 if new_total else 0
            new_sem_pct    = 100 - new_proxy_pct

            # Pset score aligned with Home.py: coverage among elements that REQUIRE a standard Pset
            ELEM_PSET_MAP_V = {
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
                "IfcCookingAppliance":       "Pset_CookingApplianceTypeCommon",
                "IfcElectricAppliance":      "Pset_ElectricApplianceTypeCommon",
                "IfcMechanicalEquipment":   "Pset_ManufacturerTypeInformation",
                "IfcEnergyConversionDevice": "Pset_EnergyConversionDeviceCommon",
                "IfcElectricalElement":     "Pset_ElectricalDeviceCommon",
                "IfcLightFixture":          "Pset_LightFixtureTypeCommon",
                "IfcDistributionElement":   "Pset_DistributionSystemCommon",
                "IfcPlant":                 "Pset_PlantCommon",
            }
            elems_with_pset = 0
            missing_req_pset = 0
            for _e in all_elems:
                _etype = _e.is_a()
                _req_pset = ELEM_PSET_MAP_V.get(_etype)
                if not _req_pset:
                    elems_with_pset += 1
                    continue

                _has_req = False
                for _d in getattr(_e, "IsDefinedBy", []):
                    if _d.is_a("IfcRelDefinesByProperties"):
                        _ps = _d.RelatingPropertyDefinition
                        if _ps and _ps.is_a("IfcPropertySet") and _ps.Name == _req_pset:
                            _has_req = True
                            break

                if _has_req:
                    elems_with_pset += 1
                else:
                    missing_req_pset += 1

            # Score
            _sem_score   = new_sem_pct / 100 * 60
            _proxy_score = new_proxy_pct / 100 * 30
            elems_requiring_pset = elems_with_pset + missing_req_pset
            _pset_score  = (elems_with_pset / elems_requiring_pset * 40) if elems_requiring_pset else 40
            new_score    = round(min(100, max(0, _sem_score - _proxy_score + _pset_score)), 1)

            if   new_score >= 85: new_grade, new_col = "Excellent", "#238636"
            elif new_score >= 70: new_grade, new_col = "Good",      "#1f6feb"
            elif new_score >= 50: new_grade, new_col = "Fair",      "#d29922"
            else:                 new_grade, new_col = "Poor",      "#da3633"

            # Current score
            cur_score = an.get("quality_score", 0)
            cur_col   = an.get("quality_color", "#8b949e")
            cur_grade = an.get("quality_grade", "—")
            delta     = round(new_score - cur_score, 1)
            delta_col = "#238636" if delta > 0 else "#da3633"

            # Display result
            st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;margin-top:8px;">
  <div style="font-size:12px;color:#8b949e;letter-spacing:1px;margin-bottom:14px;text-transform:uppercase;">
Score Preview — Before vs After Correction
  </div>
  <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;">
<div style="flex:1;min-width:140px;background:{cur_col}18;border:1.5px solid {cur_col};
border-radius:10px;padding:14px;text-align:center;">
  <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">BEFORE</div>
  <div style="font-size:32px;font-weight:800;color:{cur_col};">{cur_score}</div>
  <div style="font-size:12px;color:{cur_col};">{cur_grade}</div>
  <div style="font-size:11px;color:#8b949e;margin-top:4px;">{an.get('proxy_elements',0)} proxies</div>
</div>
<div style="display:flex;align-items:center;font-size:28px;color:#8b949e;">→</div>
<div style="flex:1;min-width:140px;background:{new_col}18;border:1.5px solid {new_col};
border-radius:10px;padding:14px;text-align:center;">
  <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">AFTER</div>
  <div style="font-size:32px;font-weight:800;color:{new_col};">{new_score}</div>
  <div style="font-size:12px;color:{new_col};">{new_grade}</div>
  <div style="font-size:11px;color:#8b949e;margin-top:4px;">{new_proxies} proxies remaining</div>
</div>
<div style="flex:1;min-width:140px;background:{delta_col}18;border:1.5px solid {delta_col};
border-radius:10px;padding:14px;text-align:center;">
  <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">IMPROVEMENT</div>
  <div style="font-size:32px;font-weight:800;color:{delta_col};">{"+" if delta>0 else ""}{delta}</div>
  <div style="font-size:12px;color:{delta_col};">points gained</div>
  <div style="font-size:11px;color:#8b949e;margin-top:4px;">
{len(fix_log_v)} proxy fixes · {sum(1 for f in fix_log_v if f[2])} with Psets · {sum(1 for f in fix_log_v if f[3])} with Materials · {len(pset_fix_log_v)} standalone Pset fixes
  </div>
</div>
  </div>
  <div style="font-size:12px;color:#8b949e;border-top:1px solid #30363d;padding-top:10px;">
✅ Preserved: GlobalId · ObjectPlacement · Representation · IfcRelContainedInSpatialStructure (storey) · IfcRelConnectsElements · IfcRelFillsElement<br>
✅ Added: IfcRelDefinesByProperties (Pset) · IfcRelAssociatesMaterial (Material)
  </div>
</div>""", unsafe_allow_html=True)

            # Store corrected bytes in session for download
            st.session_state["corrected_ifc_bytes"] = ifc_text_corrected.encode("utf-8")
            st.session_state["corrected_fix_count"] = len(fix_log_v)
            st.session_state["corrected_pset_count"] = len(pset_fix_log_v)

        except Exception as _e:
            st.error(f"Validation error: {_e}")

# ── Pset fix banner ───────────────────────────────────────────────────
pset_fixes_queued = st.session_state.get("pset_fixes", {})
if pset_fixes_queued:
    st.markdown(
        f"<div style='background:#0d1a30;border:1px solid #58a6ff;border-radius:8px;"
        f"padding:10px 16px;margin-bottom:12px;font-size:13px;color:#79c0ff;'>"
        f"📦 <strong>{len(pset_fixes_queued)} Pset fixes</strong> queued — "
        f"included in Validate preview and injected into the corrected IFC on download.</div>",
        unsafe_allow_html=True
    )

# ── Download (uses pre-validated bytes if available) ───────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("📥 Generate & Download Corrected IFC", use_container_width=True):
    # Always build fresh from current selections so download cannot become stale.
    selections = {
        gid: st.session_state.user_class_selections.get(gid, "IfcBuildingElementProxy")
        for gid in applied_ids
    }
    ifc_text_dl, fix_log_dl, skip_log_dl, pset_fix_log_dl = build_corrected_ifc(selections)
    ifc_bytes  = ifc_text_dl.encode("utf-8")
    fix_count  = len(fix_log_dl)
    pset_count = len(pset_fix_log_dl)
    if skip_log_dl:
        with st.expander(f"⚠️ {len(skip_log_dl)} skipped"):
            for _l in skip_log_dl:
                st.markdown(f"- {_l}")

    st.download_button(
        label="⬇️ Download Corrected IFC File",
        data=ifc_bytes,
        file_name="corrected_model.ifc",
        mime="application/octet-stream",
        use_container_width=True,
    )
    st.success(f"✅ {fix_count} elements reclassified + {pset_count} Psets injected — IFC class + Psets + Material added. Upload to Home page to confirm score.")

# ── Export correction report (PDF) ───────────────────────────────────────────
st.subheader("⬇️ Export Correction Report")

if st.button("📄 Download PDF Report"):

    def safe(text):
        """Remove characters that latin-1 (FPDF default) cannot encode."""
        return (str(text)
                .replace("\u2014", "-")   # em dash
                .replace("\u2013", "-")   # en dash
                .replace("\u2019", "'")   # right single quote
                .replace("\u2018", "'")   # left single quote
                .replace("\u201c", '"')   # left double quote
                .replace("\u201d", '"')   # right double quote
                .replace("\u2192", "->")  # arrow →
                .replace("\u2190", "<-")  # arrow ←
                .encode("latin-1", errors="replace").decode("latin-1"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "IFC Correction Suggestions Report", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", size=11)
    ctx = st.session_state.get("user_context", {})
    pdf.multi_cell(0, 7, safe(f"Role: {ctx.get('role','N/A')}  |  Domain: {ctx.get('domain','N/A')}  |  Purpose: {ctx.get('purpose','N/A')}"))
    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, safe(f"Total Suggestions: {len(corrections)}  |  Proxy: {proxy_fixes}  |  Missing Pset: {pset_fixes_s}"), ln=True)
    pdf.ln(4)
    for i, c in enumerate(corrections, 1):
        pdf.set_font("Arial", "B", 11)
        pdf.multi_cell(0, 7, safe(f"{i}. {c['Element Name']} ({c['Current Type']})"))
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, safe(f"   GlobalId   : {c['GlobalId']}"))
        pdf.multi_cell(0, 6, safe(f"   Issue      : {c['Issue']}"))
        pdf.multi_cell(0, 6, safe(f"   Suggestion : {c['Suggested Type']}"))
        pdf.multi_cell(0, 6, safe(f"   Confidence : {c['Confidence']}%"))
        pdf.multi_cell(0, 6, safe(f"   Add Psets  : {c['Add Psets']}"))
        pdf.multi_cell(0, 6, safe(f"   Fix        : {c['IFC Edit']}"))
        pdf.ln(3)
    path = "IFC_Correction_Suggestions.pdf"
    pdf.output(path)
    with open(path, "rb") as f:
        st.download_button(
            label="⬇️ Click to download PDF",
            data=f,
            file_name="IFC_Correction_Suggestions.pdf",
            mime="application/pdf",
        )