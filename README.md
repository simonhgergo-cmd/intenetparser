# intenetparser

Collects public posts from free sources, finds what people **struggle with**, **wish existed** and
**love**, and breaks it down by audience segment. The goal is to find problems worth building
products for.

- Free sources only. No paid APIs and no required dependencies (Python 3.11+ standard library).
- Keyword-based analysis that runs offline, plus exports you can paste into Claude or run through a
  local LLM for better quality.
- One self-contained HTML report.

## Quick start

```bash
git clone https://github.com/simonhgergo-cmd/intenetparser && cd intenetparser
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
iparse init              # creates config.toml, edit it to pick sources/communities
iparse run --once        # collect -> analyse -> report -> LLM export
open reports/report.html # macOS; on Linux use xdg-open, on Windows start
```

The first run with the default config makes about 2,800 requests and takes roughly 1.5–2 hours,
because requests are deliberately spaced out (`[http] min_interval`) so the sources don't block
you. Almost all of that is Reddit comments. Without a free Reddit app (`client_id`/`client_secret`)
Reddit allows far fewer requests per minute, so expect several hours or skipped listings.

## Sources

| Source | Status | What you need |
|---|---|---|
| Reddit | on | Nothing. A free "script" app (`client_id`/`client_secret`) is more reliable. Free API terms cover non-commercial use. |
| Hacker News | on | Nothing |
| Bluesky (free stand-in for X) | on | Search may require a free account + app password |
| Mastodon | on | Nothing |
| Stack Exchange (parenting, money, cooking, workplace, ...) | on | Nothing. A free key raises the daily limit. |
| Apple App Store reviews | on | Nothing. 1–2 star reviews of popular apps = unmet needs. |
| YouTube comments | off | Free API key (10,000 units/day, no billing) |
| TikTok | off, experimental | `pip install -e '.[tiktok]' && playwright install chromium` |
| Instagram, X, anything else | via import | Put CSV/JSON/TXT files in a folder and point `[sources.import]` at it |

**What's not covered, and why:** X has no free API, and Instagram shows almost nothing to
logged-out visitors. The TikTok collector only reads public pages while logged out: it never logs
in, likes, follows or posts, and doesn't try to hide that it's automated. TikTok often shows
captchas or empty pages to it, so expect patchy results. Automated access breaks TikTok's terms;
whether to turn it on is up to you. Bluesky and Mastodon cover the same kind of short public posts
as X. For Instagram, copy comments or posts you care about into a file and import them.

## Commands

```
iparse init                      create config.toml
iparse collect [--source NAME]   fetch posts (repeat --source to pick several)
iparse analyze [--all]           keyword analysis of new posts (--all re-analyses everything)
iparse report                    write reports/report.html
iparse export csv|jsonl          everything, for spreadsheets / pandas
iparse export llm                prompt packs for Claude or a local model (see below)
iparse llm --model NAME          run the packs through a local OpenAI-compatible model
iparse run [--every 6h] [--once] collect -> analyse -> report -> export, forever
iparse stats                     what's in the database
```

Collecting again doesn't create duplicates; it refreshes scores and comment counts.

### Running it 24/7

`iparse run` loops on its own. To keep it alive after you log out:

```bash
nohup iparse run --every 6h > iparse.log 2>&1 &
```

Or use cron instead (`crontab -e`):

```
0 */6 * * * cd /path/to/intenetparser && .venv/bin/iparse run --once >> iparse.log 2>&1
```

## Reading the report

Pick a segment and you get four lists:

- **Problems**: complaints and struggles, ranked by how many posts mention them, weighted by
  upvotes/likes and how negative the post is.
- **Wishes and requests**: "I wish there was...", "is there an app that...", "I'd pay for...",
  "someone should build...". These are the most direct product leads.
- **What makes people happy**: things people love, recommend or call a game changer. This tells
  you what "good" looks like for that group.
- **Most talked about**: common phrases. For a segment, ranked by how much *more* that group talks
  about it than everyone else.

Click a theme to see the quotes behind it, with links to the originals.

### Segments, honestly

Platforms don't say who posted something, so "every demographic" can only be approximated:

- `audience:*` comes from where a post was made (r/Parenting → parents). That describes the
  community, not the person. Add your own mappings under `[segments.communities]`.
- `age:*`, `gender:*`, `role:*`, `life:*`, `housing:*` are only set when authors say it about
  themselves ("I'm a nurse", "34F", "my toddler", "my landlord").
- `platform:*` is the source.

Nothing sensitive (health, ethnicity, religion, politics, sexuality) is inferred. Self-reported
segments are small, because most posts don't mention who wrote them.

## Better analysis with an LLM

The keyword analyser is fast and transparent, but it misses sarcasm, context and anything phrased
in an unusual way. It's best for finding leads. `iparse export llm` (also run by `iparse run`)
writes `exports/llm/`:

- `pack_001.md`, `pack_002.md`, ...: instructions plus a batch of posts that had a problem, wish
  or joy. Paste one into Claude, or any chat model, and you get structured JSON back per post:
  problems with severity, wishes, who the author is and a product idea.
- `summary.md`: all themes per segment with example quotes, plus a prompt asking for merged
  problems and ranked product ideas with evidence. This is the one to paste first.

Use `--max-chars` to fit your model's context (default 60,000 characters, roughly 15k tokens).

Local model, nothing leaves your machine (for example with [Ollama](https://ollama.com)):

```bash
ollama pull llama3.1
iparse llm --model llama3.1                                   # Ollama default URL
iparse llm --model qwen2.5 --url http://localhost:1234/v1     # LM Studio
```

Responses go to `exports/llm/responses/`.

## Tuning

- **Communities and queries:** `config.toml`. Pick subreddits, hashtags and Stack Exchange sites
  that match the groups you care about.
- **Patterns:** `iparse/analysis/lexicon.py` holds every regex for problems, wishes and joys, plus
  the sentiment word list. Add phrasings you see in your data, then run `iparse analyze --all`.
- **Thresholds:** `[analysis]`. Lower `min_mentions` to see rarer themes.

## Data and privacy

- Author names are stored only as salted hashes (set your own `author_salt`).
- Everything stays local: `data/iparse.db` (SQLite), `reports/`, `exports/`.
- Collect at a polite pace and respect each platform's terms; you're responsible for how you use
  the data.

## Development

```bash
python3 -m unittest discover -s tests -t .
```

Layout: `iparse/sources/` (one file per platform), `iparse/analysis/` (analyser, segments,
aggregation), `iparse/report.py`, `iparse/export.py`, `iparse/pipeline.py`, `iparse/cli.py`.
