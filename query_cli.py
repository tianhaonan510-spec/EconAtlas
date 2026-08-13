# -*- coding: utf-8 -*-
import argparse
import json
from pathlib import Path
from services.query_service import build_batch_response, build_query_response
def load_batch(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "queries" in data:
        data = data["queries"]
    if not isinstance(data, list):
        raise ValueError("Batch file must be a JSON list or an object with a 'queries' list.")
    return data
def main() -> None:
    parser = argparse.ArgumentParser(description="EconAtlas standardized JSON query CLI")
    parser.add_argument("--country")
    parser.add_argument("--indicator")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--frequency", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--batch", default=None, help="Path to a JSON file with batch query items")
    parser.add_argument("--output", default=None, help="Optional output JSON path")
    args = parser.parse_args()
    if args.batch:
        result = build_batch_response(load_batch(args.batch))
    else:
        if not args.country or not args.indicator:
            parser.error("--country and --indicator are required unless --batch is used")
        result = build_query_response(
            country=args.country,
            indicator=args.indicator,
            start=args.start,
            end=args.end,
            frequency=args.frequency,
            source=args.source,
        )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)
if __name__ == "__main__":
    main()
