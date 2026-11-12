from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from docpipe.evaluate import evaluate
from docpipe.pipeline import Pipeline


def build_pipeline(backend: str) -> Pipeline:
    if backend == "rules":
        return Pipeline()
    from docpipe.classify import LLMClassifier
    from docpipe.extract import LLMExtractor
    from docpipe.llm import AzureOpenAIModel

    model = AzureOpenAIModel()
    return Pipeline(classifier=LLMClassifier(model), extractor=LLMExtractor(model))


def _files(path: Path) -> list[Path]:
    return sorted(p for p in path.iterdir() if p.is_file()) if path.is_dir() else [path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docpipe", description=__doc__)
    parser.add_argument("--backend", choices=("rules", "azure"), default="rules")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser(
        "run", help="process a file or a folder and print one JSON object per document"
    )
    run.add_argument("path", type=Path)
    ev = sub.add_parser("eval", help="score the pipeline against labelled documents")
    ev.add_argument("--docs", type=Path, default=Path("samples/docs"))
    ev.add_argument("--gold", type=Path, default=Path("samples/gold"))
    args = parser.parse_args(argv)

    pipeline = build_pipeline(args.backend)
    if args.command == "run":
        for file in _files(args.path):
            for result in pipeline.run(file):
                print(json.dumps(result.to_dict(), ensure_ascii=False))
    else:
        report = evaluate(pipeline, args.docs, args.gold)
        json.dump(report.summary(), sys.stdout, indent=2, ensure_ascii=False)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
