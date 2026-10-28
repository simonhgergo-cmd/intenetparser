from __future__ import annotations

import argparse
import logging
import shutil
import sys
import time
from pathlib import Path

from . import pipeline as P
from .export import export_llm_pack, export_table
from .report import write_report

EXAMPLE = Path(__file__).resolve().parent.parent / "config.example.toml"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="iparse", description="Map what people talk about, struggle with and love.")
    ap.add_argument("-c", "--config", default="config.toml")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create config.toml from the example")
    c = sub.add_parser("collect", help="fetch posts from enabled sources")
    c.add_argument("--source", action="append", help="only this source (repeatable; ignores 'enabled')")
    a = sub.add_parser("analyze", help="run keyword analysis on new posts")
    a.add_argument("--all", action="store_true", help="re-analyse everything")
    r = sub.add_parser("report", help="write the HTML report")
    r.add_argument("--out")
    e = sub.add_parser("export", help="export data")
    e.add_argument("format", choices=["csv", "jsonl", "llm"])
    e.add_argument("--out")
    e.add_argument("--max-chars", type=int, default=60_000, help="llm: max characters per pack file")
    e.add_argument("--include-all", action="store_true", help="llm: include posts with no detected signal")
    l = sub.add_parser("llm", help="run exported LLM packs through a local OpenAI-compatible model")
    l.add_argument("--url", default="http://localhost:11434/v1", help="e.g. Ollama or LM Studio")
    l.add_argument("--model", required=True)
    l.add_argument("--packs", help="pack folder (default: <exports>/llm)")
    l.add_argument("--api-key", default="")
    run = sub.add_parser("run", help="collect -> analyze -> report -> export on a schedule, forever")
    run.add_argument("--every", help="interval like 30m, 6h, 1d (default from config)")
    run.add_argument("--once", action="store_true")
    sub.add_parser("stats", help="show what is in the database")

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    if args.cmd == "init":
        if Path(args.config).exists():
            print(f"{args.config} already exists")
            return 1
        shutil.copy(EXAMPLE, args.config)
        print(f"Wrote {args.config}. Edit it, then run: iparse run --once")
        return 0

    if not Path(args.config).exists():
        print(f"No {args.config}. Run `iparse init` first.", file=sys.stderr)
        return 1
    cfg = P.load_config(args.config)
    report_path, export_dir = P.output_paths(cfg)
    store = P.open_store(cfg)
    try:
        if args.cmd == "collect":
            P.collect(cfg, store, args.source)
        elif args.cmd == "analyze":
            print(f"Analysed {P.analyze(cfg, store, args.all)} posts")
        elif args.cmd == "report":
            path = write_report(P.build_aggregate(cfg, store), Path(args.out) if args.out else report_path)
            print(f"Report: {path}")
        elif args.cmd == "export":
            _export(cfg, store, args, export_dir)
        elif args.cmd == "llm":
            from .llm import run_packs
            packs = Path(args.packs) if args.packs else export_dir / "llm"
            for p in run_packs(packs, args.url, args.model, args.api_key):
                print(f"Wrote {p}")
        elif args.cmd == "stats":
            c = store.counts()
            print(f"{c['posts']} posts, {c['analyzed']} analysed")
            for s, n in sorted(c["by_source"].items(), key=lambda kv: -kv[1]):
                print(f"  {s:15} {n}")
        elif args.cmd == "run":
            interval = P.parse_interval(args.every or cfg.get("schedule", {}).get("every", "6h"))
            while True:
                started = time.time()
                P.collect(cfg, store)
                P.analyze(cfg, store)
                agg = P.build_aggregate(cfg, store)
                write_report(agg, report_path)
                export_llm_pack(store.joined(), export_dir / "llm", agg)
                logging.info("Cycle done. Report: %s", report_path)
                if args.once:
                    break
                sleep = max(60, interval - (time.time() - started))
                logging.info("Next cycle in %.0f minutes", sleep / 60)
                time.sleep(sleep)
    finally:
        store.close()
    return 0


def _export(cfg, store, args, export_dir: Path) -> None:
    if args.format in ("csv", "jsonl"):
        out = Path(args.out) if args.out else export_dir / f"posts.{args.format}"
        n = export_table(store.joined(), out, args.format)
        print(f"Wrote {n} rows to {out}")
        return
    out = Path(args.out) if args.out else export_dir / "llm"
    files = export_llm_pack(store.joined(), out, P.build_aggregate(cfg, store),
                            max_chars=args.max_chars, only_signals=not args.include_all)
    print(f"Wrote {len(files)} files to {out}/ (pack_*.md = per-post review, summary.md = product ideas)")


if __name__ == "__main__":
    raise SystemExit(main())
