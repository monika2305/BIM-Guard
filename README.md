# BIM-Guard
Free, web-based IFC quality assurance platform — detects semantic data loss, scores model integrity, checks NBC 2016 compliance, and exports BCF 2.1 issue reports.
# 🛡️ BIMGuard — IFC Integrity Platform

> **Free, web-based BIM quality assurance platform — no BIM software required.**

BIMGuard detects semantic data loss in IFC files exported from Revit, ArchiCAD, and Tekla,
computes a 0–100 Model Integrity Score, checks NBC 2016 compliance, and exports 
standards-compliant BCF 2.1 issue reports — all in a browser.

---

## 🚀 Live Demo
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-link.streamlit.app)

---

## 📌 Problem Statement

When BIM models are exported to IFC format, critical semantic information is silently lost.
Building elements precisely defined in Revit or ArchiCAD become generic 
`IfcBuildingElementProxy` objects — breaking coordination, compliance, and FM workflows.

Existing tools like Solibri cost ₹20–50 lakhs/year and do not check against 
India's National Building Code 2016. BIMGuard fills this gap at zero cost.

---

## ✨ Features

### 🔬 5-Level Data Loss Framework
| Level | Type | Weight |
|-------|------|--------|
| L1 | Semantic Loss (IfcBuildingElementProxy) | 30% |
| L2 | Property Loss (missing Psets) | 20% |
| L3 | Quantity Loss (missing IfcElementQuantity) | 15% |
| L4 | Relationship Loss (no storey assignment) | 25% |
| L5 | Geometry Loss (no representation) | 10% |

### 📊 11 Interactive Dashboards
| # | Module | Description |
|---|--------|-------------|
| 1 | 🏠 Home Dashboard | IFC upload, 5-level loss analysis, KPIs |
| 2 | 🔎 Proxy Classification | Detects IfcBuildingElementProxy elements |
| 3 | 📦 Pset Analysis | Checks 20 IFC element types for required Psets |
| 4 | 🧊 3D BIM Viewer | Interactive 3D viewer colour-coded by IFC type |
| 5 | 🔥 Issue Heatmap | 2D floor plan density map of quality issues |
| 6 | 🏢 Storey Quality Score | Per-floor quality scoring |
| 7 | 📏 Rule Validation | 17+ built-in rules + custom rule builder |
| 8 | 🇮🇳 NBC 2016 Compliance | National Building Code of India 2016 checks |
| 9 | 🛠️ Correction Engine | Rule-based proxy reclassification + Pset injection |
| 10 | 📋 BCF 2.1 Generator | Standards-compliant BCF issue packages |
| 11 | 🔀 Version Comparison | GlobalId-based diff of two IFC versions |

---

## 🏗️ System Architecture
```
IFC File Upload (Revit · ArchiCAD · Tekla · up to 800 MB)
        ↓
Single-Pass IFC Parser (ifcopenshell · parsed once)
        ↓
Session State Cache (all results stored · sub-second page loads)
        ↓
┌─────────────┬──────────────────┬───────────────┐
│  Analysis   │ Correction Engine│  Compliance   │
│ 5-Level Loss│ Proxy Reclass.   │ NBC 2016      │
│ Pset Check  │ Pset Injection   │ 17+ Rules     │
│ Qty/Rel/Geo │ 0–100 Score      │ BCF 2.1 Gen   │
└─────────────┴──────────────────┴───────────────┘
        ↓
11 Interactive Dashboards
        ↓
Exports: BCF 2.1 · PDF Reports · CSV · Model Score Card
```

---

## 🧮 Model Quality Score
```
Score = 100 − Total Loss%

Total Loss% = (0.30 × Semantic) + (0.20 × Property) + 
              (0.15 × Quantity) + (0.25 × Relationship) + 
              (0.10 × Geometry)
```

| Grade | Score Range |
|-------|-------------|
| 🟢 Excellent | 85 – 100 |
| 🔵 Good | 70 – 84 |
| 🟡 Fair | 50 – 69 |
| 🔴 Poor | 0 – 49 |

---

## 🇮🇳 NBC 2016 Compliance

First open-source BIM tool to implement National Building Code of India 2016:
- Part 4 — Fire Safety
- Part 6 — Structural Design
- Part 8 — Accessibility
- Part 8 — Daylighting & Ventilation
- Part 11 — Approach to Sustainability
- BIM Addendum — Data Integrity
- Part 6 — Floor Slabs

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit 1.33 |
| BIM Engine | ifcopenshell 0.7 |
| Data Processing | Pandas 2.x |
| Reporting | FPDF2 |
| Issue Format | BCF 2.1 (XML/ZIP) |
| Visualisation | HTML5 Canvas / JavaScript |
| Language | Python 3.10+ |

---

## ⚙️ Installation
```bash
# Clone the repository
git clone https://github.com/your-username/BIMGuard.git
cd BIMGuard

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run Home.py
```

---

## 📋 Requirements
```
streamlit>=1.33.0
ifcopenshell>=0.7.0
pandas>=2.0.0
fpdf2>=2.7.0
Pillow>=10.0.0
qrcode>=7.4.2
```

---

## ✅ Tested On

| IFC File | Version | Elements | Result |
|----------|---------|----------|--------|
| Duplex Apartment (buildingSMART) | IFC 2x3 | 291 | ✅ All modules passed |
| Office Building (buildingSMART) | IFC 4 | 847 | ✅ All modules passed |
| MEP Sample (buildingSMART) | IFC 2x3 | 1,203 | ✅ All modules passed |

---

## 👥 Team

**Team ArchiTechs** — KPR Institute of Engineering and Technology

| Name | Role |
|------|------|
| Mithuna Kamalanathan | Team Leader |
| Monika M | Member |

**Mentor:** Mr Mohan M, Assistant Professor, BE CSE

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

> *BIMGuard — Making BIM Data Trustworthy for Every Construction Project in India*
