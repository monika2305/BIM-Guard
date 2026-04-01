import streamlit as st
import ifcopenshell
import json
import datetime
import uuid
import zipfile
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="BCF Generator", page_icon="📋", layout="wide")

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
[data-testid="stExpander"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px !important; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background:#161b22 !important; border:1px solid #30363d !important; color:#e6edf3 !important; border-radius:6px !important; }
[data-baseweb="select"] > div { background:#161b22 !important; border:1px solid #30363d !important; }
[data-baseweb="select"] span { color:#e6edf3 !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background:#161b22 !important; }
[data-baseweb="popover"] li, [data-baseweb="menu"] li { color:#e6edf3 !important; }
[data-testid="stCheckbox"] label { color:#e6edf3 !important; }
div[data-testid="stNumberInput"] input { background:#161b22 !important; border:1px solid #30363d !important; color:#e6edf3 !important; }
::-webkit-scrollbar { width:6px; } ::-webkit-scrollbar-thumb { background:#30363d; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ── Guards ─────────────────────────────────────────────────────────────────────
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

# ══════════════════════════════════════════════════════════════════════════════
# BCF GENERATION ENGINE
# BCF 2.1 format: a .bcfzip containing:
#   bcf.version      — version manifest
#   project.bcfp     — project info
#   <topic-uuid>/    — one folder per issue
#       markup.bcf   — issue metadata, comments, viewpoints list
#       viewpoint.bcfv — camera + component selection
# ══════════════════════════════════════════════════════════════════════════════

BCF_VERSION   = "2.1"
BCF_NS        = "http://www.buildingsmart-tech.org/XMLschemas/BCF/2.1/bcf.xsd"

PRIORITY_MAP = {
    "Critical": "Critical",
    "Major":    "Major",
    "Normal":   "Normal",
    "Minor":    "Minor",
}

STATUS_MAP = {
    "Open":        "Open",
    "In Progress": "InProgress",
    "Resolved":    "Resolved",
    "Closed":      "Closed",
}

ISSUE_TYPES = ["Issue", "Request", "Clash", "Remark", "Error"]

def pretty_xml(elem):
    """Return indented XML string from an ElementTree element."""
    rough = ET.tostring(elem, encoding="unicode")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding=None).replace('<?xml version="1.0" ?>\n', '')

def make_bcf_version():
    root = ET.Element("Version", VersionId=BCF_VERSION)
    ET.SubElement(root, "DetailedVersion").text = BCF_VERSION
    return pretty_xml(root)

def make_project_bcfp(project_name, project_id):
    root = ET.Element("ProjectExtension")
    proj = ET.SubElement(root, "Project", ProjectId=project_id)
    ET.SubElement(proj, "Name").text = project_name
    ET.SubElement(root, "ExtensionSchema").text = ""
    return pretty_xml(root)

def make_markup(topic):
    """
    topic dict keys:
        guid, type, status, priority, title, description,
        author, assigned_to, creation_date, modified_date,
        stage, labels, comments, related_guids
    """
    root = ET.Element("Markup")

    # Header — IFC file reference
    header = ET.SubElement(root, "Header")
    file_el = ET.SubElement(header, "File", IfcProject=topic.get("ifc_project_guid",""),
                             isExternal="false")
    ET.SubElement(file_el, "Filename").text  = "model.ifc"
    ET.SubElement(file_el, "Date").text      = topic["creation_date"]
    ET.SubElement(file_el, "Reference").text = "../model.ifc"

    # Topic
    t = ET.SubElement(root, "Topic",
        Guid=topic["guid"],
        TopicType=topic["type"],
        TopicStatus=topic["status"]
    )
    ET.SubElement(t, "Title").text        = topic["title"]
    ET.SubElement(t, "Priority").text     = topic["priority"]
    ET.SubElement(t, "CreationDate").text = topic["creation_date"]
    ET.SubElement(t, "CreationAuthor").text = topic["author"]
    ET.SubElement(t, "ModifiedDate").text = topic["modified_date"]
    ET.SubElement(t, "ModifiedAuthor").text = topic["author"]
    if topic.get("assigned_to"):
        ET.SubElement(t, "AssignedTo").text = topic["assigned_to"]
    if topic.get("description"):
        ET.SubElement(t, "Description").text = topic["description"]
    if topic.get("stage"):
        ET.SubElement(t, "Stage").text = topic["stage"]
    for label in topic.get("labels", []):
        ET.SubElement(t, "Labels").text = label
    for rguid in topic.get("related_guids", []):
        ET.SubElement(t, "RelatedTopic", Guid=rguid)

    # Viewpoints reference
    vp = ET.SubElement(root, "Viewpoints", Guid=topic["guid"])
    ET.SubElement(vp, "Viewpoint").text = "viewpoint.bcfv"
    ET.SubElement(vp, "Snapshot").text  = "snapshot.png"
    ET.SubElement(vp, "Index").text     = "0"

    # Comments
    for c in topic.get("comments", []):
        comment = ET.SubElement(root, "Comment", Guid=str(uuid.uuid4()))
        ET.SubElement(comment, "Date").text     = c.get("date", topic["creation_date"])
        ET.SubElement(comment, "Author").text   = c.get("author", topic["author"])
        ET.SubElement(comment, "Comment").text  = c["text"]
        ET.SubElement(comment, "Viewpoint", Guid=topic["guid"])

    return pretty_xml(root)

def make_viewpoint(topic):
    """Generate a BCF viewpoint with perspective camera and component selections."""
    root = ET.Element("VisualizationInfo", Guid=topic["guid"])

    # Components — selected / coloured elements
    components = ET.SubElement(root, "Components")

    # ViewSetupHints
    ET.SubElement(components, "ViewSetupHints",
        SpacesVisible="false",
        SpaceBoundariesVisible="false",
        OpeningsVisible="false"
    )

    # Selection
    selection = ET.SubElement(components, "Selection")
    for gid in topic.get("component_guids", [])[:10]:   # BCF spec recommends ≤10 per viewpoint
        comp = ET.SubElement(selection, "Component", IfcGuid=gid)
        ET.SubElement(comp, "OriginatingSystem").text = "BIMGuard"
        ET.SubElement(comp, "AuthoringToolId").text   = gid

    # Coloring
    if topic.get("component_guids"):
        coloring = ET.SubElement(components, "Coloring")
        color_el = ET.SubElement(coloring, "Color", Color="FF0000")  # red for issues
        for gid in topic.get("component_guids", [])[:10]:
            comp = ET.SubElement(color_el, "Component", IfcGuid=gid)
            ET.SubElement(comp, "OriginatingSystem").text = "BIMGuard"

    # Visibility — hide nothing explicitly
    visibility = ET.SubElement(components, "Visibility", DefaultVisibility="true")
    ET.SubElement(visibility, "Exceptions")

    # Perspective camera — simple overhead view
    camera = ET.SubElement(root, "PerspectiveCamera")
    vp_loc = ET.SubElement(camera, "CameraViewPoint")
    ET.SubElement(vp_loc, "X").text = str(topic.get("cam_x", 0.0))
    ET.SubElement(vp_loc, "Y").text = str(topic.get("cam_y", -10.0))
    ET.SubElement(vp_loc, "Z").text = str(topic.get("cam_z", 5.0))
    vp_dir = ET.SubElement(camera, "CameraDirection")
    ET.SubElement(vp_dir, "X").text = "0"
    ET.SubElement(vp_dir, "Y").text = "1"
    ET.SubElement(vp_dir, "Z").text = "-0.5"
    vp_up = ET.SubElement(camera, "CameraUpVector")
    ET.SubElement(vp_up, "X").text = "0"
    ET.SubElement(vp_up, "Y").text = "0"
    ET.SubElement(vp_up, "Z").text = "1"
    ET.SubElement(camera, "FieldOfView").text = "60"

    return pretty_xml(root)


def _get_element_bbox(ifc_model, guid):
    """
    Return (min_x, min_y, max_x, max_y) for the IFC element with the given
    GlobalId by iterating over its geometry vertices.
    Returns None if the element cannot be found or has no geometry.
    """
    try:
        import ifcopenshell.geom
        import numpy as np

        element = ifc_model.by_guid(guid)
        if element is None:
            return None

        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)

        shape = ifcopenshell.geom.create_shape(settings, element)
        verts = shape.geometry.verts            # flat list [x,y,z, x,y,z, ...]
        if not verts:
            return None

        arr = list(verts)
        xs = arr[0::3]
        ys = arr[1::3]
        return (min(xs), min(ys), max(xs), max(ys))
    except Exception:
        return None


def _get_all_elements_bbox(ifc_model):
    """
    Return (min_x, min_y, max_x, max_y) across ALL elements in the model.
    Used as the background plan-view extent.
    Returns None on failure.
    """
    try:
        import ifcopenshell.geom

        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)

        iterator = ifcopenshell.geom.iterator(settings, ifc_model)
        all_xs, all_ys = [], []
        if iterator.initialize():
            while True:
                shape = iterator.get()
                verts = shape.geometry.verts
                if verts:
                    arr = list(verts)
                    all_xs.extend(arr[0::3])
                    all_ys.extend(arr[1::3])
                if not iterator.next():
                    break
        if all_xs:
            return (min(all_xs), min(all_ys), max(all_xs), max(all_ys))
    except Exception:
        pass
    return None


def make_snapshot_png(topic, ifc_model=None):
    """
    Generate an 800x600 PNG snapshot that shows the element's position in the
    model as a top-down (plan) view schematic:

      • Grey silhouette of the whole model footprint
      • Highlighted bounding-box rectangle for the affected element(s)
      • Issue metadata overlaid in a header and footer bar

    Falls back to a plain info-card if geometry cannot be extracted.
    """
    W, H = 800, 600
    VIEWPORT_X0, VIEWPORT_Y0 = 0, 60        # canvas area reserved for the plan
    VIEWPORT_X1, VIEWPORT_Y1 = W, H - 50

    # ── Priority colours ──────────────────────────────────────────────────────
    priority = (topic.get("priority") or "Normal").lower()
    if "critical" in priority:
        bg_col, bar_col, hl_col = (18, 10, 10), (160, 30, 30),  (255, 80,  80)
    elif "major" in priority:
        bg_col, bar_col, hl_col = (18, 14, 8),  (170, 90,  0),  (255, 180, 0)
    elif "minor" in priority:
        bg_col, bar_col, hl_col = (8,  18, 12), (0,  120, 55),  (50,  220, 100)
    else:
        bg_col, bar_col, hl_col = (10, 18, 32), (30,  80, 160), (80,  160, 255)

    img  = Image.new("RGB", (W, H), bg_col)
    draw = ImageDraw.Draw(img)

    # ── Fonts ─────────────────────────────────────────────────────────────────
    try:
        fnt_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        fnt_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      16)
        fnt_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      12)
    except Exception:
        fnt_lg = fnt_md = fnt_sm = ImageFont.load_default()

    # ── Header bar ────────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, VIEWPORT_Y0], fill=bar_col)
    draw.text((12, 10), "BIMGuard  ·  BCF Issue Snapshot", font=fnt_md, fill=(255, 255, 255))
    draw.text((12, 32), topic.get("title", "BIM Issue")[:72],          font=fnt_sm, fill=(220, 220, 220))
    type_txt = topic.get("type", "Issue")
    try:
        tw = draw.textlength(type_txt, font=fnt_sm)
    except Exception:
        tw = len(type_txt) * 8
    draw.text((W - tw - 14, 22), type_txt, font=fnt_sm, fill=(255, 230, 100))

    # ── Footer bar ────────────────────────────────────────────────────────────
    draw.rectangle([0, H - 50, W, H], fill=bar_col)
    meta = (
        f"Priority: {topic.get('priority','Normal')}  |  "
        f"Status: {topic.get('status','Open')}  |  "
        f"Author: {topic.get('author','BIMGuard')}  |  "
        f"Date: {(topic.get('creation_date') or '')[:10]}"
    )
    draw.text((12, H - 38), meta,                                       font=fnt_sm, fill=(200, 200, 200))
    draw.text((12, H - 20), "Auto-generated by BIMGuard  ·  BCF 2.1",  font=fnt_sm, fill=(140, 140, 140))

    # ── Plan-view area background ─────────────────────────────────────────────
    draw.rectangle([VIEWPORT_X0, VIEWPORT_Y0, VIEWPORT_X1, VIEWPORT_Y1],
                   fill=(22, 28, 38))

    # ── Try to render geometry ────────────────────────────────────────────────
    rendered = False
    component_guids = [g for g in (topic.get("component_guids") or []) if g]

    if ifc_model and component_guids:
        model_bbox  = _get_all_elements_bbox(ifc_model)
        elem_bboxes = [_get_element_bbox(ifc_model, g) for g in component_guids]
        elem_bboxes = [b for b in elem_bboxes if b is not None]

        if model_bbox and elem_bboxes:
            mx0, my0, mx1, my1 = model_bbox
            pad   = max((mx1 - mx0), (my1 - my0)) * 0.05 or 1.0
            mx0  -= pad; my0 -= pad; mx1 += pad; my1 += pad
            span_x = mx1 - mx0 or 1.0
            span_y = my1 - my0 or 1.0

            # coordinate mapper: IFC XY → canvas pixel
            vw = VIEWPORT_X1 - VIEWPORT_X0 - 20
            vh = VIEWPORT_Y1 - VIEWPORT_Y0 - 20

            def to_px(ix, iy):
                px = VIEWPORT_X0 + 10 + (ix - mx0) / span_x * vw
                py = VIEWPORT_Y1 - 10 - (iy - my0) / span_y * vh  # flip Y
                return int(px), int(py)

            # Draw full model silhouette (grey rectangle)
            p0 = to_px(mx0, my0)
            p1 = to_px(mx1, my1)
            draw.rectangle([p0, p1], outline=(60, 70, 90), width=1, fill=(30, 38, 52))

            # Draw grid lines every ~10 % of span
            for frac in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                gx0, gy0 = to_px(mx0 + span_x * frac, my0)
                gx1, gy1 = to_px(mx0 + span_x * frac, my1)
                draw.line([(gx0, gy0), (gx1, gy1)], fill=(40, 50, 68), width=1)
                gx0, gy0 = to_px(mx0, my0 + span_y * frac)
                gx1, gy1 = to_px(mx1, my0 + span_y * frac)
                draw.line([(gx0, gy0), (gx1, gy1)], fill=(40, 50, 68), width=1)

            # Draw highlighted element bounding boxes
            for bbox in elem_bboxes:
                ex0, ey0, ex1, ey1 = bbox
                ep0 = to_px(ex0, ey0)
                ep1 = to_px(ex1, ey1)
                # Glow / shadow
                draw.rectangle(
                    [ep0[0] - 4, ep1[1] - 4, ep1[0] + 4, ep0[1] + 4],
                    fill=(*hl_col, 60) if hasattr(draw, "rectangle") else hl_col,
                    outline=None,
                )
                draw.rectangle([ep0[1] if ep0[1]<ep1[1] else ep1[1],  # y-min pixel
                                 ep0[0] if ep0[0]<ep1[0] else ep1[0],  # x-min pixel
                                 ep1[1] if ep0[1]<ep1[1] else ep0[1],  # y-max pixel
                                 ep1[0] if ep0[0]<ep1[0] else ep0[0]], # x-max pixel
                                outline=hl_col, width=3)
                # Simpler reliable rectangle draw:
                px_x0 = min(ep0[0], ep1[0])
                px_y0 = min(ep0[1], ep1[1])
                px_x1 = max(ep0[0], ep1[0])
                px_y1 = max(ep0[1], ep1[1])
                draw.rectangle([px_x0 - 3, px_y0 - 3, px_x1 + 3, px_y1 + 3],
                               outline=(*hl_col[:3],), width=2)
                draw.rectangle([px_x0, px_y0, px_x1, px_y1],
                               fill=tuple(int(c * 0.35) for c in hl_col),
                               outline=hl_col, width=3)

            # Compass rose (top-right of viewport)
            cx, cy = VIEWPORT_X1 - 30, VIEWPORT_Y0 + 30
            draw.line([(cx, cy), (cx, cy - 18)], fill=(200, 200, 255), width=2)
            draw.text((cx - 4, cy - 30), "N", font=fnt_sm, fill=(200, 200, 255))

            # Label the highlighted element(s)
            if elem_bboxes:
                ex0, ey0, ex1, ey1 = elem_bboxes[0]
                lx, ly = to_px((ex0 + ex1) / 2, ey1)
                label = (component_guids[0][:16] + "…") if len(component_guids[0]) > 16 else component_guids[0]
                draw.text((lx + 6, ly - 10), f"▶ {label}", font=fnt_sm, fill=hl_col)

            rendered = True

    # ── Fallback: no geometry available ──────────────────────────────────────
    if not rendered:
        draw.text((VIEWPORT_X0 + 20, VIEWPORT_Y0 + 20),
                  "⚠ No geometry data available for this element.",
                  font=fnt_sm, fill=(160, 160, 160))
        guids = topic.get("component_guids") or []
        guid_txt = (guids[0][:30] + "…") if guids else "—"
        fields = [
            ("Priority",   topic.get("priority",    "Normal")),
            ("Status",     topic.get("status",       "Open")),
            ("Author",     topic.get("author",       "BIMGuard")),
            ("Date",       (topic.get("creation_date") or "")[:10]),
            ("Element ID", guid_txt),
            ("Note",       (topic.get("description") or "")[:60]),
        ]
        fy = VIEWPORT_Y0 + 50
        for label, value in fields:
            draw.text((20,  fy), label + ":", font=fnt_sm, fill=(120, 170, 255))
            draw.text((160, fy), str(value),  font=fnt_md, fill=(210, 210, 210))
            fy += 32

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()

def build_bcfzip(project_name, project_id, topics, ifc_model=None):
    """Assemble all topics into a valid BCF 2.1 zip archive, returned as bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bcf.version",  make_bcf_version())
        z.writestr("project.bcfp", make_project_bcfp(project_name, project_id))
        for topic in topics:
            folder = topic["guid"] + "/"
            z.writestr(folder + "markup.bcf",     make_markup(topic))
            z.writestr(folder + "viewpoint.bcfv", make_viewpoint(topic))
            z.writestr(folder + "snapshot.png",   make_snapshot_png(topic, ifc_model=ifc_model))
    buf.seek(0)
    return buf.read()

# ══════════════════════════════════════════════════════════════════════════════
# AUTO-GENERATE ISSUES FROM ANALYSIS DATA
# ══════════════════════════════════════════════════════════════════════════════

def auto_generate_topics(an, model, author, project_id, include_proxies,
                         include_psets, include_geo, include_rel, max_topics):
    """Build BCF topic dicts from existing BIMGuard analysis results."""
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    topics = []

    # ── 1. Proxy Issues ──────────────────────────────────────────────────────
    if include_proxies:
        proxy_list = an.get("proxy_list", [])
        for p in proxy_list[:max_topics]:
            topics.append({
                "guid":             str(uuid.uuid4()),
                "type":             "Issue",
                "status":           "Open",
                "priority":         "Major",
                "title":            f"Proxy Element: {p['Name']}",
                "description":      f"Element '{p['Name']}' (GlobalId: {p['GlobalId']}) is classified as IfcBuildingElementProxy. "
                                    f"This element has lost its semantic IFC type during export and must be reclassified. "
                                    f"Use Correction Suggestions in BIMGuard to assign the correct IFC type.",
                "author":           author,
                "assigned_to":      "",
                "creation_date":    now,
                "modified_date":    now,
                "stage":            "Design",
                "labels":           ["ProxyElement", "SemanticLoss", "BIMGuard"],
                "comments":         [{"text": "Auto-generated by BIMGuard Proxy Detection Engine.", "author": "BIMGuard", "date": now}],
                "component_guids":  [p["GlobalId"]],
                "related_guids":    [],
                "ifc_project_guid": project_id,
                "cam_x": 0, "cam_y": -10, "cam_z": 8,
            })

    # ── 2. Missing Pset Issues ───────────────────────────────────────────────
    if include_psets:
        pset_list = an.get("missing_pset_list", [])
        for p in pset_list[:max_topics]:
            topics.append({
                "guid":             str(uuid.uuid4()),
                "type":             "Issue",
                "status":           "Open",
                "priority":         "Normal",
                "title":            f"Missing Pset: {p.get('Name','Unnamed')} ({p.get('Type','')})",
                "description":      f"Element '{p.get('Name','Unnamed')}' of type {p.get('Type','')} "
                                    f"(GlobalId: {p.get('GlobalId','N/A')}) is missing its required property set "
                                    f"'{p.get('Needs','')}'. Property sets are required for compliance checks, "
                                    f"energy simulation, and cost estimation.",
                "author":           author,
                "assigned_to":      "",
                "creation_date":    now,
                "modified_date":    now,
                "stage":            "Design",
                "labels":           ["MissingPset", "PropertyData", "BIMGuard"],
                "comments":         [{"text": "Auto-generated by BIMGuard Pset Analysis Engine.", "author": "BIMGuard", "date": now}],
                "component_guids":  [p.get("GlobalId","")] if p.get("GlobalId") else [],
                "related_guids":    [],
                "ifc_project_guid": project_id,
                "cam_x": 0, "cam_y": -10, "cam_z": 8,
            })

    # ── 3. Geometry Loss Issues ──────────────────────────────────────────────
    if include_geo:
        geo_list = an.get("geo_loss_list", [])
        for p in geo_list[:max_topics]:
            topics.append({
                "guid":             str(uuid.uuid4()),
                "type":             "Error",
                "status":           "Open",
                "priority":         "Major",
                "title":            f"Missing Geometry: {p.get('Name','Unnamed')}",
                "description":      f"Element '{p.get('Name','Unnamed')}' (GlobalId: {p.get('GlobalId','N/A')}) "
                                    f"has no ObjectPlacement or Representation in the IFC model. "
                                    f"This element cannot be visualized or used in clash detection.",
                "author":           author,
                "assigned_to":      "",
                "creation_date":    now,
                "modified_date":    now,
                "stage":            "Design",
                "labels":           ["MissingGeometry", "GeometryLoss", "BIMGuard"],
                "comments":         [{"text": "Auto-generated by BIMGuard 5-Level Data Loss Analysis.", "author": "BIMGuard", "date": now}],
                "component_guids":  [p.get("GlobalId","")] if p.get("GlobalId") else [],
                "related_guids":    [],
                "ifc_project_guid": project_id,
                "cam_x": 0, "cam_y": -10, "cam_z": 8,
            })

    # ── 4. Relationship Loss Issues ──────────────────────────────────────────
    if include_rel:
        rel_list = an.get("rel_loss_list", [])
        for p in rel_list[:max_topics]:
            topics.append({
                "guid":             str(uuid.uuid4()),
                "type":             "Issue",
                "status":           "Open",
                "priority":         "Minor",
                "title":            f"No Storey Assignment: {p.get('Name','Unnamed')}",
                "description":      f"Element '{p.get('Name','Unnamed')}' (GlobalId: {p.get('GlobalId','N/A')}) "
                                    f"is not assigned to any IfcBuildingStorey via IfcRelContainedInSpatialStructure. "
                                    f"This prevents floor-based filtering and storey-level quantity takeoffs.",
                "author":           author,
                "assigned_to":      "",
                "creation_date":    now,
                "modified_date":    now,
                "stage":            "Design",
                "labels":           ["MissingStoreyAssignment", "RelationshipLoss", "BIMGuard"],
                "comments":         [{"text": "Auto-generated by BIMGuard Relationship Loss Analysis.", "author": "BIMGuard", "date": now}],
                "component_guids":  [p.get("GlobalId","")] if p.get("GlobalId") else [],
                "related_guids":    [],
                "ifc_project_guid": project_id,
                "cam_x": 0, "cam_y": -10, "cam_z": 8,
            })

    return topics

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

st.title("📋 BCF Generator")
st.caption("Generate a BIM Collaboration Format (BCF 2.1) file from your model issues — importable into Revit, Navisworks, BIM 360, Solibri, and any BCF-compatible viewer.")
st.markdown("---")

# ── Summary metrics ───────────────────────────────────────────────────────────
proxy_ct  = an.get("proxy_elements", 0)
pset_ct   = an.get("missing_pset_count", 0)
geo_ct    = an.get("geo_loss_count", 0)
rel_ct    = an.get("rel_loss_count", 0)
total_issues = proxy_ct + pset_ct + geo_ct + rel_ct

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("🔴 Proxy Elements",    proxy_ct)
m2.metric("📦 Missing Psets",     pset_ct)
m3.metric("📐 Missing Geometry",  geo_ct)
m4.metric("🔗 Missing Storey",    rel_ct)
m5.metric("📋 Total BCF Topics",  total_issues)

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["⚡ Auto-Generate from Analysis", "✏️ Manual Issue Creator", "📄 About BCF"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — AUTO-GENERATE
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Auto-Generate BCF from BIMGuard Analysis")
    st.caption("Converts all detected model issues into BCF 2.1 topics ready to import into Revit, Navisworks, BIM 360, or Solibri.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📁 Project Settings")
        ag_project_name = st.text_input("Project Name", value="BIMGuard Project", key="ag_proj")
        ag_author       = st.text_input("Author / Coordinator", value=st.session_state.get("user_context",{}).get("name","BIMGuard User"), key="ag_author")
        ag_max          = st.number_input("Max issues per category", min_value=5, max_value=200, value=50, step=5, key="ag_max")

    with col2:
        st.markdown("#### 🎯 Issue Categories to Include")
        ag_proxy = st.checkbox(f"🔴 Proxy Elements  ({proxy_ct} issues)", value=True,  key="ag_chk_proxy")
        ag_pset  = st.checkbox(f"📦 Missing Psets   ({pset_ct} issues)",  value=True,  key="ag_chk_pset")
        ag_geo   = st.checkbox(f"📐 Missing Geometry ({geo_ct} issues)",  value=True,  key="ag_chk_geo")
        ag_rel   = st.checkbox(f"🔗 No Storey Assignment ({rel_ct})",     value=False, key="ag_chk_rel")

    st.markdown("---")

    # Derive IFC project GUID
    try:
        ifc_projects = model.by_type("IfcProject")
        project_id = ifc_projects[0].GlobalId if ifc_projects else str(uuid.uuid4())
        project_display = ifc_projects[0].Name or "Unnamed Project" if ifc_projects else ag_project_name
    except Exception:
        project_id = str(uuid.uuid4())
        project_display = ag_project_name

    # Preview count
    preview_count = (
        (min(proxy_ct, ag_max) if ag_proxy else 0) +
        (min(pset_ct,  ag_max) if ag_pset  else 0) +
        (min(geo_ct,   ag_max) if ag_geo   else 0) +
        (min(rel_ct,   ag_max) if ag_rel   else 0)
    )

    st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
    padding:14px 20px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
    <div>
        <span style="font-size:14px;font-weight:700;color:#e6edf3;">Ready to generate</span>
        <span style="font-size:12px;color:#8b949e;margin-left:10px;">{preview_count} BCF topics across selected categories</span>
    </div>
    <div style="font-size:12px;color:#8b949e;">BCF 2.1 format · importable into Revit, BIM 360, Navisworks, Solibri</div>
    </div>""", unsafe_allow_html=True)

    if preview_count == 0:
        st.info("Select at least one issue category above to generate BCF topics.")
    else:
        if st.button("⚡ Generate BCF File", use_container_width=True, key="ag_gen"):
            with st.spinner(f"Building {preview_count} BCF topics..."):
                topics = auto_generate_topics(
                    an, model,
                    author       = ag_author,
                    project_id   = project_id,
                    include_proxies = ag_proxy,
                    include_psets   = ag_pset,
                    include_geo     = ag_geo,
                    include_rel     = ag_rel,
                    max_topics      = ag_max,
                )
                bcf_bytes = build_bcfzip(ag_project_name, project_id, topics, ifc_model=model)
                st.session_state["bcf_bytes"]    = bcf_bytes
                st.session_state["bcf_count"]    = len(topics)
                st.session_state["bcf_filename"] = f"BIMGuard_{ag_project_name.replace(' ','_')}.bcfzip"

        if st.session_state.get("bcf_bytes"):
            cnt  = st.session_state["bcf_count"]
            fname = st.session_state["bcf_filename"]

            st.markdown(f"""<div style="background:#0d2b18;border:1.5px solid #238636;border-radius:10px;
            padding:14px 20px;margin:10px 0;display:flex;justify-content:space-between;align-items:center;">
            <div>
                <span style="font-size:14px;font-weight:700;color:#238636;">✅ BCF file ready</span>
                <span style="font-size:12px;color:#8b949e;margin-left:10px;">{cnt} topics · BCF 2.1 format</span>
            </div>
            <div style="font-size:11px;color:#8b949e;">{fname}</div>
            </div>""", unsafe_allow_html=True)

            st.download_button(
                label=f"⬇️ Download {fname}",
                data=st.session_state["bcf_bytes"],
                file_name=fname,
                mime="application/zip",
                use_container_width=True,
            )

            # Preview table
            st.markdown("#### 📋 Topic Preview")
            topics_preview = auto_generate_topics(
                an, model, ag_author, project_id,
                ag_proxy, ag_pset, ag_geo, ag_rel, ag_max
            )
            import pandas as pd
            preview_rows = [{
                "Title":       t["title"][:70]+"…" if len(t["title"])>70 else t["title"],
                "Type":        t["type"],
                "Priority":    t["priority"],
                "Status":      t["status"],
                "Labels":      ", ".join(t["labels"][:2]),
                "Components":  len(t["component_guids"]),
            } for t in topics_preview[:100]]
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True, height=350)
            if cnt > 100:
                st.caption(f"Showing first 100 of {cnt} topics.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MANUAL ISSUE CREATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Manual BCF Issue Creator")
    st.caption("Create individual BCF topics by hand — useful for coordination issues, RFIs, and clash notes.")

    if "manual_topics" not in st.session_state:
        st.session_state.manual_topics = []

    # ── Add new topic form ────────────────────────────────────────────────────
    with st.expander("➕ Add New Issue", expanded=len(st.session_state.manual_topics)==0):
        fc1, fc2 = st.columns(2)
        m_title    = fc1.text_input("Issue Title *", placeholder="e.g. Wall W-12 missing FireRating", key="m_title")
        m_type     = fc2.selectbox("Issue Type", ISSUE_TYPES, key="m_type")

        fd1, fd2, fd3 = st.columns(3)
        m_priority = fd1.selectbox("Priority", list(PRIORITY_MAP.keys()), index=1, key="m_pri")
        m_status   = fd2.selectbox("Status",   list(STATUS_MAP.keys()),   index=0, key="m_stat")
        m_author   = fd3.text_input("Author", value=st.session_state.get("user_context",{}).get("name","BIMGuard User"), key="m_auth")

        fe1, fe2 = st.columns(2)
        m_assigned = fe1.text_input("Assigned To", placeholder="e.g. architect@firm.com", key="m_assign")
        m_stage    = fe2.selectbox("Stage", ["Design", "Construction", "Handover", "Operation"], key="m_stage")

        m_desc     = st.text_area("Description", placeholder="Describe the issue in detail...", height=100, key="m_desc")
        m_labels   = st.text_input("Labels (comma-separated)", placeholder="e.g. FireSafety, Walls, NBC", key="m_labels")
        m_guids    = st.text_area("Component GlobalIds (one per line)", placeholder="Paste GlobalIds of affected elements...", height=80, key="m_guids")
        m_comment  = st.text_area("Initial Comment", placeholder="Add an initial comment or note...", height=60, key="m_comment")

        if st.button("➕ Add Issue to List", key="m_add"):
            if not m_title.strip():
                st.error("Issue title is required.")
            else:
                now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                guids = [g.strip() for g in m_guids.split("\n") if g.strip()]
                labels = [l.strip() for l in m_labels.split(",") if l.strip()]
                comments = []
                if m_comment.strip():
                    comments.append({"text": m_comment.strip(), "author": m_author, "date": now})
                st.session_state.manual_topics.append({
                    "guid":             str(uuid.uuid4()),
                    "type":             m_type,
                    "status":           STATUS_MAP[m_status],
                    "priority":         PRIORITY_MAP[m_priority],
                    "title":            m_title.strip(),
                    "description":      m_desc.strip(),
                    "author":           m_author,
                    "assigned_to":      m_assigned,
                    "creation_date":    now,
                    "modified_date":    now,
                    "stage":            m_stage,
                    "labels":           labels if labels else ["BIMGuard"],
                    "comments":         comments,
                    "component_guids":  guids,
                    "related_guids":    [],
                    "ifc_project_guid": "",
                    "cam_x": 0, "cam_y": -10, "cam_z": 8,
                })
                st.success(f"✅ Issue '{m_title}' added. ({len(st.session_state.manual_topics)} total)")
                st.rerun()

    # ── Current issue list ────────────────────────────────────────────────────
    if st.session_state.manual_topics:
        st.markdown(f"#### 📋 {len(st.session_state.manual_topics)} Issue(s) in Queue")

        for i, t in enumerate(st.session_state.manual_topics):
            pri_col = {"Critical":"#da3633","Major":"#d29922","Normal":"#58a6ff","Minor":"#8b949e"}.get(t["priority"],"#8b949e")
            with st.expander(f"{i+1}. {t['title']}  —  {t['priority']}  |  {t['status']}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**Type:** {t['type']}")
                c2.markdown(f"**Author:** {t['author']}")
                c3.markdown(f"**Stage:** {t['stage']}")
                c4.markdown(f"**Components:** {len(t['component_guids'])}")
                if t.get("description"):
                    st.markdown(f"**Description:** {t['description']}")
                if t.get("labels"):
                    st.markdown(f"**Labels:** {', '.join(t['labels'])}")
                if t.get("comments"):
                    st.markdown(f"**Comment:** {t['comments'][0]['text']}")
                if st.button(f"🗑️ Remove", key=f"del_{i}"):
                    st.session_state.manual_topics.pop(i)
                    st.rerun()

        # ── Export ───────────────────────────────────────────────────────────
        st.markdown("---")
        mc1, mc2 = st.columns(2)
        man_project = mc1.text_input("Project Name", "Manual BCF Export", key="man_proj")
        man_author  = mc2.text_input("Author",
                      value=st.session_state.get("user_context",{}).get("name","BIMGuard User"),
                      key="man_auth_exp")

        if st.button("⬇️ Export Manual Issues as BCF", use_container_width=True, key="man_export"):
            try:
                ifc_projects = model.by_type("IfcProject")
                proj_id = ifc_projects[0].GlobalId if ifc_projects else str(uuid.uuid4())
            except Exception:
                proj_id = str(uuid.uuid4())
            bcf_bytes = build_bcfzip(man_project, proj_id, st.session_state.manual_topics, ifc_model=model)
            st.download_button(
                label=f"⬇️ Download {man_project.replace(' ','_')}.bcfzip",
                data=bcf_bytes,
                file_name=f"{man_project.replace(' ','_')}.bcfzip",
                mime="application/zip",
                use_container_width=True,
                key="man_dl",
            )

        if st.button("🗑️ Clear All Issues", key="man_clear"):
            st.session_state.manual_topics = []
            st.rerun()
    else:
        st.info("No manual issues yet. Use the form above to add issues.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ABOUT BCF
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("What is BCF?")
    st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px 22px;margin-bottom:12px;">
<p style="color:#e6edf3;font-size:14px;margin:0 0 10px;">
<strong style="color:#58a6ff;">BIM Collaboration Format (BCF)</strong> is an open standard by buildingSMART International
that allows different BIM tools to share model issues, comments, and markups without exchanging the full IFC model.
It is the industry standard for coordinating issues between architects, engineers, and contractors on a shared BIM project.
</p>
<p style="color:#8b949e;font-size:13px;margin:0;">
BCF is supported by Autodesk Revit, Autodesk BIM 360, Trimble Navisworks, Graphisoft ArchiCAD, Solibri,
BIMcollab, Tekla Structures, and over 100 other BIM tools.
</p>
</div>""", unsafe_allow_html=True)

    st.markdown("#### 📁 BCF 2.1 File Structure")
    st.code("""BIMGuard_Project.bcfzip
├── bcf.version              ← BCF version manifest (2.1)
├── project.bcfp             ← Project name and GUID
└── <topic-guid>/            ← One folder per issue
    ├── markup.bcf           ← Issue title, description, author,
    │                           status, priority, comments,
    │                           component GlobalIds
    └── viewpoint.bcfv       ← Camera position + highlighted
                                components (coloured red)""", language="text")

    st.markdown("#### 🔧 How to Import BCF in Common Tools")

    col1, col2 = st.columns(2)
    with col1:
        for tool, steps in [
            ("Autodesk Revit", ["Open the Add-Ins tab", "Click BCF Manager (install from Autodesk App Store if needed)", "Click Open BCF → select .bcfzip", "Issues appear in the issue list with element highlighting"]),
            ("Autodesk BIM 360", ["Go to Document Management", "Upload the .bcfzip file", "Open in BIM 360 Issues viewer", "Each topic becomes a linked issue"]),
            ("Solibri", ["Go to Communication → BCF", "Click Import BCF", "Select the .bcfzip file", "Topics appear with viewpoints and components highlighted"]),
        ]:
            st.markdown(f"**{tool}**")
            for s in steps:
                st.markdown(f"&nbsp;&nbsp;&nbsp;{s}", unsafe_allow_html=True)
            st.markdown("")

    with col2:
        for tool, steps in [
            ("Trimble Navisworks", ["Go to Home → Tools → BCF Manager", "Click Import → select .bcfzip", "Issues appear in the BCF panel", "Click a topic to highlight components"]),
            ("Graphisoft ArchiCAD", ["Go to Teamwork → BCF Manager", "Click Import BCF File", "Select the .bcfzip", "Components are highlighted per topic"]),
            ("BIMcollab Zoom", ["Open BIMcollab Zoom", "Go to Issues → Import BCF", "Select the .bcfzip file", "Issues sync to the BIMcollab cloud platform"]),
        ]:
            st.markdown(f"**{tool}**")
            for s in steps:
                st.markdown(f"&nbsp;&nbsp;&nbsp;{s}", unsafe_allow_html=True)
            st.markdown("")

    st.markdown("#### 📌 BCF Topic Fields Reference")
    import pandas as pd
    st.dataframe(pd.DataFrame([
        {"Field":"Title",       "Required":"Yes","Description":"Short summary of the issue"},
        {"Field":"TopicType",   "Required":"Yes","Description":"Issue / Request / Clash / Remark / Error"},
        {"Field":"TopicStatus", "Required":"Yes","Description":"Open / InProgress / Resolved / Closed"},
        {"Field":"Priority",    "Required":"No", "Description":"Critical / Major / Normal / Minor"},
        {"Field":"CreationDate","Required":"Yes","Description":"ISO 8601 UTC timestamp"},
        {"Field":"CreationAuthor","Required":"Yes","Description":"Email or name of the author"},
        {"Field":"AssignedTo",  "Required":"No", "Description":"Assignee email or name"},
        {"Field":"Description", "Required":"No", "Description":"Full description of the issue"},
        {"Field":"Stage",       "Required":"No", "Description":"Design / Construction / Handover"},
        {"Field":"Labels",      "Required":"No", "Description":"Freetext tags for filtering"},
        {"Field":"Component GlobalIds","Required":"No","Description":"IFC element GlobalIds highlighted in viewpoint"},
        {"Field":"Comments",    "Required":"No", "Description":"Threaded discussion on the topic"},
    ]), use_container_width=True, hide_index=True)