"""SBOM parsing and supply-chain dependency risk analysis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config.llm_config import LLMConfig, _extract_content
from backend.config.settings import get_settings

# Simulated threat intelligence — known vulnerable versions
VULNERABLE_PACKAGES: dict[str, str] = {
    "lodash": "4.17.20",
    "axios": "0.21.0",
    "minimist": "1.2.5",
    "node-fetch": "2.6.0",
    "requests": "2.25.0",
    "urllib3": "1.26.4",
    "pillow": "8.1.0",
    "django": "3.1.0",
    "flask": "1.0.0",
    "golang.org/x/crypto": "0.0.0-20210220033148",
    "github.com/gin-gonic/gin": "1.6.0",
}

# Simulated transitive dependency map (direct -> transitive deps)
TRANSITIVE_MAP: dict[str, list[str]] = {
    "express": ["lodash", "qs", "body-parser"],
    "react-scripts": ["webpack", "lodash", "axios"],
    "fastapi": ["starlette", "pydantic"],
    "django": ["sqlparse", "urllib3"],
    "requests": ["urllib3", "certifi"],
    "gin": ["github.com/gin-gonic/gin"],
    "github.com/gin-gonic/gin": ["golang.org/x/crypto"],
}


@dataclass
class Dependency:
    name: str
    version: str
    source_file: str
    ecosystem: str  # python, npm, go
    direct: bool = True
    vulnerable: bool = False
    transitive_of: str | None = None
    risk_level: str = "Low"
    notes: str = ""


@dataclass
class SBOMAnalysis:
    dependencies: list[Dependency] = field(default_factory=list)
    transitive_risks: list[Dependency] = field(default_factory=list)
    groq_assessment: str = ""
    graph_edges: list[dict[str, str]] = field(default_factory=list)


class SBOMParser:
    """Parse dependency manifests and enrich with threat intelligence."""

    def __init__(self, repo_path: Path | str) -> None:
        self.root = Path(repo_path).resolve()

    def parse_repo(self) -> list[Dependency]:
        deps: list[Dependency] = []
        manifests = get_settings().sbom_manifest_files
        req = self.root / "requirements.txt" if "requirements.txt" in manifests else None
        pkg = self.root / "package.json" if "package.json" in manifests else None
        gomod = self.root / "go.mod" if "go.mod" in manifests else None

        if req and req.is_file():
            deps.extend(self._parse_requirements(req))
        if pkg and pkg.is_file():
            deps.extend(self._parse_package_json(pkg))
        if gomod and gomod.is_file():
            deps.extend(self._parse_go_mod(gomod))
        return deps

    def _parse_requirements(self, path: Path) -> list[Dependency]:
        deps: list[Dependency] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            match = re.match(r"^([a-zA-Z0-9_\-.]+)\s*(?:==|>=|<=|~=|!=)?\s*([0-9.]+)?", line)
            if match:
                name = match.group(1).lower().replace("_", "-")
                version = match.group(2) or "unknown"
                deps.append(
                    Dependency(
                        name=name,
                        version=version,
                        source_file=path.name,
                        ecosystem="python",
                    )
                )
        return deps

    def _parse_package_json(self, path: Path) -> list[Dependency]:
        deps: list[Dependency] = []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return deps
        for section in ("dependencies", "devDependencies"):
            for name, version in (data.get(section) or {}).items():
                clean_ver = re.sub(r"[^0-9.]", "", str(version)) or str(version)
                deps.append(
                    Dependency(
                        name=name.lower(),
                        version=clean_ver,
                        source_file=path.name,
                        ecosystem="npm",
                    )
                )
        return deps

    def _parse_go_mod(self, path: Path) -> list[Dependency]:
        deps: list[Dependency] = []
        in_require = False
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            if in_require and stripped == ")":
                in_require = False
                continue
            if stripped.startswith("require ") and "(" not in stripped:
                parts = stripped.replace("require ", "").split()
                if len(parts) >= 2:
                    deps.append(
                        Dependency(
                            name=parts[0],
                            version=parts[1],
                            source_file=path.name,
                            ecosystem="go",
                        )
                    )
                continue
            if in_require:
                parts = stripped.split()
                if len(parts) >= 2:
                    deps.append(
                        Dependency(
                            name=parts[0],
                            version=parts[1],
                            source_file=path.name,
                            ecosystem="go",
                        )
                    )
        return deps

    def _mark_vulnerable(self, deps: list[Dependency]) -> None:
        for dep in deps:
            vuln_ver = VULNERABLE_PACKAGES.get(dep.name) or VULNERABLE_PACKAGES.get(
                dep.name.lower()
            )
            if vuln_ver:
                dep.vulnerable = True
                dep.risk_level = "High"
                dep.notes = f"Known vulnerable version (CVE simulated): <= {vuln_ver}"

    def find_transitive_risks(self, deps: list[Dependency]) -> list[Dependency]:
        """Identify transitive deps where direct package pulls in vulnerable package."""
        risks: list[Dependency] = []
        edges: list[dict[str, str]] = []
        direct_names = {d.name for d in deps}

        for dep in deps:
            transitive_names = TRANSITIVE_MAP.get(dep.name, [])
            for tname in transitive_names:
                edges.append({"from": dep.name, "to": tname, "type": "depends_on"})
                vuln_ver = VULNERABLE_PACKAGES.get(tname)
                if vuln_ver:
                    risks.append(
                        Dependency(
                            name=tname,
                            version=vuln_ver,
                            source_file=dep.source_file,
                            ecosystem=dep.ecosystem,
                            direct=False,
                            vulnerable=True,
                            transitive_of=dep.name,
                            risk_level="Critical" if tname in direct_names else "High",
                            notes=f"Transitive via {dep.name} — vulnerable {tname}<={vuln_ver}",
                        )
                    )
        self._last_edges = edges
        return risks

    def enrich_with_groq(
        self, deps: list[Dependency], llm_config: LLMConfig
    ) -> str:
        """Use Groq to cross-reference deps against threat intelligence."""
        if not deps:
            return "No dependencies found in manifest files."

        dep_summary = [
            {"name": d.name, "version": d.version, "ecosystem": d.ecosystem}
            for d in deps[:30]
        ]
        vuln_list = list(VULNERABLE_PACKAGES.keys())

        prompt = (
            "You are a supply-chain security analyst.\n"
            f"Direct dependencies: {json.dumps(dep_summary)}\n"
            f"Known vulnerable packages: {json.dumps(vuln_list)}\n"
            "In 2-3 sentences, identify the highest-risk transitive supply chain paths "
            "and recommend which packages to upgrade first."
        )
        llm = llm_config.get_llm(large_context=False)
        response = llm.invoke(prompt)
        return _extract_content(response)

    def analyze(self, llm_config: LLMConfig | None = None) -> SBOMAnalysis:
        deps = self.parse_repo()
        self._mark_vulnerable(deps)
        transitive = self.find_transitive_risks(deps)
        edges = getattr(self, "_last_edges", [])

        groq_text = ""
        if llm_config and deps:
            try:
                groq_text = self.enrich_with_groq(deps, llm_config)
            except Exception as exc:
                groq_text = f"Groq enrichment unavailable: {exc}"

        return SBOMAnalysis(
            dependencies=deps,
            transitive_risks=transitive,
            groq_assessment=groq_text,
            graph_edges=edges,
        )
