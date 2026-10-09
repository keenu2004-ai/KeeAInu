"""Domain Search Vocabulary & Explainable Multi-Factor Relevance Scoring Engine."""

import re
from typing import List, Dict, Any, Tuple
from backend.app.schemas.acquisition import RelevanceScoreBreakdown


# Configurable search vocabulary covering candidate domains and defect semantics
SEARCH_VOCABULARY = {
    "GENERAL_INSPECTION": [
        "borescope", "videoscope", "industrial endoscopy", "remote visual inspection", "rvi",
        "optical inspection", "internal visual inspection", "industrial anomaly detection",
        "surface defect detection", "defect segmentation", "flaw detection"
    ],
    "MECHANICAL": [
        "turbine", "engine", "compressor", "rotor", "blade", "gearbox", "bearing", "machinery",
        "turbine blade", "gas turbine", "steam turbine", "engine inspection", "aircraft engine",
        "bearing defect", "gearbox inspection", "compressor blade", "rotor shaft", "machinery defect",
        "casting porosity", "machining scratch", "mechanical wear", "fatigue crack"
    ],
    "PIPES_CHANNELS": [
        "pipe", "pipeline", "sewer", "tube", "boiler", "conduit", "heat exchanger",
        "pipe inspection", "pipeline corrosion", "sewer inspection", "tube wall thinning",
        "heat exchanger tube", "boiler tube", "internal weld defect", "pipe pitting",
        "pipeline crack", "internal deposit", "pipe blockage", "scale accumulation"
    ],
    "MOULD_CAVITIES": [
        "mould", "mold", "die", "cavity", "tooling", "injection",
        "mould cavity", "mold channel", "die cavity", "cooling channel", "injection mould",
        "die casting defect", "tooling surface", "mould wear", "cavity pitting", "tooling crack"
    ],
    "DEFECT_TERMS": [
        "crack", "corrosion", "pitting", "fracture", "erosion", "deposit", "debris", "wear",
        "porosity", "spalling", "scuffing", "deformation", "burn mark", "weld lack of fusion", "defect", "flaw"
    ]
}


VIDEOSCOPE_DIRECT_KEYWORDS = [
    "borescope", "videoscope", "endoscope", "endoscopy", "fiberscope",
    "pipe crawler", "pipe camera", "tube inspection camera", "rvi probe"
]


def evaluate_relevance(
    title: str,
    description: str,
    target_domain: str = "UNKNOWN",
    modalities: List[str] = None,
    annotation_types: List[str] = None,
    is_direct_videoscope_declared: bool = False
) -> RelevanceScoreBreakdown:
    """
    Compute transparent, multi-factor explainable relevance score (0-100 total).
    
    Weights:
    - Videoscope Similarity: 0-30 points
    - Domain Match: 0-25 points
    - Modality Match: 0-15 points
    - Defect Utility: 0-15 points
    - Annotation Quality: 0-10 points
    - Provenance Completeness: 0-5 points
    """
    modalities = modalities or []
    annotation_types = annotation_types or []
    full_text = f"{title} {description}".lower()
    explanations = []

    # 1. Videoscope Similarity (0-30)
    videoscope_score = 0.0
    direct_match = False
    for kw in VIDEOSCOPE_DIRECT_KEYWORDS:
        if kw in full_text:
            videoscope_score = 30.0
            direct_match = True
            explanations.append(f"Direct videoscope keyword match: '{kw}'. High visual domain fidelity.")
            break

    if not direct_match:
        if is_direct_videoscope_declared:
            videoscope_score = 25.0
            direct_match = True
            explanations.append("Declared direct videoscope/borescope source.")
        elif any(w in full_text for w in ["pipe", "cavity", "internal", "channel", "tube"]):
            videoscope_score = 15.0
            explanations.append("Related internal-cavity visual context; not confirmed videoscope.")
        else:
            videoscope_score = 5.0
            explanations.append("External benchtop/surface inspection footage. Cross-domain exploratory utility only.")

    # 2. Domain Match (0-25)
    domain_score = 0.0
    target_upper = target_domain.upper() if target_domain else "UNKNOWN"
    
    if target_upper in SEARCH_VOCABULARY:
        matches = [kw for kw in SEARCH_VOCABULARY[target_upper] if kw in full_text]
        if matches:
            domain_score = min(25.0, 10.0 + len(matches) * 5.0)
            explanations.append(f"Target domain '{target_upper}' matched keywords: {matches[:3]}.")
        else:
            domain_score = 8.0
            explanations.append(f"General industrial context without explicit '{target_upper}' keyword matches.")
    else:
        # Check any domain match
        matched_domains = []
        for dom, keywords in SEARCH_VOCABULARY.items():
            if dom in ("GENERAL_INSPECTION", "DEFECT_TERMS"):
                continue
            if any(kw in full_text for kw in keywords):
                matched_domains.append(dom)
        if matched_domains:
            domain_score = 18.0
            explanations.append(f"Matches industrial candidate domains: {matched_domains}.")
        else:
            domain_score = 10.0
            explanations.append("General industrial / surface domain.")

    # 3. Modality Match (0-15)
    modality_score = 0.0
    has_video = any("video" in m.lower() for m in modalities) or "video" in full_text
    has_image = any("image" in m.lower() or "still" in m.lower() for m in modalities) or "image" in full_text

    if has_video:
        modality_score = 15.0
        explanations.append("Continuous video sequences matching videoscope inspection operational modality.")
    elif has_image:
        modality_score = 12.0
        explanations.append("High-resolution still inspection images.")
    else:
        modality_score = 5.0
        explanations.append("Unspecified or non-standard visual modality.")

    # 4. Defect Utility (0-15)
    defect_score = 0.0
    defect_matches = [d for d in SEARCH_VOCABULARY["DEFECT_TERMS"] if d in full_text]
    if defect_matches:
        defect_score = min(15.0, 7.0 + len(defect_matches) * 3.0)
        explanations.append(f"Confirmed defect categories present: {defect_matches[:4]}.")
    else:
        defect_score = 4.0
        explanations.append("Normal/baseline or unclassified anomaly samples.")

    # 5. Annotation Quality (0-10)
    annot_score = 0.0
    annots_lower = [a.lower() for a in annotation_types]
    if any("segmentation" in a or "mask" in a or "pixel" in a for a in annots_lower):
        annot_score = 10.0
        explanations.append("Pixel-level segmentation masks available.")
    elif any("box" in a or "bbox" in a for a in annots_lower):
        annot_score = 8.0
        explanations.append("Bounding box spatial annotations available.")
    elif any("tag" in a or "label" in a or "class" in a for a in annots_lower):
        annot_score = 5.0
        explanations.append("Image-level classification labels available.")
    else:
        annot_score = 2.0
        explanations.append("Unannotated / raw footage requiring human review.")

    # 6. Provenance Completeness (0-5)
    prov_score = 4.0

    total = round(videoscope_score + domain_score + modality_score + defect_score + annot_score + prov_score, 1)
    total = min(100.0, max(0.0, total))

    return RelevanceScoreBreakdown(
        videoscope_similarity=videoscope_score,
        domain_match=domain_score,
        modality_match=modality_score,
        defect_utility=defect_score,
        annotation_quality=annot_score,
        provenance_completeness=prov_score,
        total_score=total,
        is_direct_videoscope=direct_match,
        relevance_explanations=explanations
    )
