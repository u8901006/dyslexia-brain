#!/usr/bin/env python3
"""
Generate dyslexia daily report HTML using Zhipu AI.
Reads papers JSON, analyzes with AI, generates styled HTML.
"""

import json
import sys
import os
import time
import argparse
from datetime import datetime, timezone, timedelta

import httpx

API_BASE = os.environ.get(
    "ZHIPU_API_BASE", "https://open.bigmodel.cn/api/coding/paas/v4"
)
MODEL_NAME = os.environ.get("ZHIPU_MODEL", "zhipu-coding-plan/glm-5.1")

SYSTEM_PROMPT = (
    "你是閱讀障礙（dyslexia）與學習科學領域的資深研究員與科學傳播者。你的任務是：\n"
    "1. 從提供的醫學與教育文獻中，篩選出最具臨床意義與研究價值的論文\n"
    "2. 對每篇論文進行繁體中文摘要、分類、PICO 分析\n"
    "3. 評估其臨床實用性（高/中/低）\n"
    "4. 生成適合醫療專業人員、教育工作者閱讀的日報\n\n"
    "輸出格式要求：\n"
    "- 語言：繁體中文（台灣用語）\n"
    "- 專業但易懂\n"
    "- 每篇論文需包含：中文標題、一句話總結、PICO分析、臨床實用性、分類標籤\n"
    "- 最後提供今日精選 TOP 3（最重要/最影響臨床實踐的論文）\n"
    "回傳格式必須是純 JSON，不要用 markdown code block 包裹。"
)


def repair_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rstrip("`").strip()
    if not text.endswith("}"):
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")
        text += "]" * max(0, open_brackets) + "}" * max(0, open_braces)
    return text


def load_papers(input_path: str) -> dict:
    if input_path == "-":
        data = json.load(sys.stdin)
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    return data


def analyze_papers(api_key: str, papers_data: dict) -> dict:
    tz_taipei = timezone(timedelta(hours=8))
    date_str = papers_data.get("date", datetime.now(tz_taipei).strftime("%Y-%m-%d"))
    paper_count = papers_data.get("count", 0)

    papers_list = papers_data.get("papers", [])
    trimmed = []
    for p in papers_list[:25]:
        entry = dict(p)
        if len(entry.get("abstract", "")) > 500:
            entry["abstract"] = entry["abstract"][:500] + "..."
        trimmed.append(entry)
    papers_text = json.dumps(trimmed, ensure_ascii=False, indent=2)

    prompt = f"""以下是 {date_str} 從 PubMed 抓取的最新閱讀障礙（dyslexia）相關文獻（共 {paper_count} 篇）。

請進行以下分析，並以 JSON 格式回傳（不要用 markdown code block）：

{{
  "date": "{date_str}",
  "market_summary": "1-2句話總結今天文獻的整體趨勢與亮點",
  "top_picks": [
    {{
      "rank": 1,
      "title_zh": "中文標題",
      "title_en": "English Title",
      "journal": "期刊名",
      "summary": "一句話總結（繁體中文，點出核心發現與臨床意義）",
      "pico": {{
        "population": "研究對象",
        "intervention": "介入措施",
        "comparison": "對照組",
        "outcome": "主要結果"
      }},
      "clinical_utility": "高/中/低",
      "utility_reason": "為什麼實用的一句話說明",
      "tags": ["標籤1", "標籤2"],
      "url": "原文連結",
      "emoji": "相關emoji"
    }}
  ],
  "all_papers": [
    {{
      "title_zh": "中文標題",
      "title_en": "English Title",
      "journal": "期刊名",
      "summary": "一句話總結",
      "clinical_utility": "高/中/低",
      "tags": ["標籤1"],
      "url": "連結",
      "emoji": "emoji"
    }}
  ],
  "keywords": ["關鍵字1", "關鍵字2"],
  "topic_distribution": {{
    "閱讀介入": 3,
    "音韻處理": 2
  }}
}}

原始文獻資料：
{papers_text}

請篩選出最重要的 TOP 5-8 篇論文放入 top_picks（按重要性排序），其餘放入 all_papers。
每篇 paper 的 tags 請從以下選擇：閱讀障礙、發展性閱讀障礙、音韻覺識、音韻處理、快速命名、解碼、閱讀流暢度、閱讀理解、正字法處理、閱讀介入、結構化識字教學、神經影像、功能性連結、工作記憶、執行功能、ADHD共病、語言發展障礙、跨語言研究、華語閱讀、早期篩檢、學習障礙、特殊教育、神經發展、書寫發展、雙語識字。
記住：回傳純 JSON，不要用 ```json``` 包裹。"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 8192,
    }

    models_to_try = [MODEL_NAME, "glm-4-flash", "glm-4-plus", "glm-4"]

    for model in models_to_try:
        payload["model"] = model
        for attempt in range(3):
            try:
                print(
                    f"[INFO] Trying {model} (attempt {attempt + 1})...",
                    file=sys.stderr,
                )
                resp = httpx.post(
                    f"{API_BASE}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 429:
                    wait = 60 * (attempt + 1)
                    print(f"[WARN] Rate limited, waiting {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()

                text = repair_json(text)

                result = json.loads(text)
                print(
                    f"[INFO] Analysis complete: {len(result.get('top_picks', []))} top picks, {len(result.get('all_papers', []))} total",
                    file=sys.stderr,
                )
                return result

            except json.JSONDecodeError as e:
                print(
                    f"[WARN] JSON parse failed on attempt {attempt + 1}: {e}",
                    file=sys.stderr,
                )
                if attempt == 0:
                    try:
                        text = repair_json(text)
                        result = json.loads(text)
                        print(f"[INFO] JSON repaired successfully", file=sys.stderr)
                        return result
                    except Exception:
                        pass
                if attempt < 2:
                    time.sleep(5)
                continue
            except httpx.HTTPStatusError as e:
                print(
                    f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:200]}",
                    file=sys.stderr,
                )
                if e.response.status_code == 429:
                    wait = 60 * (attempt + 1)
                    time.sleep(wait)
                    continue
                break
            except Exception as e:
                print(f"[ERROR] {model} failed: {e}", file=sys.stderr)
                break

    print("[ERROR] All models and attempts failed", file=sys.stderr)
    return None


def generate_html(analysis: dict) -> str:
    date_str = analysis.get(
        "date", datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    )
    date_parts = date_str.split("-")
    if len(date_parts) == 3:
        date_display = (
            f"{date_parts[0]}\u5e74{int(date_parts[1])}\u6708{int(date_parts[2])}\u65e5"
        )
    else:
        date_display = date_str

    summary = analysis.get("market_summary", "")
    top_picks = analysis.get("top_picks", [])
    all_papers = analysis.get("all_papers", [])
    keywords = analysis.get("keywords", [])
    topic_dist = analysis.get("topic_distribution", {})

    top_picks_html = ""
    for pick in top_picks:
        tags_html = "".join(
            f'<span class="tag">{t}</span>' for t in pick.get("tags", [])
        )
        util = pick.get("clinical_utility", "\u4e2d")
        utility_class = (
            "utility-high"
            if util == "\u9ad8"
            else ("utility-mid" if util == "\u4e2d" else "utility-low")
        )
        pico = pick.get("pico", {})
        pico_html = ""
        if pico:
            pico_html = f"""
            <div class="pico-grid">
              <div class="pico-item"><span class="pico-label">P</span><span class="pico-text">{pico.get("population", "-")}</span></div>
              <div class="pico-item"><span class="pico-label">I</span><span class="pico-text">{pico.get("intervention", "-")}</span></div>
              <div class="pico-item"><span class="pico-label">C</span><span class="pico-text">{pico.get("comparison", "-")}</span></div>
              <div class="pico-item"><span class="pico-label">O</span><span class="pico-text">{pico.get("outcome", "-")}</span></div>
            </div>"""

        top_picks_html += f"""
        <div class="news-card featured">
          <div class="card-header">
            <span class="rank-badge">#{pick.get("rank", "")}</span>
            <span class="emoji-icon">{pick.get("emoji", "\U0001f4c4")}</span>
            <span class="{utility_class}">{util}\u5b9e\u7528\u6027</span>
          </div>
          <h3>{pick.get("title_zh", pick.get("title_en", ""))}</h3>
          <p class="journal-source">{pick.get("journal", "")} &middot; {pick.get("title_en", "")}</p>
          <p>{pick.get("summary", "")}</p>
          {pico_html}
          <div class="card-footer">
            {tags_html}
            <a href="{pick.get("url", "#")}" target="_blank">\u95b1\u8b80\u539f\u6587 \u2192</a>
          </div>
        </div>"""

    all_papers_html = ""
    for paper in all_papers:
        tags_html = "".join(
            f'<span class="tag">{t}</span>' for t in paper.get("tags", [])
        )
        util = paper.get("clinical_utility", "\u4e2d")
        utility_class = (
            "utility-high"
            if util == "\u9ad8"
            else ("utility-mid" if util == "\u4e2d" else "utility-low")
        )
        all_papers_html += f"""
        <div class="news-card">
          <div class="card-header-row">
            <span class="emoji-sm">{paper.get("emoji", "\U0001f4c4")}</span>
            <span class="{utility_class} utility-sm">{util}</span>
          </div>
          <h3>{paper.get("title_zh", paper.get("title_en", ""))}</h3>
          <p class="journal-source">{paper.get("journal", "")}</p>
          <p>{paper.get("summary", "")}</p>
          <div class="card-footer">
            {tags_html}
            <a href="{paper.get("url", "#")}" target="_blank">PubMed \u2192</a>
          </div>
        </div>"""

    keywords_html = "".join(f'<span class="keyword">{k}</span>' for k in keywords)
    topic_bars_html = ""
    if topic_dist:
        max_count = max(topic_dist.values()) if topic_dist else 1
        for topic, count in topic_dist.items():
            width_pct = int((count / max_count) * 100)
            topic_bars_html += f"""
            <div class="topic-row">
              <span class="topic-name">{topic}</span>
              <div class="topic-bar-bg"><div class="topic-bar" style="width:{width_pct}%"></div></div>
              <span class="topic-count">{count}</span>
            </div>"""

    total_count = len(top_picks) + len(all_papers)

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Dyslexia Brain &middot; \u95b1\u8b80\u969c\u7919\u6587\u737b\u65e5\u5831 &middot; {date_display}</title>
<meta name="description" content="{date_display} \u95b1\u8b80\u969c\u7919\u6587\u737b\u65e5\u5831\uff0c\u7531 AI \u81ea\u52d5\u5f59\u6574 PubMed \u6700\u65b0\u8ad6\u6587"/>
<style>
  :root {{ --bg: #f0f4f8; --surface: #ffffff; --line: #d1dbe6; --text: #1a2a3a; --muted: #5a6d7e; --accent: #2b7a9e; --accent-soft: #d4eaf5; --accent-dark: #1a5c78; --card-bg: rgba(255,255,255,0.92); }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: linear-gradient(135deg, #e8f0f8 0%, #f0f4f8 40%, #f5f0eb 100%); color: var(--text); font-family: "Noto Sans TC", "PingFang TC", "Helvetica Neue", Arial, sans-serif; min-height: 100vh; overflow-x: hidden; }}
  .container {{ position: relative; z-index: 1; max-width: 880px; margin: 0 auto; padding: 60px 32px 80px; }}
  header {{ display: flex; align-items: center; gap: 16px; margin-bottom: 52px; animation: fadeDown 0.6s ease both; }}
  .logo {{ width: 48px; height: 48px; border-radius: 14px; background: linear-gradient(135deg, var(--accent), var(--accent-dark)); display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; box-shadow: 0 4px 20px rgba(43,122,158,0.25); }}
  .header-text h1 {{ font-size: 22px; font-weight: 700; color: var(--text); letter-spacing: -0.3px; }}
  .header-meta {{ display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap; align-items: center; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; letter-spacing: 0.3px; }}
  .badge-date {{ background: var(--accent-soft); border: 1px solid var(--line); color: var(--accent); }}
  .badge-count {{ background: rgba(43,122,158,0.06); border: 1px solid var(--line); color: var(--muted); }}
  .badge-source {{ background: transparent; color: var(--muted); font-size: 11px; padding: 0 4px; }}
  .summary-card {{ background: var(--card-bg); border: 1px solid var(--line); border-radius: 24px; padding: 28px 32px; margin-bottom: 32px; box-shadow: 0 20px 60px rgba(26,42,58,0.06); animation: fadeUp 0.5s ease 0.1s both; }}
  .summary-card h2 {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.6px; color: var(--accent); margin-bottom: 16px; }}
  .summary-text {{ font-size: 15px; line-height: 1.8; color: var(--text); }}
  .section {{ margin-bottom: 36px; animation: fadeUp 0.5s ease both; }}
  .section-title {{ display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 700; color: var(--text); margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--line); }}
  .section-icon {{ width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; background: var(--accent-soft); }}
  .news-card {{ background: var(--card-bg); border: 1px solid var(--line); border-radius: 24px; padding: 22px 26px; margin-bottom: 12px; box-shadow: 0 8px 30px rgba(26,42,58,0.04); transition: background 0.2s, border-color 0.2s, transform 0.2s; }}
  .news-card:hover {{ transform: translateY(-2px); box-shadow: 0 12px 40px rgba(26,42,58,0.08); }}
  .news-card.featured {{ border-left: 3px solid var(--accent); }}
  .news-card.featured:hover {{ border-color: var(--accent); }}
  .card-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }}
  .rank-badge {{ background: linear-gradient(135deg, var(--accent), var(--accent-dark)); color: #fff; font-weight: 700; font-size: 12px; padding: 2px 8px; border-radius: 6px; }}
  .emoji-icon {{ font-size: 18px; }}
  .card-header-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
  .emoji-sm {{ font-size: 14px; }}
  .news-card h3 {{ font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 8px; line-height: 1.5; }}
  .journal-source {{ font-size: 12px; color: var(--accent); margin-bottom: 8px; opacity: 0.8; }}
  .news-card p {{ font-size: 13.5px; line-height: 1.75; color: var(--muted); }}
  .card-footer {{ margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
  .tag {{ padding: 2px 9px; background: var(--accent-soft); border-radius: 999px; font-size: 11px; color: var(--accent); }}
  .news-card a {{ font-size: 12px; color: var(--accent); text-decoration: none; opacity: 0.7; margin-left: auto; }}
  .news-card a:hover {{ opacity: 1; }}
  .utility-high {{ color: #2a7a3a; font-size: 11px; font-weight: 600; padding: 2px 8px; background: rgba(42,122,58,0.1); border-radius: 4px; }}
  .utility-mid {{ color: #8a6a1e; font-size: 11px; font-weight: 600; padding: 2px 8px; background: rgba(138,106,30,0.1); border-radius: 4px; }}
  .utility-low {{ color: var(--muted); font-size: 11px; font-weight: 600; padding: 2px 8px; background: rgba(90,109,126,0.08); border-radius: 4px; }}
  .utility-sm {{ font-size: 10px; }}
  .pico-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; padding: 12px; background: rgba(240,244,248,0.8); border-radius: 14px; border: 1px solid var(--line); }}
  .pico-item {{ display: flex; gap: 8px; align-items: baseline; }}
  .pico-label {{ font-size: 10px; font-weight: 700; color: #fff; background: var(--accent); padding: 2px 6px; border-radius: 4px; flex-shrink: 0; }}
  .pico-text {{ font-size: 12px; color: var(--muted); line-height: 1.4; }}
  .keywords-section {{ margin-bottom: 36px; }}
  .keywords {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
  .keyword {{ padding: 5px 14px; background: var(--accent-soft); border: 1px solid var(--line); border-radius: 20px; font-size: 12px; color: var(--accent); cursor: default; transition: background 0.2s; }}
  .keyword:hover {{ background: rgba(43,122,158,0.18); }}
  .topic-section {{ margin-bottom: 36px; }}
  .topic-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
  .topic-name {{ font-size: 13px; color: var(--muted); width: 110px; flex-shrink: 0; text-align: right; }}
  .topic-bar-bg {{ flex: 1; height: 8px; background: var(--line); border-radius: 4px; overflow: hidden; }}
  .topic-bar {{ height: 100%; background: linear-gradient(90deg, var(--accent), #4aa3c4); border-radius: 4px; transition: width 0.6s ease; }}
  .topic-count {{ font-size: 12px; color: var(--accent); width: 24px; }}
  .clinic-banner {{ margin-top: 48px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; animation: fadeUp 0.5s ease 0.4s both; }}
  .clinic-link {{ display: flex; align-items: center; gap: 14px; padding: 18px 24px; background: var(--card-bg); border: 1px solid var(--line); border-radius: 24px; text-decoration: none; color: var(--text); transition: all 0.2s; box-shadow: 0 8px 30px rgba(26,42,58,0.04); }}
  .clinic-link:hover {{ border-color: var(--accent); transform: translateY(-2px); box-shadow: 0 12px 40px rgba(26,42,58,0.08); }}
  .clinic-icon {{ font-size: 28px; flex-shrink: 0; }}
  .clinic-info {{ flex: 1; }}
  .clinic-name {{ font-size: 15px; font-weight: 700; color: var(--text); }}
  .clinic-desc {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}
  .clinic-arrow {{ font-size: 18px; color: var(--accent); font-weight: 700; }}
  footer {{ margin-top: 32px; padding-top: 22px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--muted); display: flex; justify-content: space-between; animation: fadeUp 0.5s ease 0.5s both; }}
  footer a {{ color: var(--muted); text-decoration: none; }}
  footer a:hover {{ color: var(--accent); }}
  @keyframes fadeDown {{ from {{ opacity: 0; transform: translateY(-16px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(16px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  @media (max-width: 600px) {{ .container {{ padding: 36px 18px 60px; }} .summary-card, .news-card {{ padding: 20px 18px; }} .pico-grid {{ grid-template-columns: 1fr; }} .clinic-banner {{ grid-template-columns: 1fr; }} footer {{ flex-direction: column; gap: 6px; text-align: center; }} .topic-name {{ width: 70px; font-size: 11px; }} }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo">\U0001f4da</div>
    <div class="header-text">
      <h1>Dyslexia Brain &middot; \u95b1\u8b80\u969c\u7919\u6587\u737b\u65e5\u5831</h1>
      <div class="header-meta">
        <span class="badge badge-date">\U0001f4c5 {date_display}</span>
        <span class="badge badge-count">\U0001f4ca {total_count} \u7bc7\u6587\u737b</span>
        <span class="badge badge-source">Powered by PubMed + Zhipu AI</span>
      </div>
    </div>
  </header>

  <div class="summary-card">
    <h2>\U0001f4cb \u4eca\u65e5\u6587\u737b\u8da8\u52e2</h2>
    <p class="summary-text">{summary}</p>
  </div>

  {"<div class='section'><div class='section-title'><span class='section-icon'>\u2b50</span>\u4eca\u65e5\u7cbe\u9078 TOP Picks</div>" + top_picks_html + "</div>" if top_picks_html else ""}

  {"<div class='section'><div class='section-title'><span class='section-icon'>\U0001f4da</span>\u5176\u4ed6\u503c\u5f97\u95dc\u6ce8\u7684\u6587\u737b</div>" + all_papers_html + "</div>" if all_papers_html else ""}

  {"<div class='topic-section section'><div class='section-title'><span class='section-icon'>\U0001f4ca</span>\u4e3b\u984c\u5206\u4f48</div>" + topic_bars_html + "</div>" if topic_bars_html else ""}

  {"<div class='keywords-section section'><div class='section-title'><span class='section-icon'>\U0001f3f7\ufe0f</span>\u95dc\u9375\u5b57</div><div class='keywords'>" + keywords_html + "</div></div>" if keywords_html else ""}

  <div class="clinic-banner">
    <a href="https://www.leepsyclinic.com/" class="clinic-link" target="_blank">
      <span class="clinic-icon">\U0001f3e5</span>
      <div class="clinic-info">
        <span class="clinic-name">\u674e\u653f\u6d0b\u8eab\u5fc3\u8a3a\u6240\u9996\u9801</span>
        <span class="clinic-desc">\u5c08\u696d\u8eab\u5fc3\u8a3a\u7699\u8a55\u8aee\u8a62\u670d\u52d9</span>
      </div>
      <span class="clinic-arrow">\u2192</span>
    </a>
    <a href="https://blog.leepsyclinic.com/" class="clinic-link" target="_blank">
      <span class="clinic-icon">\U0001f4e8</span>
      <div class="clinic-info">
        <span class="clinic-name">\u8a02\u95b1\u96fb\u5b50\u5831</span>
        <span class="clinic-desc">\u63a5\u6536\u6700\u65b0\u8eab\u5fc3\u91ab\u5b78\u8cc7\u8a0a</span>
      </div>
      <span class="clinic-arrow">\u2192</span>
    </a>
  </div>

  <footer>
    <span>\u8cc7\u6599\u4f86\u6e90\uff1aPubMed &middot; \u5206\u6790\u6a21\u578b\uff1a{MODEL_NAME}</span>
    <span><a href="https://github.com/u8901006/dyslexia-brain">GitHub</a></span>
  </footer>
</div>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(description="Generate dyslexia daily report HTML")
    parser.add_argument("--input", required=True, help="Input papers JSON file")
    parser.add_argument("--output", required=True, help="Output HTML file")
    parser.add_argument(
        "--api-key", default=os.environ.get("ZHIPU_API_KEY", ""), help="Zhipu API key"
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "[ERROR] No API key provided. Set ZHIPU_API_KEY env var or use --api-key",
            file=sys.stderr,
        )
        sys.exit(1)

    papers_data = load_papers(args.input)
    if not papers_data or not papers_data.get("papers"):
        print("[WARN] No papers found, generating empty report", file=sys.stderr)
        tz_taipei = timezone(timedelta(hours=8))
        analysis = {
            "date": datetime.now(tz_taipei).strftime("%Y-%m-%d"),
            "market_summary": "\u4eca\u65e5 PubMed \u66ab\u7121\u65b0\u7684\u95b1\u8b80\u969c\u7919\u76f8\u95dc\u6587\u737b\u66f4\u65b0\u3002\u8acb\u660e\u5929\u518d\u67e5\u770b\u3002",
            "top_picks": [],
            "all_papers": [],
            "keywords": [],
            "topic_distribution": {},
        }
    else:
        analysis = analyze_papers(args.api_key, papers_data)
        if not analysis:
            print("[ERROR] Analysis failed, cannot generate report", file=sys.stderr)
            sys.exit(1)

    html = generate_html(analysis)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Report saved to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
