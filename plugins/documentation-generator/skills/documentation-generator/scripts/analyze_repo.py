"""Inventory a codebase before documenting it.

Answers the questions you would otherwise spend twenty tool calls answering:
what stack is this, where are the data models, where are the routes, what
migrations exist, what is big enough to matter.

    python analyze_repo.py <repo-root> [--json] [--max-depth 4]

The point is speed and coverage, not cleverness. Read the report, then open the
handful of files it points at. Anything it guesses wrong is cheap to correct by
looking; anything it misses entirely is a signal the project is unusual and
deserves a closer read.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "target", "vendor", ".idea",
    ".vscode", "coverage", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "site-packages", ".terraform", "bin", "obj", ".gradle", "Pods",
}

CODE_EXT = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".go": "Go", ".rb": "Ruby",
    ".java": "Java", ".kt": "Kotlin", ".cs": "C#", ".php": "PHP",
    ".rs": "Rust", ".sql": "SQL", ".prisma": "Prisma", ".graphql": "GraphQL",
    ".proto": "Protobuf", ".vue": "Vue", ".svelte": "Svelte",
}

# marker file -> what it tells us
STACK_MARKERS = {
    "requirements.txt": "Python", "pyproject.toml": "Python",
    "package.json": "Node", "go.mod": "Go", "Gemfile": "Ruby",
    "pom.xml": "Java/Maven", "build.gradle": "Java/Gradle",
    "Cargo.toml": "Rust", "composer.json": "PHP", "alembic.ini": "Alembic",
    "manage.py": "Django", "artisan": "Laravel", "schema.prisma": "Prisma",
    "docker-compose.yml": "Docker Compose", "Dockerfile": "Docker",
    "openapi.yaml": "OpenAPI", "openapi.json": "OpenAPI",
}

FRAMEWORK_HINTS = [
    (r"\bfrom\s+fastapi\b|\bFastAPI\(", "FastAPI"),
    (r"\bfrom\s+flask\b|\bFlask\(", "Flask"),
    (r"\bfrom\s+django\b|django\.db", "Django"),
    (r"\bsqlalchemy\b|DeclarativeBase|declarative_base", "SQLAlchemy"),
    (r"\bfrom\s+pydantic\b|BaseModel", "Pydantic"),
    (r"require\(['\"]express|from\s+['\"]express", "Express"),
    (r"@nestjs/", "NestJS"),
    (r"from\s+['\"]next/|next\.config", "Next.js"),
    (r"@Entity\(|javax\.persistence|jakarta\.persistence", "JPA"),
    (r"@RestController|@SpringBootApplication", "Spring"),
    (r"ActiveRecord::Base|ApplicationRecord", "Rails"),
    (r"\bgorm\.Model\b|gorm\.io", "GORM"),
    (r"\bprisma\b", "Prisma"),
    (r"mongoose\.(model|Schema)", "Mongoose"),
    (r"\bcreateSlice\b|configureStore", "Redux Toolkit"),
    (r"from\s+['\"]react['\"]|\bReact\.(FC|Component)\b|useState\(", "React"),
    (r"from\s+['\"]vue['\"]|defineComponent\(", "Vue"),
    (r"@angular/core", "Angular"),
    (r"from\s+['\"]svelte", "Svelte"),
    (r"@tanstack/react-query|useQuery\(|useMutation\(", "TanStack Query"),
    (r"\bcreate\(\s*\)\s*\(|from\s+['\"]zustand", "Zustand"),
    (r"from\s+['\"]react-router|createBrowserRouter", "React Router"),
    (r"\bi18next\b|useTranslation\(", "i18next"),
    (r"from\s+['\"]vitest|describe\(|it\(", "Vitest / Jest"),
    (r"@playwright/test", "Playwright"),
    (r"tailwind\.config|@tailwind\b", "Tailwind"),
    (r"from\s+['\"]axios|axios\.create\(", "Axios"),
    (r"\bcelery\b|@shared_task", "Celery"),
    (r"\bredis\b|aioredis", "Redis"),
    (r"\balembic\b|op\.create_table", "Alembic"),
]

# (label, path regex, content regex) — content regex is optional
ROLE_RULES = [
    ("data model", r"(models?|entities|schema)/", r"class\s+\w+|@Entity|Schema\("),
    ("data model", r"", r"DeclarativeBase|declarative_base|models\.Model|"
                       r"@Entity\b|ActiveRecord::Base|gorm\.Model"),
    ("migration", r"(migrations?|alembic/versions|db/migrate)/", r""),
    ("route / endpoint", r"(routes?|endpoints?|controllers?|api|handlers?)/",
     r"@(app|router)\.(get|post|put|patch|delete)|@(Get|Post|Put|Patch|Delete)"
     r"Mapping|app\.(get|post|put|patch|delete)\(|router\.(get|post|put)"),
    ("route / endpoint", r"", r"@(app|router)\.(get|post|put|patch|delete)\(|"
                             r"@RestController|@RequestMapping"),
    ("service / domain logic", r"(services?|domain|usecases?|core)/", r""),
    ("background worker", r"(workers?|jobs?|tasks?|celery)/", r""),
    ("configuration", r"(config|settings|conf)/", r""),
    ("test", r"(tests?|spec|__tests__)/", r""),
    ("frontend component", r"(components?|pages?|views?|screens?)/", r""),
]

AUTH_SIGNALS = [
    (r"\bjwt\b|jsonwebtoken|PyJWT|python-jose", "JWT"),
    (r"\boauth2?\b|OpenID|openid", "OAuth / OIDC"),
    (r"express-session|SessionMiddleware|flask_login", "sessions"),
    (r"require_role|@PreAuthorize|hasRole|\bRBAC\b|has_permission",
     "role checks"),
    (r"\bbcrypt\b|argon2|passlib|password_hash", "password hashing"),
    (r"\bapi[_-]?key\b", "API keys"),
    (r"\bcan_(read|edit|write|delete|approve|view)\b|policy\.py",
     "policy module"),
    (r"required_scopes|\bscopes\b\s*[:=]", "scopes"),
    (r"\bmfa\b|\btotp\b|two[_-]?factor", "MFA"),
]

ROUTE_PATTERNS = [
    # python decorators — @app.get(...), @router.post(...), @some_router.put(...)
    r"@\w*(?:app|router|api|bp)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)",
    # express / nest — app.get(...), router.post(...), shipmentRouter.put(...)
    r"\b\w*(?:[Aa]pp|[Rr]outer|[Aa]pi)\.(get|post|put|patch|delete)"
    r"\(\s*['\"]([^'\"]+)",
    # spring
    r"@(Get|Post|Put|Patch|Delete)Mapping\(\s*(?:value\s*=\s*)?['\"]([^'\"]+)",
    # go — chi / gorilla / echo
    r"\.(Get|Post|Put|Patch|Delete)\(\s*[\"`]([^\"`]+)",
]

MODEL_PATTERNS = [
    r"__tablename__\s*=\s*['\"](\w+)['\"]",          # SQLAlchemy
    r"class\s+(\w+)\s*\(\s*models\.Model",            # Django
    r"@Entity\b[\s\S]{0,120}?class\s+(\w+)",          # JPA
    r"model\s+(\w+)\s*\{",                            # Prisma
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"`]?(\w+)",  # raw SQL
]


def walk(root: str, max_depth: int):
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith(".")]
        if depth > max_depth:
            dirnames[:] = []
        for name in filenames:
            yield dirpath, name, os.path.join(dirpath, name)


def read_head(path: str, limit: int = 60_000) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def analyze(root: str, max_depth: int) -> dict:
    root = os.path.abspath(root)
    languages: Counter = Counter()
    markers: list[str] = []
    frameworks: set[str] = set()
    roles: defaultdict[str, list] = defaultdict(list)
    routes: list[tuple[str, str, str]] = []
    tables: list[tuple[str, str]] = []
    biggest: list[tuple[int, str]] = []
    migrations: list[str] = []
    openapi: list[str] = []
    auth_signals: set[str] = set()
    frontend_packages: set[str] = set()

    for dirpath, name, full in walk(root, max_depth):
        rel = os.path.relpath(full, root).replace(os.sep, "/")
        ext = os.path.splitext(name)[1].lower()

        if name in STACK_MARKERS:
            markers.append(f"{STACK_MARKERS[name]}  ({rel})")
        if name in ("openapi.yaml", "openapi.json", "swagger.json"):
            openapi.append(rel)
        if name == "package.json" and "/" in rel:
            frontend_packages.add(rel.rsplit("/", 1)[0])

        if ext not in CODE_EXT:
            continue

        try:
            size = os.path.getsize(full)
        except OSError:
            continue
        languages[CODE_EXT[ext]] += 1
        biggest.append((size, rel))

        text = read_head(full)
        if not text:
            continue

        for pattern, label in FRAMEWORK_HINTS:
            if re.search(pattern, text):
                frameworks.add(label)
        for pattern, label in AUTH_SIGNALS:
            if re.search(pattern, text):
                auth_signals.add(label)

        lowered = rel.lower()
        for label, path_re, content_re in ROLE_RULES:
            if path_re and not re.search(path_re, lowered):
                continue
            if content_re and not re.search(content_re, text):
                continue
            if rel not in [r for r, _ in roles[label]]:
                roles[label].append((rel, size))
            break

        if re.search(r"(migrations?|alembic/versions|db/migrate)/", lowered):
            migrations.append(rel)

        for pattern in ROUTE_PATTERNS:
            for m in re.finditer(pattern, text):
                verb, path = m.group(1).upper(), m.group(2)
                routes.append((verb, path, rel))

        for pattern in MODEL_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                tables.append((m.group(1), rel))

    biggest.sort(reverse=True)
    return {
        "root": root,
        "languages": languages.most_common(),
        "stack_markers": sorted(set(markers)),
        "frameworks": sorted(frameworks),
        "roles": {k: sorted(v, key=lambda x: -x[1])[:25] for k, v in roles.items()},
        "routes": routes,
        "tables": sorted(set(tables)),
        "migrations": sorted(migrations),
        "openapi": openapi,
        "largest_files": [(s, p) for s, p in biggest[:25]],
        "auth_signals": sorted(auth_signals),
        "frontend_packages": sorted(frontend_packages),
    }


def suggest_documents(a: dict) -> list[tuple[str, str]]:
    """Which of the document types this codebase can actually support.

    Deliberately conservative: proposing a schema document for a service with
    no persistence invites a fabricated one, which is worse than none.
    """
    out = []
    if a["tables"] or a["migrations"]:
        out.append(("Database Schema",
                    f"{len(a['tables'])} tables/models, "
                    f"{len(a['migrations'])} migration files"))
    if a["routes"] or a["openapi"]:
        n = len({(v, p) for v, p, _ in a["routes"]})
        note = f"{n} distinct routes" + (", plus an OpenAPI spec"
                                         if a["openapi"] else "")
        if n and n < 5:
            note += " — small enough to fold into the architecture document"
        out.append(("API Contracts", note))

    multi_lang = len([n for _, n in a["languages"] if n >= 3]) > 1
    if (a["roles"].get("service / domain logic") or a["roles"].get("data model")
            or a["frontend_packages"] or multi_lang):
        why = "services, models and layering are identifiable"
        if a["frontend_packages"]:
            why = (f"{len(a['frontend_packages'])} package(s) — cross-package "
                   f"contracts are worth documenting")
        elif multi_lang:
            why = "more than one language in one system"
        out.append(("Architecture Overview", why))

    if a["routes"] and (a["roles"].get("service / domain logic")
                        or a["roles"].get("background worker") or multi_lang):
        out.append(("Sequence / flow document",
                    "entry points call into services — flows are traceable"))

    if a["auth_signals"]:
        out.append(("Auth & authorisation",
                    f"detected: {', '.join(sorted(a['auth_signals']))}"))

    if not out:
        out.append(("Architecture Overview",
                    "nothing else detected — start here and read manually"))
    return out


def report(a: dict) -> str:
    L = []
    add = L.append
    add("=" * 74)
    add(f"REPOSITORY  {a['root']}")
    add("=" * 74)

    add("\nLANGUAGES")
    for lang, n in a["languages"]:
        add(f"  {n:>5}  {lang}")

    if a["stack_markers"]:
        add("\nSTACK MARKERS")
        for m in a["stack_markers"]:
            add(f"  {m}")

    if a["frameworks"]:
        add("\nFRAMEWORKS DETECTED")
        add("  " + ", ".join(a["frameworks"]))

    add("\nSUGGESTED DOCUMENTS")
    for name, why in suggest_documents(a):
        add(f"  {name:<28}  {why}")

    if a["tables"]:
        add(f"\nDATA MODELS / TABLES  ({len(a['tables'])})")
        for name, path in a["tables"][:40]:
            add(f"  {name:<32}  {path}")
        if len(a["tables"]) > 40:
            add(f"  … and {len(a['tables']) - 40} more")

    if a["routes"]:
        add(f"\nROUTES  ({len(a['routes'])})")
        seen = set()
        for verb, path, src in a["routes"][:60]:
            key = (verb, path)
            if key in seen:
                continue
            seen.add(key)
            add(f"  {verb:<7} {path:<44} {src}")
        if len(a["routes"]) > 60:
            add(f"  … and {len(a['routes']) - 60} more")

    add("\nFILES BY ROLE")
    for role in ("data model", "route / endpoint", "service / domain logic",
                 "background worker", "configuration", "migration",
                 "frontend component", "test"):
        items = a["roles"].get(role) or []
        if not items:
            continue
        add(f"  {role.upper()}  ({len(items)} shown)")
        for path, size in items[:12]:
            add(f"      {size:>8,}  {path}")

    if a["migrations"]:
        add(f"\nMIGRATIONS  ({len(a['migrations'])})")
        for m in a["migrations"][-10:]:
            add(f"  {m}")
        add("  (most recent last — read these for the current schema state)")

    if a["openapi"]:
        add("\nOPENAPI SPEC")
        for o in a["openapi"]:
            add(f"  {o}   ← read this before hand-rolling API docs")

    add("\nLARGEST CODE FILES  (usually where the real logic is)")
    for size, path in a["largest_files"][:15]:
        add(f"  {size:>8,}  {path}")

    add("\n" + "-" * 74)
    add("Next: open the files above that match the document you are writing.")
    add("This report is a map, not a substitute for reading the code.")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--max-depth", type=int, default=5)
    args = ap.parse_args()

    a = analyze(args.root, args.max_depth)
    if args.json:
        a["suggested_documents"] = suggest_documents(a)
        print(json.dumps(a, indent=2))
    else:
        try:
            print(report(a))
        except UnicodeEncodeError:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            print(report(a))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
