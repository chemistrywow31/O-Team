"""O-Team CLI — Build a pipeline from a prompt chain.

Usage:
    # Single .md file (--- separated prompts):
    python -m scripts.chain prompts.md [--json]

    # Directory with numbered .md files:
    python -m scripts.chain ./my-chain/ [--json]

    # Directory with chain.yaml (advanced):
    python -m scripts.chain ./my-chain/ [--json]

    # Interactive (prompts as JSON array from stdin):
    python -m scripts.chain --interactive --prompts '<json>' [--json]
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

from . import utils


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_chain(source_path: str) -> dict:
    """Detect what kind of prompt chain source this is, without building.

    Returns a description of what was found so the user can confirm.
    """
    source = utils.resolve_path(source_path)

    if not source.exists():
        return {"success": False, "error": f"Path not found: {source}"}

    if source.is_file() and source.suffix == ".md":
        try:
            content = source.read_text(encoding="utf-8")
        except Exception as e:
            return {"success": False, "error": f"Cannot read file: {e}"}

        # Strip frontmatter
        stripped = content
        if stripped.lstrip().startswith("---"):
            after_first = stripped.lstrip()[3:]
            end_pos = after_first.find("\n---")
            if end_pos != -1:
                candidate = after_first[:end_pos].strip()
                if candidate and ":" in candidate:
                    stripped = after_first[end_pos + 4:]

        sections = [s.strip() for s in re.split(r"\n---\s*\n", stripped) if s.strip()]
        steps = []
        for i, section in enumerate(sections):
            heading = _extract_heading(section)
            preview = section[:80].replace("\n", " ")
            if len(section) > 80:
                preview += "..."
            steps.append({
                "index": i + 1,
                "name": heading or f"Step {i+1}",
                "preview": preview,
            })

        return {
            "success": True,
            "format": "single-file",
            "source": str(source),
            "name": source.stem,
            "step_count": len(sections),
            "steps": steps,
        }

    if source.is_file() and source.suffix in (".yaml", ".yml"):
        try:
            data = utils.read_yaml(source)
        except Exception:
            return {"success": False, "error": f"Cannot parse YAML: {source}"}
        nodes = data.get("nodes", [])
        return {
            "success": True,
            "format": "chain-yaml",
            "source": str(source),
            "name": data.get("name", source.stem),
            "step_count": len(nodes),
            "steps": [
                {
                    "index": i + 1,
                    "name": n.get("id", f"Step {i+1}"),
                    "preview": (n.get("prompt", "") or n.get("prompt_file", ""))[:80],
                }
                for i, n in enumerate(nodes)
            ],
        }

    if source.is_dir():
        chain_yaml = source / "chain.yaml"
        if chain_yaml.exists():
            return detect_chain(str(chain_yaml))

        # Scan for numbered .md files
        pattern_named = re.compile(r"^(\d+)-(.+)\.md$")
        pattern_bare = re.compile(r"^(\d+)\.md$")
        candidates = []
        for f in sorted(source.iterdir()):
            if not f.is_file():
                continue
            m = pattern_named.match(f.name)
            if m:
                heading = ""
                try:
                    heading = _extract_heading(f.read_text(encoding="utf-8"))
                except Exception:
                    pass
                candidates.append({
                    "index": int(m.group(1)),
                    "name": heading or m.group(2),
                    "file": f.name,
                })
                continue
            m = pattern_bare.match(f.name)
            if m:
                heading = ""
                try:
                    heading = _extract_heading(f.read_text(encoding="utf-8"))
                except Exception:
                    pass
                candidates.append({
                    "index": int(m.group(1)),
                    "name": heading or f"Step {m.group(1)}",
                    "file": f.name,
                })

        if not candidates:
            # Fall back to any .md files
            for f in sorted(source.iterdir()):
                if f.is_file() and f.suffix == ".md":
                    heading = ""
                    try:
                        heading = _extract_heading(f.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                    candidates.append({
                        "index": len(candidates) + 1,
                        "name": heading or f.stem,
                        "file": f.name,
                    })

        if not candidates:
            return {"success": False, "error": f"No .md files found in {source}"}

        candidates.sort(key=lambda c: c["index"])
        return {
            "success": True,
            "format": "directory",
            "source": str(source),
            "name": source.name,
            "step_count": len(candidates),
            "steps": [
                {
                    "index": c["index"],
                    "name": c["name"],
                    "preview": c["file"],
                }
                for c in candidates
            ],
        }

    return {"success": False, "error": f"Unsupported path type: {source}"}


def build_chain(source_path: str, output_path: str | None = None) -> dict:
    """Build a pipeline from a prompt chain source.

    Supports three input formats (auto-detected):
    1. Single .md file — sections separated by --- lines
    2. Directory with numbered .md files (NN.md or NN-name.md)
    3. Directory with chain.yaml (advanced config)

    Args:
        source_path: Path to .md file, directory, or chain.yaml
        output_path: (optional) output pipeline YAML path

    Returns:
        dict with success status and pipeline info
    """
    source = utils.resolve_path(source_path)

    # Single .md file → parse sections
    if source.is_file() and source.suffix == ".md":
        return _build_from_single_file(source, output_path)

    # YAML file → advanced config
    if source.is_file() and source.suffix in (".yaml", ".yml"):
        return _build_from_yaml(source, output_path)

    # Directory
    if source.is_dir():
        chain_yaml = source / "chain.yaml"
        if chain_yaml.exists():
            return _build_from_yaml(chain_yaml, output_path)
        # Try numbered .md files first, fall back to any .md files
        result = _build_from_directory(source, output_path)
        if result["success"]:
            return result
        return _build_from_directory(source, output_path, strict_naming=False)

    return {"success": False, "error": f"Path not found: {source}"}


def build_chain_from_prompts(
    prompts: list[str],
    name: str = "chain",
    output_path: str | None = None,
    models: list[str] | None = None,
    efforts: list[str] | None = None,
) -> dict:
    """Build a pipeline from a list of prompt strings.

    Used by the interactive flow in /ot:chain.

    Args:
        prompts: List of prompt texts (one per step)
        name: Pipeline name
        output_path: (optional) output pipeline YAML path
        models: Optional per-step model IDs (empty string = skip)
        efforts: Optional per-step effort levels (empty string = skip)

    Returns:
        dict with success status and pipeline info
    """
    if not prompts:
        return {"success": False, "error": "No prompts provided"}

    valid_efforts = {"low", "medium", "high", "xhigh", "max", ""}

    nodes = []
    for i, prompt_text in enumerate(prompts):
        text = prompt_text.strip()
        if not text:
            continue
        step_name = _extract_heading(text) or f"step-{i+1}"
        is_last = (i == len(prompts) - 1)
        node = {
            "id": f"{i+1:02d}-{_slugify_name(step_name)}",
            "mode": "gate" if is_last else "auto",
            "prompt": text,
            "timeout": utils.DEFAULT_TIMEOUT,
        }

        if models and i < len(models):
            m = (models[i] or "").strip()
            if m:
                node["model"] = m

        if efforts and i < len(efforts):
            e = (efforts[i] or "").strip()
            if e:
                if e not in valid_efforts:
                    return {
                        "success": False,
                        "error": f"Step {i+1}: invalid effort '{e}' (must be low/medium/high/xhigh/max)",
                    }
                node["effort"] = e

        nodes.append(node)

    if not nodes:
        return {"success": False, "error": "All prompts were empty"}

    return _write_pipeline(name, "", nodes, output_path)


# ---------------------------------------------------------------------------
# Single .md file parser
# ---------------------------------------------------------------------------


def _build_from_single_file(md_file: Path, output_path: str | None) -> dict:
    """Build pipeline from a single .md file with --- separators.

    Format:
        prompt text for step 1...

        ---

        prompt text for step 2...

        ---

        prompt text for step 3...

    Optional: first # heading in each section becomes the step name.
    """
    try:
        content = md_file.read_text(encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"Cannot read file: {e}"}

    # Strip leading YAML frontmatter if present (--- ... ---)
    stripped = content
    if stripped.lstrip().startswith("---"):
        after_first = stripped.lstrip()[3:]
        end_pos = after_first.find("\n---")
        if end_pos != -1:
            # Check if this looks like YAML frontmatter (has key: value lines)
            candidate = after_first[:end_pos].strip()
            if candidate and ":" in candidate:
                stripped = after_first[end_pos + 4:]

    # Split by --- on its own line
    sections = re.split(r"\n---\s*\n", stripped)

    prompts = []
    for section in sections:
        text = section.strip()
        if text:
            prompts.append(text)

    if not prompts:
        return {"success": False, "error": f"No prompt sections found in {md_file}"}

    if len(prompts) == 1:
        return {
            "success": False,
            "error": f"Only 1 section found. Use --- to separate steps. Example:\n\n"
                     f"Step 1 prompt...\n\n---\n\nStep 2 prompt...",
        }

    name = md_file.stem
    nodes = []
    for i, prompt_text in enumerate(prompts):
        step_name = _extract_heading(prompt_text) or f"step-{i+1}"
        is_last = (i == len(prompts) - 1)
        nodes.append({
            "id": f"{i+1:02d}-{_slugify_name(step_name)}",
            "mode": "gate" if is_last else "auto",
            "prompt": prompt_text,
            "timeout": utils.DEFAULT_TIMEOUT,
        })

    return _write_pipeline(name, "", nodes, output_path)


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------


def _build_from_directory(
    directory: Path,
    output_path: str | None,
    strict_naming: bool = True,
) -> dict:
    """Build pipeline by scanning .md files in a directory.

    strict_naming=True: tries numbered patterns (NN-name.md or NN.md)
    strict_naming=False: any .md file, sorted alphabetically
    """
    if strict_naming:
        # Try NN-name.md first, then NN.md
        pattern_named = re.compile(r"^(\d+)-(.+)\.md$")
        pattern_bare = re.compile(r"^(\d+)\.md$")
        candidates = []
        for f in sorted(directory.iterdir()):
            if not f.is_file():
                continue
            m = pattern_named.match(f.name)
            if m:
                candidates.append({
                    "index": int(m.group(1)),
                    "name": m.group(2),
                    "path": f,
                })
                continue
            m = pattern_bare.match(f.name)
            if m:
                candidates.append({
                    "index": int(m.group(1)),
                    "name": f"step-{m.group(1)}",
                    "path": f,
                })
        if not candidates:
            return {
                "success": False,
                "error": f"No numbered .md files found in {directory}",
            }
        candidates.sort(key=lambda c: c["index"])
    else:
        candidates = []
        for f in sorted(directory.iterdir()):
            if f.is_file() and f.suffix == ".md" and f.name != "chain.yaml":
                candidates.append({
                    "index": len(candidates) + 1,
                    "name": f.stem,
                    "path": f,
                })
        if not candidates:
            return {
                "success": False,
                "error": f"No .md files found in {directory}",
            }

    name = directory.name
    nodes = []
    for i, c in enumerate(candidates):
        is_last = (i == len(candidates) - 1)
        node_id = f"{c['index']:02d}-{_slugify_name(c['name'])}"

        # Try to extract a heading from the file for a better name
        prompt_path = c["path"].resolve()
        heading = ""
        try:
            heading = _extract_heading(c["path"].read_text(encoding="utf-8"))
        except Exception:
            pass
        if heading:
            node_id = f"{c['index']:02d}-{_slugify_name(heading)}"

        nodes.append({
            "id": node_id,
            "mode": "gate" if is_last else "auto",
            "prompt_file": str(prompt_path),
            "timeout": utils.DEFAULT_TIMEOUT,
        })

    return _write_pipeline(name, "", nodes, output_path)


# ---------------------------------------------------------------------------
# chain.yaml parser (advanced)
# ---------------------------------------------------------------------------


def _build_from_yaml(chain_yaml: Path, output_path: str | None) -> dict:
    """Build pipeline from a chain.yaml file (advanced users)."""
    try:
        data = utils.read_yaml(chain_yaml)
    except Exception as e:
        return {"success": False, "error": f"YAML parse failed: {e}"}

    if not isinstance(data, dict):
        return {"success": False, "error": "chain.yaml must be a mapping"}

    name = data.get("name", chain_yaml.parent.name)
    objective = data.get("objective", "")
    nodes = data.get("nodes", [])

    if not nodes:
        return {"success": False, "error": "chain.yaml has no nodes"}

    pipeline_nodes = []
    for i, node in enumerate(nodes):
        prompt = node.get("prompt", "").strip()
        prompt_file = node.get("prompt_file", "").strip()

        # Resolve prompt_file to absolute path
        resolved_prompt_file = ""
        if prompt_file and not prompt:
            pf = Path(prompt_file)
            if not pf.is_absolute():
                pf = (chain_yaml.parent / pf).resolve()
            if not pf.exists():
                return {
                    "success": False,
                    "error": f"Node {i+1}: prompt_file not found: {pf}",
                }
            resolved_prompt_file = str(pf)

        node_id = node.get("id") or f"{i+1:02d}-{_slugify_name(node.get('name', 'step'))}"
        mode = node.get("mode", "auto" if i < len(nodes) - 1 else "gate")

        pipeline_node = {
            "id": node_id,
            "mode": mode,
            "timeout": node.get("timeout", utils.DEFAULT_TIMEOUT),
        }

        if prompt:
            pipeline_node["prompt"] = prompt
        if resolved_prompt_file:
            pipeline_node["prompt_file"] = resolved_prompt_file
        elif prompt_file:
            pipeline_node["prompt_file"] = prompt_file
        if node.get("identity", "").strip():
            pipeline_node["identity"] = node["identity"]
        if node.get("rules"):
            resolved_rules = []
            for rp_str in node["rules"]:
                rp = Path(rp_str)
                if not rp.is_absolute():
                    rp = (chain_yaml.parent / rp).resolve()
                resolved_rules.append(str(rp))
            pipeline_node["rules"] = resolved_rules
        if node.get("team"):
            pipeline_node["team"] = node["team"]
            pipeline_node["team_path"] = node.get("team_path", "")

        pipeline_nodes.append(pipeline_node)

    return _write_pipeline(name, objective, pipeline_nodes, output_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_heading(text: str) -> str:
    """Extract the first # heading from text, if any."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _slugify_name(name: str) -> str:
    """Simple slugify for node names."""
    slug = re.sub(r"[^a-z0-9\-]", "-", name.lower().strip())
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-") or "step"


def _write_pipeline(
    name: str,
    objective: str,
    nodes: list[dict],
    output_path: str | None,
) -> dict:
    """Write the pipeline YAML file."""
    slug = utils.slugify(name)
    if not slug:
        slug = "chain-" + hashlib.md5(name.encode()).hexdigest()[:6]

    pipeline_data = {
        "version": "1",
        "name": name,
        "slug": slug,
        "objective": objective,
        "created_at": utils.now_local_iso(),
        "nodes": nodes,
    }

    if output_path:
        out = utils.resolve_path(output_path)
    else:
        project_dir = utils.ensure_project_dir()
        out = project_dir / utils.PIPELINES_DIR_NAME / f"{slug}.yaml"

    utils.write_yaml(out, pipeline_data)

    return {
        "success": True,
        "pipeline": pipeline_data,
        "output_path": str(out),
        "node_count": len(nodes),
        "nodes": [
            {
                "id": n["id"],
                "mode": n["mode"],
                "type": "team" if n.get("team") else "prompt",
            }
            for n in nodes
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build pipeline from prompt chain"
    )
    parser.add_argument(
        "source", nargs="?", default=None,
        help="Path to .md file, directory, or chain.yaml",
    )
    parser.add_argument(
        "--detect", action="store_true", default=False,
        help="Detect format only — do not build pipeline",
    )
    parser.add_argument(
        "--prompts", default=None,
        help="JSON array of prompt strings (for interactive mode)",
    )
    parser.add_argument(
        "--models", default=None,
        help="JSON array of model IDs per step (parallel to --prompts; empty string = skip)",
    )
    parser.add_argument(
        "--efforts", default=None,
        help="JSON array of effort levels per step (low/medium/high/xhigh/max; empty = skip)",
    )
    parser.add_argument(
        "--name", default="chain",
        help="Pipeline name (used with --prompts)",
    )
    parser.add_argument("--output", default=None, help="Output pipeline YAML path")
    parser.add_argument("--json", action="store_true", default=False)
    args = parser.parse_args()

    if args.detect:
        if not args.source:
            result = {"success": False, "error": "Provide a source path with --detect"}
        else:
            result = detect_chain(args.source)
    elif args.prompts:
        import json as _json
        try:
            prompts = _json.loads(args.prompts)
            models = _json.loads(args.models) if args.models else None
            efforts = _json.loads(args.efforts) if args.efforts else None
        except _json.JSONDecodeError as e:
            result = {"success": False, "error": f"Invalid JSON: {e}"}
        else:
            result = build_chain_from_prompts(
                prompts, args.name, args.output,
                models=models, efforts=efforts,
            )
    elif args.source:
        result = build_chain(args.source, args.output)
    else:
        result = {"success": False, "error": "Provide a source path or --prompts"}

    if args.json:
        utils.print_json(result)
    else:
        if result["success"]:
            print(f"Chain pipeline created: {result['output_path']}")
            print(f"   Nodes: {result['node_count']}")
            for n in result["nodes"]:
                mode_icon = ">" if n["mode"] == "auto" else "|"
                print(f"   {mode_icon} {n['id']} ({n['type']})")
        else:
            print(f"Error: {result.get('error')}")

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
