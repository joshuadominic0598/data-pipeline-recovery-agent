"""Policy is code, not a model's opinion. Unknown edits fail closed."""

import ast
import difflib
import hashlib
import json

from .config import TEMPLATE

RECIPES = {
    "column_alias": {
        "cause": "schema_drift",
        "setting": "SOURCE_TEMP_COLUMN",
        "value": "temp_c",
        "approval": False,
        "tool": "inspect_schema",
        "label": "Use contracted temperature alias",
        "impact": "Map temp_c to temperature_c; preserve every value and business rule.",
    },
    "exact_dedup": {
        "cause": "duplicates",
        "setting": "DEDUPLICATE_EXACT",
        "value": True,
        "approval": False,
        "tool": "profile_records",
        "label": "Remove exact connector replays",
        "impact": "Remove byte-equivalent duplicate events. Conflicting versions remain blocked.",
    },
    "replay_partition": {
        "cause": "missing_partition",
        "setting": "BACKFILL_PARTITION",
        "value": True,
        "approval": False,
        "tool": "inspect_manifest",
        "label": "Replay verified landed partition",
        "impact": "Use the same-date immutable landing snapshot after verifying its checksum.",
    },
    "quarantine_invalid": {
        "cause": "invalid_values",
        "setting": "QUARANTINE_INVALID",
        "value": True,
        "approval": True,
        "tool": "profile_records",
        "label": "Quarantine impossible records",
        "impact": "Exclude invalid events from consumption; preserve them in a quarantine data product. Changes data treatment.",
    },
    "registry_mirror": {
        "cause": "dependency_down",
        "setting": "DEPENDENCY_PROVIDER",
        "value": "mirror",
        "approval": True,
        "tool": "probe_dependency",
        "label": "Use the verified registry mirror",
        "impact": "Switch a workflow dependency to a version-matched mirror. Requires owner approval.",
    },
}


def patch(recipe):
    spec = RECIPES[recipe]
    source = TEMPLATE.read_text()
    tree = ast.parse(source)
    target = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == spec["setting"]
    )
    lines = source.splitlines(keepends=True)
    lines[target.lineno - 1] = (
        f"{spec['setting']} = {json.dumps(spec['value']) if isinstance(spec['value'], str) else repr(spec['value'])}\n"
    )
    candidate = "".join(lines)
    verify_patch(candidate, recipe)
    diff = "".join(
        difflib.unified_diff(
            source.splitlines(True),
            candidate.splitlines(True),
            fromfile="a/pipeline/transform.py",
            tofile="b/pipeline/transform.py",
        )
    )
    return candidate, diff


def verify_patch(candidate, recipe):
    spec = RECIPES[recipe]
    tree = ast.parse(candidate)
    baseline = ast.parse(TEMPLATE.read_text())
    changed = False
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == spec["setting"]
        ):
            if ast.literal_eval(node.value) != spec["value"]:
                raise ValueError("Repair setting differs from approved runbook")
            original = next(
                n
                for n in baseline.body
                if isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == spec["setting"]
            )
            node.value = original.value
            changed = True
    if not changed or ast.dump(tree) != ast.dump(baseline):
        raise ValueError("Edit changes unapproved code, business logic, architecture or dependencies")


def eligible(recipe, observations):
    if recipe not in RECIPES:
        return False
    o = observations.get(RECIPES[recipe]["tool"], {})
    if recipe == "column_alias":
        return (
            o.get("alias_contract") == {"temp_c": "temperature_c"}
            and "temp_c" in o.get("columns", [])
            and "temperature_c" not in o.get("columns", [])
        )
    if recipe == "exact_dedup":
        return o.get("exact_replays", 0) > 0 and o.get("conflicting_events") == 0
    if recipe == "replay_partition":
        return (
            o.get("inbox_exists") is False
            and o.get("landing_verified") is True
            and o.get("same_partition") is True
        )
    if recipe == "quarantine_invalid":
        return 0 < o.get("invalid_count", 0) <= 10
    if recipe == "registry_mirror":
        return o.get("primary_available") is False and o.get("mirror_verified") is True
    return False


def proposal_digest(code, inputs):
    return hashlib.sha256((code + "\n" + inputs).encode()).hexdigest()
