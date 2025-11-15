import requests
import sys
import json
import re
from libzim.reader import Archive
from libzim.search import Query, Searcher
from libzim.suggestion import SuggestionSearcher
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


OPENROUTER_API_KEY = "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"  # <-- Replace with your actual key
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def clean_text_for_openrouter(text):
    """Clean text for OpenRouter input: allow alphabets, numbers, spaces."""
    cleaned = re.sub(r'[^A-Za-z0-9 \n]+', ' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def sanitize_summary_output(text):
    if not text or text.startswith("[Error"):
        return ""
    cleaned = re.sub(r'[^A-Za-z0-9 ]+', ' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    fallback_phrases = [
        "please provide the text",
        "need the excerpt",
        "paste it here",
    ]
    if any(phrase in cleaned.lower() for phrase in fallback_phrases):
        return ""
    if len(cleaned) < 10:
        return ""
    return cleaned


def summarize_with_openrouter_chunk(text, max_retries=2):
    cleaned_text = clean_text_for_openrouter(text)
    if not cleaned_text:
        return "[Error: Cleaned text empty]"

    prompt_message = (
        "Summarize this part of a Wikipedia article briefly, clearly, and factually — like Gemini would. Use key points:\n\n"
        + cleaned_text
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "nvidia/nemotron-nano-12b-v2-vl:free",  # Updated model here
        "messages": [
            {"role": "user", "content": prompt_message}
        ],
        "extra_body": {"reasoning": {"enabled": True}}  # Enable reasoning for detailed responses (optional)
    }

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                data=json.dumps(data),
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            summary = result["choices"][0]["message"]["content"].strip()
            if summary == "" or "please provide the text" in summary.lower():
                raise ValueError("Empty or fallback response from OpenRouter")
            return summary
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                text = text[: len(text) // 2]
                cleaned_text = clean_text_for_openrouter(text)
                if not cleaned_text:
                    return "[Error: Text too small after halving]"
                data["messages"][0]["content"] = (
                    "Summarize this part of a Wikipedia article briefly, clearly, and factually — like Gemini would. Use key points:\n\n"
                    + cleaned_text
                )
            else:
                return "[Error: Request timed out]"
        except Exception as e:
            return f"[OpenRouter error: {e}]"


def summarize_in_parallel(full_text):
    print("⚙️ Splitting text into 8 chunks for parallel summarization...\n")
    chunks = []
    part_size = len(full_text) // 8
    for i in range(8):
        start = i * part_size
        end = (i + 1) * part_size if i < 7 else len(full_text)
        chunks.append(full_text[start:end])

    level1_summaries = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(summarize_with_openrouter_chunk, chunk): i for i, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            raw_result = future.result()
            sanitized_result = sanitize_summary_output(raw_result)
            level1_summaries.append(sanitized_result)
            print(f"Level 1 summary chunk (sanitized):\n{sanitized_result}\n")

    level1_summaries = [s for s in level1_summaries if s]

    if not level1_summaries:
        print("[Error] No valid summaries obtained from chunks.")
        return "[Error] Unable to generate summary from the article."

    print("✅ Level 1 summaries completed. Merging into fewer summaries...\n")

    summaries_to_merge = level1_summaries
    while len(summaries_to_merge) > 2:
        merged = []
        for i in range(0, len(summaries_to_merge), 2):
            if i + 1 < len(summaries_to_merge):
                combo_text = summaries_to_merge[i] + "\n\n" + summaries_to_merge[i + 1]
            else:
                combo_text = summaries_to_merge[i]
            raw_merged_summary = summarize_with_openrouter_chunk(combo_text)
            sanitized_merged_summary = sanitize_summary_output(raw_merged_summary)
            if sanitized_merged_summary:
                merged.append(sanitized_merged_summary)
            else:
                merged.append(combo_text[:500])  # fallback to partial text
            print(f"Merged summary part:\n{merged[-1]}\n")
        summaries_to_merge = merged

    final_input = "\n\n".join(summaries_to_merge)
    detailed_prompt = (
        "You are an expert assistant. "
        "Please provide a detailed and expanded summary of the following text. "
        "Make it about 20 lines long, structured as clear bullet points or numbered points, "
        "including key facts, explanations, and insights. "
        "The tone should be factual, comprehensive, and easy to understand.\n\n"
        + final_input
    )

    data = {
        "model": "nvidia/nemotron-nano-12b-v2-vl:free",  # Updated model here for final summary
        "messages": [
            {"role": "user", "content": detailed_prompt}
        ],
        "extra_body": {"reasoning": {"enabled": True}}  # Enable reasoning here as well
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps(data),
            timeout=300,
        )
        response.raise_for_status()
        result = response.json()
        detailed_summary = result["choices"][0]["message"]["content"].strip()
        if not detailed_summary:
            detailed_summary = "[Error] Empty detailed summary returned."
    except Exception as e:
        detailed_summary = f"[OpenRouter error during detailed summary: {e}]"

    print("✨ Detailed Final Summary:\n")
    print(detailed_summary)
    return detailed_summary


# Load ZIM file safely
zim_path = r"F:\programs\Wikipedia-Search engine\wikipedia_en_all_nopic_2025-08\wikipedia_en_all_nopic_2025-08\wikipedia_en_all_nopic_2025-08.zim"
zim = Archive(zim_path)
print(f"✅ Loaded Wikipedia ZIM file successfully!\nMain entry: {zim.main_entry.path}\n")

search_string = input("🔍 Enter your search query: ").strip()

results = []
total = 0
using_fulltext = False

if zim.has_fulltext_index:
    print(f"\n📖 Searching for '{search_string}' using full-text index...\n")
    query = Query().set_query(search_string)
    searcher = Searcher(zim)
    search = searcher.search(query)
    total = search.getEstimatedMatches()
    results = list(search.getResults(0, min(10, total)))
    using_fulltext = True
else:
    print(f"\n📖 Full-text index not found. Searching titles for '{search_string}'...\n")
    suggestion_searcher = SuggestionSearcher(zim)
    suggestion = suggestion_searcher.suggest(search_string)
    total = suggestion.getEstimatedMatches()
    results = list(suggestion.getResults(0, min(10, total)))

if not results:
    print("❌ No matches found.")
else:
    print(f"Found {total} matches. Showing top {len(results)}:\n")
    entries = []
    for i, r in enumerate(results, start=1):
        try:
            entry = zim.get_entry_by_path(r) if using_fulltext else r
            entries.append(entry)
            print(f"{i}. {entry.title}")
        except Exception:
            print(f"{i}. [Invalid entry: {r}]")

    choice = input("\n👉 Enter article number to open (1–10): ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(entries):
            selected = entries[idx]
            print(f"\n📄 Loading '{selected.title}' ...\n")
            content = bytes(selected.get_item().content).decode("utf-8", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(separator="\n", strip=True)

            print("───────────────────────────────")
            print("✨ Gemini-like Summary (Parallel OpenRouter):\n")
            summary = summarize_in_parallel(text)
            print("\n───────────────────────────────")
        else:
            print("⚠️ Invalid choice.")
    else:
        print("⚠️ Invalid input.")
