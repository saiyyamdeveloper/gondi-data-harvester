# Gondi Data Harvester v1 🛡️

**Masaram Gondi (𑴎𑴳 / गोंडी) ke liye duniya ka sabse bada digital corpus banane ka pehla kadam.**

Is corpus se aage banega **MGboard AI**: Voice Typing · Auto Suggestion · Spell Checker · Gondi Dictionary · Translation · AI Chatbot.

> **v2 ka sapna — GDAN (Gondi Digital Archive Network):** YouTube + Telegram +
> Facebook + Instagram + News Websites + PDF Books + Research Papers + Masaram Gondi
> Unicode Documents — sab kuch ek corpus mein.

---

## Aapka Roadmap → Ab kya hai (v1)

| Aapka Phase | Status | Kahan hai |
|---|---|---|
| 1. Foundation | ✅ | yeh repo hi (Python + GitHub + VS Code/Termux) |
| 2. Data Structure | ✅ | `database/` — CSV + JSON, aapke wale 6 fields |
| 3. YouTube Collector | ✅ | `crawlers/youtube_collector.py` |
| 4. Telegram Collector | ✅ (public channels) | `crawlers/telegram_collector.py` |
| 5. Facebook Collector | 🕒 v1 = safe import | `crawlers/facebook_collector.py` |
| 6. Instagram Collector | 🕒 v1 = safe import | `crawlers/instagram_collector.py` |
| 7. Language Detector | ✅ | `filters/gondi_detector.py` + `filters/gondi_lexicon.txt` |
| 8. Duplicate Cleaner | ✅ | `filters/dedup.py` (SHA-256 hash) |
| 9. Auto Scheduler | ✅ | `scheduler/run_all.py` + `.github/workflows/daily-harvest.yml` |
| 10. Dashboard | ✅ | `dashboard/index.html` + `data/stats.json` |
| 11. AI Training Dataset | 🕒 | corpus hi dataset hai — `data/corpus/` |

```
Gondi_Data_Harvester/
├── data/
│   ├── corpus/          # corpus.csv + corpus.json   ← MAIN OUTPUT
│   ├── inbox/           # manual data yahan aata hai (sample_posts.jsonl)
│   └── stats.json       # dashboard ke liye
├── crawlers/            # youtube, telegram, facebook, instagram
├── filters/             # gondi_detector.py, dedup.py, gondi_lexicon.txt
├── database/            # models.py (Post), corpus.py (load/merge/save)
├── scheduler/           # run_all.py (poora pipeline ek command mein)
├── tools/               # make_stats.py, serve_dashboard.py, import_inbox.py
├── dashboard/           # index.html
├── tests/               # test_pipeline.py
├── config/              # youtube_videos.txt, telegram_channels.txt, keywords.json
├── .github/workflows/   # daily-harvest.yml (GitHub Actions)
├── requirements.txt
└── README.md
```

## Quickstart (Day 1)

```bash
# 1. Dependencies
pip install -r requirements.txt

# 2. Config mein apne sources daalo
#    config/youtube_videos.txt     -> Gondi video URLs/IDs
#    config/telegram_channels.txt  -> public channel names

# 3. Sample data se pipeline dekho (5 posts, sab 5 language types)
python tools/import_inbox.py data/inbox/sample_posts.jsonl

# 4. Poora harvest
python scheduler/run_all.py

# 5. Dashboard
python tools/serve_dashboard.py
#    -> browser mein http://localhost:8080
```

Tests: `python tests/test_pipeline.py`

## Data Format (Phase 2)

Har post ek jaisa format — `data/corpus/corpus.csv` **aur** `data/corpus/corpus.json` dono:

| Field | Kya hota hai |
|---|---|
| `platform` | youtube / telegram / facebook / instagram / manual |
| `author` | channel/page/channel name |
| `date` | post ki date (YYYY-MM-DD) |
| `text` | Gondi text (transcript/caption/post) |
| `link` | original URL |
| `language` | masaram_gondi / gunjala_gondi / roman_gondi / devanagari_gondi / possible_gondi / other |
| `id` | SHA-256 based — dedup ke liye |
| `is_sample` | "yes" agar test/sample data hai |
| `collected_at` | kab collect hui (UTC) |

CSV `utf-8-sig` (BOM) mein hai — Excel mein Devanagari/Masaram Gondi sahi dikhenge.

## Har Platform kaise chalta hai

### YouTube (Phase 3) — sabse zyada data
- `config/youtube_videos.txt` mein video URLs/IDs daalo (pehle se 4 real Gondi
  videos seed kiye hain — "Gondi Bhasha Sikhen", "Gondwana Gondi Language" channels se).
- Transcript `youtube-transcript-api` se aata hai — **API key nahi chahiye**.
- Optional: GitHub secret ya env var `YOUTUBE_API_KEY` daalo → `config/keywords.json`
  ke keywords se naye videos khud search honge.
- Note: Gondi audio ke auto-captions aksar Hindi mein hote hain — detector decide
  karega, aur dono types corpus mein useful hain.

### Telegram (Phase 4) — public channels only
- `config/telegram_channels.txt` mein channel names daalo.
- `t.me/s/<channel>` web preview se latest ~20 messages: text, media caption, date, link.
- **Private channels nahi milte** (aur na lena chahiye).

### Facebook & Instagram (Phase 5-6) — safe import (v1)
Direct scraping ToS ke against hai, isliye v1 mein:
- Browser se **public** posts copy karo → `data/inbox/facebook_YYYY-MM-DD.json`
  (format har file ke top par likha hai) → `python tools/import_inbox.py <file>`
- Ya chhodo — `run_all.py` har baar inbox scan kar leta hai, duplicates khud skip hote hain.
- v2: apni page ke liye Meta Graph API ka official raasta.

## Language Detector (Phase 7)

Har post par yeh rules lagte hain (is order mein):

1. **Masaram Gondi Unicode** (U+11D00–U+11D5F) mila → `masaram_gondi` (100% pakka signal)
2. **Gunjala Gondi Unicode** (U+11D60–U+11DAF) mila → `gunjala_gondi`
3. Roman text + dictionary hits → `roman_gondi`
4. Devanagari text + dictionary hits → `devanagari_gondi` (Gondi + Hindi mix)
5. Bas 1 hit → `possible_gondi` (review ke liye)
6. Warna → `other` (corpus mein rehta hai, dashboard par split dikhta hai)

**Dictionary: `filters/gondi_lexicon.txt`** — abhi starter hai (~45 words, sab
Wikipedia/UDHR Gondi translation se verified). **Isse badhau** — har Gondi-English
dictionary se copy ki gayi ek line detector ko aur strong karti hai. Hindi ke common
words (sab, koi, hak…) par half weight hai taaki false-positive na ho.

## Duplicate Cleaner (Phase 8)

- Text ko normalise (NFKC + casefold + whitespace collapse) → **SHA-256 hash**
- Same text same ya alag platform se aaye — sirf ek copy corpus mein rehti hai
- Naya harvest vs purana corpus — dono jagah check hota hai

## Cloudflare Pages Hosting (LIVE) 🌐

**Live URL: https://gondi-corpus.pages.dev**

Harvest ho → corpus update ho → **dashboard khud Cloudflare Pages par deploy ho jata hai.**

```bash
# Manual deploy (jab bhi chahen)
export CLOUDFLARE_API_TOKEN="..."        # "Pages:Edit" permission wala token
export CLOUDFLARE_ACCOUNT_ID="..."       # Cloudflare Account Settings se
python tools/push_to_pages.py            # (wrangler chalta hai — npm hona chahiye)
```

- Flow: `tools/build_site.py` → `deploy/site/` (dashboard + stats + corpus) →
  `npx wrangler pages deploy` → live
- GitHub Actions mein yahi step roz subah harvest ke baad chalta hai.
  GitHub repo ke **Settings → Secrets** mein daalo: `CLOUDFLARE_API_TOKEN`
  aur `CLOUDFLARE_ACCOUNT_ID`
- Sirf public safe data host hota hai: dashboard, stats.json, corpus.csv/json

> 🔐 **Security note:** API token ko sirf *Pages:Edit* permission rakho.
> Token kisi bhi chat/email mein share hua ho to usse baad mein
> **rotate/revoke** kar lena (Cloudflare Dashboard → Members → API Tokens).
> GitHub mein hamesha Secrets ke through hi use karo, code mein kabhi nahi.

## Auto Scheduler (Phase 9)

- **Local:** `python scheduler/run_all.py` — abhi bhi aise hi chala sakte ho
- **GitHub Actions:** `.github/workflows/daily-harvest.yml` — roz subah **06:30 IST**
  poora pipeline chalta hai, corpus update hota hai, aur **data khud commit ho jata hai**
  repo mein. Aapko kuch karna nahi padta.
- GitHub repo banao → yeh folder push karo → Settings → Secrets →
  `YOUTUBE_API_KEY` (optional) daalo → bas.

## 🔗 Link Ingestion — "Link do, Gondi data aayega"

Koi bhi social media link do — uska Gondi content corpus mein aa jayega,
aur source yaad rehta hai taaki **roz subah ka auto-harvest** wahan se naya
data uthata rahe.

```bash
# YouTube channel — saare recent videos ke transcripts
python tools/add_source.py https://www.youtube.com/@gondibhasha_sikhen

# Telegram public channel — latest + purani messages (pagination)
python tools/add_source.py https://t.me/some_gondi_channel

# Ek single YouTube video
python tools/add_source.py https://youtu.be/XXXXXXXXXXX

# WhatsApp group — pehle app se export karo:
#   Group → group name → ⋮ → Export chat → Without media → .txt file
#   File ko exports/ folder mein rakho, phir:
python tools/add_source.py exports/whatsapp_gondwana_group.txt

# Facebook / Instagram page (v1: manual export ki guidance milti hai)
python tools/add_source.py https://www.facebook.com/somepage
```

### Har platform ki feasibility (honest)

| Platform | Kya milta hai | Kaise |
|---|---|---|
| **YouTube** channel | ✅ Saare recent videos ke transcripts (default 30, `--max 100` tak) | Page scrape / Data API (key ho to) |
| **Telegram** channel | ✅ Latest + `?before=` pagination se ~60-150 purani messages | t.me/s preview |
| **Telegram** full history | 🕒 Channel owner ko apna bot add karna hoga (BotFather se banayein) — v2 mein implement | Bot API |
| **Facebook** page | ⚠️ Public pages ka scraping ToS-violation hai. **Apni page** ho to Meta Graph API; doosri page ka content browser se copy karke inbox mein daalein | Manual/API |
| **Instagram** | ⚠️ Same — login-wall hai. Apne account ke liye Graph API baad mein | Manual/API |
| **WhatsApp** group | ✅ "Export chat (Without media)" wala .txt — parser built-in | App se export karo |

⚠️ **WhatsApp privacy:** yeh corpus PUBLIC hai (GitHub + Cloudflare).
Sirf aise groups import karo jinke aap member ho aur jiska content share
karne mein aap comfortable ho. Export files `exports/` mein rehti hain jo
**repo mein commit NAHI hoti** (gitignored).

### Sources ka registry
Har add kiya gaya link `config/sources.txt` mein save hota hai. Roz subah 06:30 IST
ka GitHub Actions run har source dobara check karta hai — naye posts aate
jaate hain, duplicates dedup se hat jaate hain.

## Data Browser / Dashboard (Phase 10)

`python tools/serve_dashboard.py` → http://localhost:8080

- Total posts, Gondi posts, total words, unique words, Masaram Gondi characters
- Platform-wise aur language-detection-wise split
- Recent 10 posts (original links ke saath)

## Ethics & ToS (zaroori)

- Sirf **public** data. Kisi ka private data, DM, ya restricted content — kabhi nahi.
- Facebook/Instagram direct scraping nahi — official API / manual inbox hi.
- Rate-limits honored (delays code mein hain). Sources ka credit `link` field mein rehta hai.
- Yeh shikshan/research ke liye corpus hai — data ka istemal bhi waise hi karo.

## v2 — GDAN Roadmap (aage)

1. News websites + PDF books + research papers ke collectors (PDF text extraction: `pypdf`)
2. Masaram Gondi Unicode documents ka special ingester
3. Lexicon expansion (Gondi-English dictionary se bulk import)
4. Sentence-level segmentation + MGboard ke liye final training formats (word-level for auto-suggestion, text-pairs for translation)
5. Versioning: har harvest ka snapshot (corpus v1.0, v1.1…)
