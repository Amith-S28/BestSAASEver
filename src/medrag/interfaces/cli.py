"""MedRAG Command Line Interface (CLI) tool."""

import argparse
import asyncio
import json
from pathlib import Path
import sys

# Ensure src and project root are in python path
src_root = Path(__file__).resolve().parent.parent.parent
project_root = src_root.parent
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def app() -> None:
    """Main CLI entrypoint for MedRAG institutional operations."""
    parser = argparse.ArgumentParser(
        prog="medrag",
        description="MedRAG v2.0: Institutional Clinical AI Intelligence SaaS Platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Operational sub-command")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start FastAPI HTTP and SSE server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Binding host address")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    serve_parser.add_argument("--reload", action="store_true", help="Enable live auto-reload")

    # Health command
    subparsers.add_parser("health", help="Check subsystem health and telemetry")

    # Lint command
    subparsers.add_parser("lint", help="Verify pure domain layer boundary with AST linter")

    # Benchmark command
    subparsers.add_parser("benchmark", help="Run MedQA clinical faithfulness benchmark")

    # Airgap command
    subparsers.add_parser("airgap", help="Generate airgap packaging checksum manifest")

    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn
        print(f"Starting MedRAG v2.0 Institutional API on http://{args.host}:{args.port}")
        uvicorn.run("medrag.interfaces.api.app:app", host=args.host, port=args.port, reload=args.reload)

    elif args.command == "health":
        from medrag.interfaces.api.routes.health import health_check
        res = asyncio.run(health_check())
        print(json.dumps(res, indent=2))

    elif args.command == "lint":
        import subprocess
        res = subprocess.run([sys.executable, "scripts/lint_domain_imports.py"])
        sys.exit(res.returncode)

    elif args.command == "benchmark":
        from scripts.run_medqa_benchmarks import evaluate_medqa_benchmarks
        res = asyncio.run(evaluate_medqa_benchmarks())
        print(json.dumps(res, indent=2))

    elif args.command == "airgap":
        from scripts.package_airgap_bundle import generate_airgap_manifest
        manifest = generate_airgap_manifest()
        print(json.dumps(manifest, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    app()
