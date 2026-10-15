
import csv
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT = (
    PROJECT_ROOT.parent
    / "KeeAInu-training"
    / "near_duplicate_report.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "data" / "segmentation" / "review"

GROUPS_CSV = OUTPUT_DIR / "duplicate_group_review.csv"
SUMMARY_JSON = OUTPUT_DIR / "duplicate_group_summary.json"

# Conservative starting threshold. These are candidates for review,
# not automatic proof that two images are duplicates.
PHASH_MAX = 4
DHASH_MAX = 4


def main():
    if not REPORT.is_file():
        raise FileNotFoundError(f"Missing duplicate report: {REPORT}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Union-find builds candidate groups from strong similarity edges.
    parent = {}
    rank = {}

    def find(item):
        parent.setdefault(item, item)
        rank.setdefault(item, 0)

        if parent[item] != item:
            parent[item] = find(parent[item])

        return parent[item]

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return

        if rank[ra] < rank[rb]:
            ra, rb = rb, ra

        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    strong_edges = []
    ambiguous_cross_split = 0
    cross_split_candidates = 0

    with REPORT.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            image_a = row["image_a"]
            image_b = row["image_b"]
            split_a = row["split_a"]
            split_b = row["split_b"]
            phash = int(row["phash_distance"])
            dhash = int(row["dhash_distance"])
            cross_split = row["cross_split"].strip().lower() == "true"

            if cross_split:
                cross_split_candidates += 1

            if phash <= PHASH_MAX and dhash <= DHASH_MAX:
                union(image_a, image_b)
                strong_edges.append({
                    "image_a": image_a,
                    "split_a": split_a,
                    "image_b": image_b,
                    "split_b": split_b,
                    "phash_distance": phash,
                    "dhash_distance": dhash,
                    "cross_split": cross_split,
                    "review_status": "NEEDS_VISUAL_REVIEW",
                })
            elif cross_split and (phash <= 8 or dhash <= 4):
                ambiguous_cross_split += 1

    components = {}
    for image in list(parent):
        components.setdefault(find(image), []).append(image)

    # Only components containing multiple images become candidate groups.
    group_for_image = {}
    group_number = 0

    for members in components.values():
        if len(members) < 2:
            continue

        group_number += 1
        group_id = f"DUP-{group_number:05d}"

        for image in members:
            group_for_image[image] = group_id

    with GROUPS_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        fields = [
            "group_id",
            "image_a",
            "split_a",
            "image_b",
            "split_b",
            "phash_distance",
            "dhash_distance",
            "cross_split",
            "review_status",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for edge in strong_edges:
            edge["group_id"] = group_for_image.get(
                edge["image_a"], ""
            )
            writer.writerow(edge)

    group_sizes = Counter(group_for_image.values())

    summary = {
        "source_report": str(REPORT),
        "candidate_threshold": {
            "phash_max": PHASH_MAX,
            "dhash_max": DHASH_MAX,
            "logic": "Both thresholds must be satisfied",
        },
        "cross_split_candidates_in_source_report": cross_split_candidates,
        "strong_candidate_edges": len(strong_edges),
        "strong_candidate_groups": len(group_sizes),
        "images_in_strong_candidate_groups": len(group_for_image),
        "ambiguous_cross_split_candidates": ambiguous_cross_split,
        "warning": (
            "Groups are similarity candidates, not confirmed duplicates. "
            "Review before using them to change dataset splits."
        ),
        "outputs": {
            "review_csv": str(GROUPS_CSV),
        },
    }

    SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
