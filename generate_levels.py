#!/usr/bin/env python3
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "LevelDesignConfig.json"
ALL_CATEGORIES_PATH = ROOT / "AllCategories.json"
CATEGORIES_DIR = ROOT / "Categories"
OUTPUT_PATH = ROOT / "Levels.json"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_range(value) -> Tuple[int, int]:
    if isinstance(value, int):
        return value, value
    if isinstance(value, str) and "-" in value:
        start, end = value.split("-", 1)
        return int(start), int(end)
    return int(value), int(value)


def _parse_level_key(key: str) -> List[int]:
    if not key.startswith("level"):
        return []
    range_part = key[len("level"):]
    if "-" in range_part:
        start, end = range_part.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(range_part)]


def _choose_grid(grid_sizes: List[str]) -> Dict[str, int]:
    chosen = random.choice(grid_sizes)
    rows, cols = chosen.lower().split("x", 1)
    return {"Rows": int(rows), "Column": int(cols)}


def _difficulty_to_hard_ratio(difficulty: int) -> float:
    max_ratio = random.uniform(0.6, 0.7)
    return max(0.0, ((difficulty - 1) / 9.0) * max_ratio)


def _load_words(category: str, difficulty: str) -> List[str]:
    path = CATEGORIES_DIR / f"{category}-{difficulty}.json"
    if not path.exists() and difficulty == "hard":
        path = CATEGORIES_DIR / f"{category}-normal.json"
    return _load_json(path)


def _pick_words(
    word_count: int,
    allowed_categories: List[str],
    normal_categories: List[str],
    hard_categories: List[str],
    hard_ratio: float,
    max_word_length: int,
) -> Tuple[List[str], str]:
    hard_target = round(word_count * hard_ratio)
    normal_target = word_count - hard_target

    normal_pool = [c for c in allowed_categories if c in normal_categories] or allowed_categories
    hard_pool = [c for c in allowed_categories if c in hard_categories] or allowed_categories

    cache: Dict[Tuple[str, str], List[str]] = {}
    chosen_words: List[str] = []
    used_words = set()
    categories_used = set()

    def pick_from(category: str, difficulty: str) -> str:
        key = (category, difficulty)
        if key not in cache:
            cache[key] = list(_load_words(category, difficulty))
        options = [word for word in cache[key] if len(word) <= max_word_length]
        if not options:
            raise ValueError(
                f"No words <= {max_word_length} letters for {category} ({difficulty})."
            )
        random.shuffle(options)
        for word in options:
            if word not in used_words:
                used_words.add(word)
                return word
        return random.choice(options)

    for _ in range(normal_target):
        category = random.choice(normal_pool)
        categories_used.add(category)
        chosen_words.append(pick_from(category, "normal"))

    for _ in range(hard_target):
        category = random.choice(hard_pool)
        categories_used.add(category)
        chosen_words.append(pick_from(category, "hard"))

    category_name = (
        next(iter(categories_used)) if len(categories_used) == 1 else "Mixed category"
    )
    random.shuffle(chosen_words)
    return chosen_words, category_name


def build_levels(config: dict) -> dict:
    all_categories = _load_json(ALL_CATEGORIES_PATH)
    normal_categories = all_categories.get("normal", [])
    hard_categories = all_categories.get("hard", [])
    default_categories = sorted(set(normal_categories + hard_categories))

    levels_output: Dict[str, dict] = {}
    for key, level_config in config.items():
        for level_number in _parse_level_key(key):
            words_count_raw = level_config.get("words_count", 0)
            min_words, max_words = _parse_range(words_count_raw)
            word_count = random.randint(min_words, max_words)

            difficulty = level_config.get("difficulty")
            if difficulty is None:
                difficulty = random.randint(1, 10)

            hard_ratio = _difficulty_to_hard_ratio(int(difficulty))

            grid_sizes = level_config.get("grid_size", [])
            if not grid_sizes:
                raise ValueError(f"Missing grid_size for {key}")
            grid_size = _choose_grid(grid_sizes)

            allowed_categories = level_config.get("category") or default_categories

            max_word_length = max(1, min(grid_size["Rows"], grid_size["Column"]) - 2)
            words, category_name = _pick_words(
                word_count,
                allowed_categories,
                normal_categories,
                hard_categories,
                hard_ratio,
                max_word_length,
            )

            levels_output[f"Level{level_number}"] = {
                "words": words,
                "GridSize": grid_size,
                "CategoryName": category_name,
            }

    return levels_output


def main() -> None:
    config = _load_json(CONFIG_PATH)
    levels = build_levels(config)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(levels, handle, indent=2)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
