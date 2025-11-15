#  Installing `wikipedia.zim` & Setting Up the Local Wikipedia Summarizer

*A complete, extremely detailed guide for beginners and advanced users*

---

##  1. Downloading the Wikipedia `.zim` File

This script requires a **Wikipedia ZIM archive** — a single offline file containing the full encyclopedia.

###  Step 1: Go to the official Kiwix repository

Visit the Kiwix ZIM download directory:

**[https://download.kiwix.org/zim/wikipedia/](https://download.kiwix.org/zim/wikipedia/)**

###  Step 2: Choose the ZIM build

Your code uses:

```
wikipedia_en_all_nopic_2025-08.zim
```

So navigate to:

```
https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_nopic_2025-08.zim
```

###  Notes

* **`*_nopic`** versions are recommended because they are *smaller* and *faster*.
* **All ZIM files work**, as long as your code’s path matches the file name.
* This file is usually **20–40 GB**, so ensure enough disk space.

###  Step 3: Place the file anywhere

For example:

```
F:\programs\Wikipedia-Search engine\wikipedia_en_all_nopic_2025-08\wikipedia_en_all_nopic_2025-08.zim
```

Your script uses **absolute path**, so make sure it is correct.

---

##  2. Installing Python Dependencies

Your script requires these libraries:

| Library              | Purpose                               |
| -------------------- | ------------------------------------- |
| `libzim`             | To read ZIM archives                  |
| `ollama`             | To communicate with your local model  |
| `beautifulsoup4`     | For HTML → text extraction            |
| `concurrent.futures` | For parallel summarization (built-in) |

### Install them using `pip`:

```bash
pip install libzim ollama beautifulsoup4
```

No extra dependencies are needed.

---

##  3. Installing and Setting Up *Ollama*

The script uses **Ollama locally** for summarization.

### Step 1: Download Ollama

Official download:

**[https://ollama.com/download](https://ollama.com/download)**

Choose your OS (Windows / macOS / Linux).

### Step 2: Install any model you want

Your script uses:

```
LOCAL_MODEL = "Model_name"
```

Replace `"Model_name"` with an actual model like:

```
llama3
llama3.1
qwen2.5
mistral
```

Then install it:

```bash
ollama pull llama3
```

### Step 3: Make sure Ollama is running

On Windows:

* Ollama runs automatically after installation.
* Or start from Start Menu → **Ollama**

You can test:

```bash
ollama run llama3
```

If it responds, you’re good to go.

---

##  4. Understanding the ZIM Search System

Your script supports:

###  Title search (always available)

Uses `SuggestionSearcher`.

###  Full-text search (when ZIM has index)

Your ZIM file includes full-text index, so:

```python
zim.has_fulltext_index
```

returns `True`.

The script automatically detects this.

---

## 📘 5. How the Script Loads and Processes the Wikipedia Article

### 1️⃣ Load the ZIM:

```python
zim = Archive(zim_path)
```

### 2️⃣ Search user query

Either using:

* `Searcher` for full-text
* `SuggestionSearcher` for title-only

### 3️⃣ Extract article HTML:

```python
content = bytes(selected.get_item().content).decode("utf-8", errors="ignore")
```

### 4️⃣ Convert HTML → clean text:

```python
soup = BeautifulSoup(content, "html.parser")
text = soup.get_text(separator="\n", strip=True)
```

### 5️⃣ Split into 8 chunks

Using:

```python
summarize_in_parallel(text)
```

Each chunk is summarized independently via **parallel threads**.

### 6️⃣ Merge → merge → merge

Summaries are recursively compressed.

### 7️⃣ Final summary

A 20-line bullet-point explanation is created.

---

## ⚙️ 6. Running the Script

Once everything is installed, simply run:

```bash
python your_script.py
```

The script will:

1. Load the ZIM file
2. Ask for a search query
3. Show top 10 matches
4. Load selected article
5. Summarize it using your local Ollama model
6. Print the final summary

---

##  7. Troubleshooting

###  “libzim not found”

Install it:

```bash
pip install libzim
```

###  “Failed to load ZIM file”

Check the path in your code:

```python
zim_path = r"F:\...\wikipedia_en_all_nopic_2025-08.zim"
```

###  “Ollama connection error”

Make sure Ollama is running:

```bash
ollama list
```

###  Empty summaries

Your script automatically halves chunk size and retries twice.

---

##  Done!

You now have a **complete offline Wikipedia search + summarizer engine**, powered by:

* **libzim** (offline Wikipedia)
* **BeautifulSoup** (HTML parsing)
* **Ollama** (local LLM summarization)
* **ThreadPoolExecutor** (parallel processing)
