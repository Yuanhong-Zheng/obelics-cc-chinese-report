"""End-to-end OBELICS pipeline driver for cc-chinese sample data.

Runs DOMTreeSimplificator -> PreExtractionSimplificator -> image URL extraction ->
img2dataset download -> urls_to_images -> node-level & doc-level filtering, on a
configurable subset of the cc-chinese HTML files produced by 1_parse.py.
"""

import argparse
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup
from datasets import Dataset, load_from_disk
from PIL import Image, ImageFile

from obelics.processors import (
    DOMTreeSimplificator,
    PreExtractionSimplificator,
    CommonCrawlWebDocumentExtractor as WebDocumentExtractor,
    WebDocumentFilteringDocLevel,
    WebDocumentFilteringNodeLevel,
)
from obelics.utils import (
    DIGITS_RE,
    FLAGGED_WORDS,
    NON_PRINTING_CHARACTERS_RE,
    PUNCTUATION,
    SPECIAL_CHARACTERS,
    STOPWORDS,
    UNICODE_PUNCTUATION,
)

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_cc_chinese")

CANONICAL_RE = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', re.I)


def extract_canonical_url(html: str, fallback: str) -> str:
    m = CANONICAL_RE.search(html)
    if m:
        return m.group(1)
    try:
        soup = BeautifulSoup(html, "lxml")
        link = soup.find("link", rel="canonical")
        if link and link.get("href"):
            return link["href"]
    except Exception:
        pass
    return fallback


def build_html_dataset(html_files, limit):
    rows = {"html": [], "url": []}
    for idx, path in enumerate(html_files[:limit]):
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        url = extract_canonical_url(html, fallback=f"http://cc-chinese.local/doc/{idx}")
        rows["html"].append(html)
        rows["url"].append(url)
    return Dataset.from_dict(rows)


def make_filter_node_level(filtering_params, args):
    return WebDocumentFilteringNodeLevel(
        cond_check_format=filtering_params["cond_check_format"],
        valid_formats=filtering_params["valid_formats"],
        cond_check_size_image=filtering_params["cond_check_size_image"],
        original_width_min_cutoff=filtering_params["original_width_min_cutoff"],
        original_width_max_cutoff=filtering_params["original_width_max_cutoff"],
        original_height_min_cutoff=filtering_params["original_height_min_cutoff"],
        original_height_max_cutoff=filtering_params["original_height_max_cutoff"],
        rendered_width_min_cutoff=filtering_params["rendered_width_min_cutoff"],
        rendered_width_max_cutoff=filtering_params["rendered_width_max_cutoff"],
        rendered_height_min_cutoff=filtering_params["rendered_height_min_cutoff"],
        rendered_height_max_cutoff=filtering_params["rendered_height_max_cutoff"],
        aspect_ratio_max_cutoff=filtering_params["aspect_ratio_max_cutoff"],
        cond_remove_non_printing_characters=filtering_params["cond_remove_non_printing_characters"],
        non_printing_characters_re=NON_PRINTING_CHARACTERS_RE,
        cond_standardize_whitespace=filtering_params["cond_standardize_whitespace"],
        cond_check_number_words_node_level=filtering_params["cond_check_number_words_node_level"],
        strip_characters=SPECIAL_CHARACTERS,
        number_words_node_level_min_cutoff=filtering_params["number_words_node_level_min_cutoff"],
        number_words_node_level_max_cutoff=filtering_params["number_words_node_level_max_cutoff"],
        cond_check_character_repetition_ratio_node_level=filtering_params["cond_check_character_repetition_ratio_node_level"],
        character_repetition_length_node_level=filtering_params["character_repetition_length_node_level"],
        character_repetition_node_level_max_cutoff=filtering_params["character_repetition_node_level_max_cutoff"],
        cond_check_word_repetition_ratio_node_level=filtering_params["cond_check_word_repetition_ratio_node_level"],
        word_repetition_length_node_level=filtering_params["word_repetition_length_node_level"],
        word_repetition_node_level_max_cutoff=filtering_params["word_repetition_node_level_max_cutoff"],
        cond_check_special_character_ratio_node_level=filtering_params["cond_check_special_character_ratio_node_level"],
        special_character_ratio_node_level_max_cutoff=filtering_params["special_character_ratio_node_level_max_cutoff"],
        cond_check_stopword_ratio_node_level=filtering_params["cond_check_stopword_ratio_node_level"],
        stopwords=STOPWORDS,
        stopword_ratio_node_level_min_cutoff=filtering_params["stopword_ratio_node_level_min_cutoff"],
        cond_check_flagged_word_ratio_node_level=filtering_params["cond_check_flagged_word_ratio_node_level"],
        flagged_words=FLAGGED_WORDS,
        flagged_word_ratio_node_level_max_cutoff=filtering_params["flagged_word_ratio_node_level_max_cutoff"],
        cond_check_punctuation_ratio_node_level=filtering_params["cond_check_punctuation_ratio_node_level"],
        min_number_words_to_check_punctuation_ratio_node_level=filtering_params["min_number_words_to_check_punctuation_ratio_node_level"],
        punctuation=PUNCTUATION,
        punctuation_ratio_node_level_min_cutoff=filtering_params["punctuation_ratio_node_level_min_cutoff"],
        cond_check_common_word_ratio_node_level=filtering_params["cond_check_common_word_ratio_node_level"],
        path_common_words=args.path_common_words,
        common_word_ratio_node_level_min_cutoff=filtering_params["common_word_ratio_node_level_min_cutoff"],
        cond_check_lang_id_node_level=filtering_params["cond_check_lang_id_node_level"],
        path_lang_id_model=args.path_lang_id_model,
        lang_id_node_level_min_cutoff=filtering_params["lang_id_node_level_min_cutoff"],
        cond_check_perplexity_score_node_level=filtering_params["cond_check_perplexity_score_node_level"],
        digits_re=DIGITS_RE,
        unicode_punctuation=UNICODE_PUNCTUATION,
        path_sentencepiece_model=args.path_sentencepiece_model,
        path_kenlm_model=args.path_kenlm_model,
        perplexity_score_node_level_max_cutoff=filtering_params["perplexity_score_node_level_max_cutoff"],
    )


def make_filter_doc_level(filtering_params, args):
    return WebDocumentFilteringDocLevel(
        cond_check_number_images=filtering_params["cond_check_number_images"],
        number_images_min_cutoff=filtering_params["number_images_min_cutoff"],
        number_images_max_cutoff=filtering_params["number_images_max_cutoff"],
        cond_check_number_words_doc_level=filtering_params["cond_check_number_words_doc_level"],
        strip_characters=SPECIAL_CHARACTERS,
        number_words_doc_level_min_cutoff=filtering_params["number_words_doc_level_min_cutoff"],
        number_words_doc_level_max_cutoff=filtering_params["number_words_doc_level_max_cutoff"],
        cond_check_character_repetition_ratio_doc_level=filtering_params["cond_check_character_repetition_ratio_doc_level"],
        character_repetition_length_doc_level=filtering_params["character_repetition_length_doc_level"],
        character_repetition_doc_level_max_cutoff=filtering_params["character_repetition_doc_level_max_cutoff"],
        cond_check_word_repetition_ratio_doc_level=filtering_params["cond_check_word_repetition_ratio_doc_level"],
        word_repetition_length_doc_level=filtering_params["word_repetition_length_doc_level"],
        word_repetition_doc_level_max_cutoff=filtering_params["word_repetition_doc_level_max_cutoff"],
        cond_check_special_character_ratio_doc_level=filtering_params["cond_check_special_character_ratio_doc_level"],
        special_character_ratio_doc_level_max_cutoff=filtering_params["special_character_ratio_doc_level_max_cutoff"],
        cond_check_stopword_ratio_doc_level=filtering_params["cond_check_stopword_ratio_doc_level"],
        stopwords=STOPWORDS,
        stopword_ratio_doc_level_min_cutoff=filtering_params["stopword_ratio_doc_level_min_cutoff"],
        cond_check_flagged_word_ratio_doc_level=filtering_params["cond_check_flagged_word_ratio_doc_level"],
        flagged_words=FLAGGED_WORDS,
        flagged_word_ratio_doc_level_max_cutoff=filtering_params["flagged_word_ratio_doc_level_max_cutoff"],
        cond_check_punctuation_ratio_doc_level=filtering_params["cond_check_punctuation_ratio_doc_level"],
        punctuation=PUNCTUATION,
        punctuation_ratio_doc_level_min_cutoff=filtering_params["punctuation_ratio_doc_level_min_cutoff"],
        cond_check_common_word_ratio_doc_level=filtering_params["cond_check_common_word_ratio_doc_level"],
        path_common_words=args.path_common_words,
        common_word_ratio_doc_level_min_cutoff=filtering_params["common_word_ratio_doc_level_min_cutoff"],
        cond_check_lang_id_doc_level=filtering_params["cond_check_lang_id_doc_level"],
        path_lang_id_model=args.path_lang_id_model,
        lang_id_doc_level_min_cutoff=filtering_params["lang_id_doc_level_min_cutoff"],
        cond_check_perplexity_score_doc_level=filtering_params["cond_check_perplexity_score_doc_level"],
        non_printing_characters_re=NON_PRINTING_CHARACTERS_RE,
        digits_re=DIGITS_RE,
        unicode_punctuation=UNICODE_PUNCTUATION,
        path_sentencepiece_model=args.path_sentencepiece_model,
        path_kenlm_model=args.path_kenlm_model,
        perplexity_score_doc_level_max_cutoff=filtering_params["perplexity_score_doc_level_max_cutoff"],
    )


def dump_jsonl(dataset, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        for ex in dataset:
            slim = {
                "url": ex.get("url"),
                "texts": ex.get("texts"),
                "images_urls": ex.get("images_urls") if "images_urls" in ex else ex.get("images"),
                "num_found": ex.get("num_found"),
                "num_not_found": ex.get("num_not_found"),
                "general_metadata": ex.get("general_metadata"),
            }
            f.write(json.dumps(slim, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html-list", default="/ytech_m2v8_hdd/workspace/kling_mm/zhengyuanhong/interleave/outputs/cc-chinese/raw/html_files.txt")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--num-proc", type=int, default=4)
    parser.add_argument("--out-dir", default="/ytech_m2v8_hdd/workspace/kling_mm/zhengyuanhong/interleave/outputs/cc-chinese/obelics")
    parser.add_argument("--filter-config", default="/ytech_m2v8_hdd/workspace/kling_mm/zhengyuanhong/interleave/OBELICS/obelics/configs/config_filter_web_documents_zh.yaml")
    parser.add_argument("--download-images", action="store_true", help="invoke img2dataset to download images")
    parser.add_argument("--image-size", type=int, default=256)
    parser.add_argument("--thread-count", type=int, default=32)
    # filter assets - unused when corresponding cond_* is False, but Filter constructor reads them
    parser.add_argument("--path-common-words", default="/ytech_m2v8_hdd/workspace/kling_mm/zhengyuanhong/interleave/OBELICS/assets/common_words_stub.json")
    parser.add_argument("--path-lang-id-model", default="")
    parser.add_argument("--path-sentencepiece-model", default="")
    parser.add_argument("--path-kenlm-model", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tmp").mkdir(exist_ok=True)

    # Stub common_words file (filter requires path even when check is disabled).
    cw_path = Path(args.path_common_words)
    cw_path.parent.mkdir(parents=True, exist_ok=True)
    if not cw_path.exists():
        cw_path.write_text("{}", encoding="utf-8")

    logger.info("Building HTML dataset (first %d docs)", args.limit)
    with open(args.html_list, "r", encoding="utf-8") as f:
        html_files = [ln.strip() for ln in f if ln.strip()]
    html_files = [p if os.path.isabs(p) else os.path.join("/ytech_m2v8_hdd/workspace/kling_mm/zhengyuanhong/interleave", p) for p in html_files]
    html_dataset = build_html_dataset(html_files, args.limit)
    logger.info("Built html_dataset with %d rows", len(html_dataset))

    # 1) DOM simplification + node extraction -> texts/images columns
    dom = DOMTreeSimplificator(
        strip_multiple_linebreaks=True,
        strip_multiple_spaces=True,
        remove_html_comments=True,
        replace_line_break_tags=True,
        unwrap_tags=True,
        strip_tags=True,
        strip_special_divs=True,
        remove_dates=True,
        remove_empty_leaves=True,
        unnest_nodes=True,
        remake_tree=True,
        css_rules=["[class~='footer']", "[class~='site-info']"],
        css_rules_replace_with_text={"[class~='more-link']": "\n\nEND_OF_DOCUMENT_TOKEN_TO_BE_REPLACED\n\n"},
    )
    pre_extract = PreExtractionSimplificator(
        only_text_image_nodes=True, format_texts=True, merge_consecutive_text_nodes=True
    )

    image_urls_file = str(out_dir / "image_urls.txt")
    extractor = WebDocumentExtractor(
        html_dataset=html_dataset,
        dom_tree_simplificator=dom,
        pre_extraction_simplificator=pre_extract,
        path_save_dir_dataset=str(out_dir / "web_documents_raw"),
        num_proc=args.num_proc,
        path_save_file_image_urls=image_urls_file,
        path_save_dir_downloaded_images=str(out_dir / "tmp" / "downloaded_images"),
        thread_count=args.thread_count,
        number_sample_per_shard=10_000,
        image_size=args.image_size,
        resize_mode="no",
        path_save_dir_tmp_datasets_images=str(out_dir / "tmp" / "tmp_image_dataset"),
        path_save_dir_dataset_images=str(out_dir / "image_dataset"),
        path_save_file_map_url_idx=str(out_dir / "map_url_idx.json"),
        num_proc_urls_to_images=args.num_proc,
        path_save_dir_sharded_dataset=str(out_dir / "sharded_dataset"),
        shard_size=1000,
    )

    logger.info("Step 1: html -> texts/images")
    # Stash urls to re-attach after the destructive remove_columns map inside html_to_web_documents.
    original_urls = list(html_dataset["url"])
    extractor.html_to_web_documents()
    extractor.dataset = extractor.dataset.add_column("url", original_urls)
    logger.info("Step 2: gather image urls")
    extractor.get_image_urls()
    extractor.save_dataset()
    logger.info("Raw web documents saved to %s", out_dir / "web_documents_raw")

    if args.download_images:
        logger.info("Step 3a: img2dataset download")
        extractor.download_images()
        logger.info("Step 3b: build image dataset from downloaded shards")
        extractor.create_dataset_images()
        logger.info("Step 3c: replace urls with image bytes in records")
        extractor.urls_to_images()
        # Save with-images version
        with_images_path = out_dir / "web_documents_with_images"
        extractor.dataset.save_to_disk(str(with_images_path))
        logger.info("With-image dataset saved to %s", with_images_path)
        dataset_for_filter = extractor.dataset
    else:
        logger.info("Skipping image download; converting URL strings to None for filter compatibility.")

        def _strip_images(example):
            example["images_urls"] = list(example["images"])
            example["images"] = [None for _ in example["images"]]
            return example

        dataset_for_filter = extractor.dataset.map(_strip_images, num_proc=args.num_proc)

    # 4) Filter
    with open(args.filter_config, "r") as f:
        filtering_params = yaml.load(f, Loader=yaml.FullLoader)

    logger.info("Step 4a: node-level filter")
    f_node = make_filter_node_level(filtering_params, args)
    filtered = dataset_for_filter.map(f_node, num_proc=args.num_proc)

    if not args.download_images:
        # node-level filter zeroed out `images` to avoid PIL access; for doc-level
        # restore url strings so the "at least one image" check has something to count.
        def _restore_images(example):
            example["images"] = list(example["images_urls"]) if "images_urls" in example else example["images"]
            return example
        filtered = filtered.map(_restore_images, num_proc=args.num_proc)

    logger.info("Step 4b: doc-level filter")
    f_doc = make_filter_doc_level(filtering_params, args)
    final_ds = filtered.filter(f_doc, num_proc=args.num_proc)

    final_dir = out_dir / "web_documents_filtered"
    if final_dir.exists():
        shutil.rmtree(final_dir)
    final_ds.save_to_disk(str(final_dir))

    jsonl_path = out_dir / "web_documents_filtered.jsonl"
    dump_jsonl(final_ds, str(jsonl_path))

    logger.info("Raw docs:      %d", len(dataset_for_filter))
    logger.info("After filter:  %d", len(final_ds))
    logger.info("Saved HF ds: %s", final_dir)
    logger.info("Saved jsonl: %s", jsonl_path)


if __name__ == "__main__":
    sys.exit(main())
