import json
import os
import ast
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed
from itertools import islice
from typing import Iterable, List, Tuple
from tqdm import tqdm

INPUT_PATH = "data/cc-chinese/part-00000"
OUTPUT_DIR = "outputs/cc-chinese/raw"
HTML_DIR = os.path.join(OUTPUT_DIR, "html")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "records.jsonl")
HTML_LIST_PATH = os.path.join(OUTPUT_DIR, "html_files.txt")


def count_lines(path: str) -> int:
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def chunks(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            return
        yield batch


def process_batch(args: Tuple[int, List[str], str]) -> List[Tuple[int, int, str]]:
    start_idx, lines, html_dir = args
    results: List[Tuple[int, int, str]] = []

    for offset, raw in enumerate(lines):
        idx = start_idx + offset + 1  # 1-based file naming
        raw = raw.strip()
        if not raw:
            continue

        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            # 兼容 Python 字典字符串（单引号）
            try:
                obj = ast.literal_eval(raw)
            except Exception:
                continue

        if not isinstance(obj, dict):
            continue

        html = obj.get("html")
        img_num = obj.get("img_num")

        if not isinstance(html, str):
            continue

        html_filename = f"{idx}.html"
        html_path = os.path.join(html_dir, html_filename)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        results.append((idx, int(img_num) if img_num is not None else 0, html_path))

    return results


def main() -> None:
    os.makedirs(HTML_DIR, exist_ok=True)

    workers = max(1, (os.cpu_count() or 1) - 1)
    batch_size = 200

    total_lines = count_lines(INPUT_PATH)
    total_batches = (total_lines + batch_size - 1) // batch_size if total_lines > 0 else 0

    futures = []
    line_base = 0

    with open(INPUT_PATH, "r", encoding="utf-8") as fin, ProcessPoolExecutor(max_workers=workers) as ex:
        for batch in tqdm(
            chunks(fin, batch_size),
            total=total_batches,
            desc="Submitting batches",
            dynamic_ncols=True,
        ):
            futures.append(ex.submit(process_batch, (line_base, batch, HTML_DIR)))
            line_base += len(batch)

        merged: List[Tuple[int, int, str]] = []
        for fut in tqdm(
            as_completed(futures),
            total=total_batches,
            desc="Processing batches",
            dynamic_ncols=True,
        ):
            merged.extend(fut.result())

    merged.sort(key=lambda x: x[0])

    with open(MANIFEST_PATH, "w", encoding="utf-8") as fout:
        with open(HTML_LIST_PATH, "w", encoding="utf-8") as html_f:
            for _, img_num, html_path in merged:
                html_f.write(html_path + "\n")
                rec = {
                    "img_num": img_num,
                    "html_path": html_path,
                }
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(
        f"Done. html_dir={HTML_DIR}, manifest={MANIFEST_PATH}, "
        f"html_list={HTML_LIST_PATH}, count={len(merged)}"
    )


if __name__ == "__main__":
    main()
