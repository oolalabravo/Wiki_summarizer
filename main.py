import sys
import json
import re
import ollama
from libzim.reader import Archive
from libzim.search import Query, Searcher
from libzim.suggestion import SuggestionSearcher
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


# -----------------------------
# CLEAN + SANITIZE FUNCTIONS
# -----------------------------

def clean_text_for_ollama(text):
    cleaned = re.sub(r'[^A-Za-z0-9 \n]+', ' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def sanitize_summary_output(text):
    if not text:
        return ""
    cleaned = re.sub(r'[^A-Za-z0-9 ]+', ' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    fallback = [
        "provide the text",
        "paste it",
        "need the excerpt",
    ]
    if any(x in cleaned.lower() for x in fallback):
        return ""

    return cleaned if len(cleaned) > 10 else ""


# -----------------------------
# LOCAL OLLAMA SUMMARIZATION
# -----------------------------

LOCAL_MODEL = "Model_name"    # <-- Change this to any local Ollama model you want

def summarize_with_ollama_chunk(text, max_retries=2):
    cleaned = clean_text_for_ollama(text)
    if not cleaned:
        return "[Error: Text empty after cleaning]"

    prompt = (
        "Summarize this part of a Wikipedia article briefly, clearly, and factually "
        "like Gemini would. Use key points:\n\n" + cleaned
    )

    for attempt in range(max_retries + 1):
        try:
            response = ollama.chat(
                model=LOCAL_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )

            summary = response["message"]["content"].strip()
            if not summary:
                raise ValueError("Empty response")

            return summary

        except Exception:
            if attempt < max_retries:
                # Try reducing the chunk size
                text = text[: len(text) // 2]
                cleaned = clean_text_for_ollama(text)
                prompt = (
                    "Summarize this part of a Wikipedia article briefly:\n\n" + cleaned
                )
            else:
                return "[Error: local model failed]"


# -----------------------------
# PARALLEL SUMMARIZATION PIPELINE
# -----------------------------

def summarize_in_parallel(full_text):
    print("⚙️ Splitting text into 8 chunks...\n")
    chunks = []

    part_size = len(full_text) // 8
    for i in range(8):
        start = i * part_size
        end = (i + 1) * part_size if i < 7 else len(full_text)
        chunks.append(full_text[start:end])

    level1 = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(summarize_with_ollama_chunk, chunk): i
            for i, chunk in enumerate(chunks)
        }

        for future in as_completed(futures):
            raw = future.result()
            clean = sanitize_summary_output(raw)
            level1.append(clean)
            print(f"Chunk summary:\n{clean}\n")

    level1 = [x for x in level1 if x]

    if not level1:
        return "[Error] No valid summaries generated."

    print("🔄 Merging summaries...\n")

    summaries = level1
    while len(summaries) > 2:
        merged = []
        for i in range(0, len(summaries), 2):
            if i + 1 < len(summaries):
                combo = summaries[i] + "\n\n" + summaries[i + 1]
            else:
                combo = summaries[i]

            raw = summarize_with_ollama_chunk(combo)
            clean = sanitize_summary_output(raw)
            merged.append(clean if clean else combo[:500])

        summaries = merged

    final_text = "\n\n".join(summaries)

    final_prompt = (
        "Give a detailed, expanded, 20-line summary with bullet points. "
        "Be factual, clear, and comprehensive:\n\n" + final_text
    )

    try:
        resp = ollama.chat(
            model=LOCAL_MODEL,
            messages=[{"role": "user", "content": final_prompt}],
        )
        final_summary = resp["message"]["content"].strip()
    except Exception as e:
        final_summary = f"[Error in final summary: {e}]"

    print("\n✨ Final Summary:\n")
    print(final_summary)
    return final_summary


# -----------------------------
# WIKIPEDIA ZIM LOADING + SEARCH
# -----------------------------

zim_path = r"F:\programs\Wikipedia-Search engine\wikipedia_en_all_nopic_2025-08\wikipedia_en_all_nopic_2025-08.zim"
zim = Archive(zim_path)
print(f"Loaded ZIM successfully. Main entry: {zim.main_entry.path}\n")

search_string = input("Search: ").strip()

results = []
using_fulltext = False

if zim.has_fulltext_index:
    print(f"\nFull-text search: {search_string}\n")
    q = Query().set_query(search_string)
    searcher = Searcher(zim)
    search = searcher.search(q)

    total = search.getEstimatedMatches()
    results = list(search.getResults(0, min(10, total)))
    using_fulltext = True
else:
    print("\nTitle search only.\n")
    suggestion = SuggestionSearcher(zim).suggest(search_string)
    total = suggestion.getEstimatedMatches()
    results = list(suggestion.getResults(0, min(10, total)))

if not results:
    print("No results.")
    sys.exit()

print(f"Found {total} results. Showing top {len(results)}:\n")

entries = []
for i, r in enumerate(results, 1):
    try:
        entry = zim.get_entry_by_path(r) if using_fulltext else r
        entries.append(entry)
        print(f"{i}. {entry.title}")
    except:
        print(f"{i}. [Invalid entry]")

choice = input("\nChoose article (1-10): ")

if not choice.isdigit() or not (1 <= int(choice) <= len(entries)):
    print("Invalid selection.")
    sys.exit()

selected = entries[int(choice) - 1]

print(f"\nLoading article: {selected.title}\n")
content = bytes(selected.get_item().content).decode("utf-8", errors="ignore")
soup = BeautifulSoup(content, "html.parser")
text = soup.get_text(separator="\n", strip=True)

print("─────────────────────────────────────────────")
print("Summarizing article using local Ollama…\n")

summary = summarize_in_parallel(text)

print("\n─────────────────────────────────────────────")
