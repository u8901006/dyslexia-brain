#!/usr/bin/env python3
"""Generate index.html listing all dyslexia daily reports."""

import glob
import os
from datetime import datetime

html_files = sorted(glob.glob("docs/dyslexia-*.html"), reverse=True)
links = ""
for f in html_files[:60]:
    name = os.path.basename(f)
    date = name.replace("dyslexia-", "").replace(".html", "")
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
        weekday = ["一", "二", "三", "四", "五", "六", "日"][d.weekday()]
        date_display = f"{d.year}年{d.month}月{d.day}日（週{weekday}）"
    except Exception:
        date_display = date
        weekday = ""
    links += f'<li><a href="{name}">\U0001f4c5 {date_display}</a></li>\n'

total = len(html_files)

index = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Dyslexia Brain · 閱讀障礙文獻日報</title>
<style>
  :root {{ --bg: #f0f4f8; --surface: #ffffff; --line: #d1dbe6; --text: #1a2a3a; --muted: #5a6d7e; --accent: #2b7a9e; --accent-soft: #d4eaf5; --accent-dark: #1a5c78; }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: linear-gradient(135deg, #e8f0f8 0%, #f0f4f8 40%, #f5f0eb 100%); color: var(--text); font-family: "Noto Sans TC", "PingFang TC", "Helvetica Neue", Arial, sans-serif; min-height: 100vh; }}
  .container {{ position: relative; z-index: 1; max-width: 640px; margin: 0 auto; padding: 80px 24px; }}
  .logo {{ font-size: 48px; text-align: center; margin-bottom: 16px; }}
  h1 {{ text-align: center; font-size: 24px; color: var(--text); margin-bottom: 8px; }}
  .subtitle {{ text-align: center; color: var(--accent); font-size: 14px; margin-bottom: 48px; }}
  .count {{ text-align: center; color: var(--muted); font-size: 13px; margin-bottom: 32px; }}
  ul {{ list-style: none; }}
  li {{ margin-bottom: 8px; }}
  a {{ color: var(--text); text-decoration: none; display: block; padding: 14px 20px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; transition: all 0.2s; font-size: 15px; }}
  a:hover {{ background: var(--accent-soft); border-color: var(--accent); transform: translateX(4px); }}
  .clinic-section {{ margin-top: 48px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .clinic-link {{ display: flex; align-items: center; gap: 10px; padding: 14px 18px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; text-decoration: none; color: var(--text); transition: all 0.2s; }}
  .clinic-link:hover {{ background: var(--accent-soft); border-color: var(--accent); }}
  .clinic-icon {{ font-size: 22px; }}
  .clinic-name {{ font-size: 13px; font-weight: 600; }}
  footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: var(--muted); }}
  footer a {{ display: inline; padding: 0; background: none; border: none; color: var(--muted); }}
  footer a:hover {{ color: var(--accent); }}
  @media (max-width: 600px) {{ .clinic-section {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="logo">\U0001f4da</div>
  <h1>Dyslexia Brain</h1>
  <p class="subtitle">閱讀障礙文獻日報 · 每日自動更新</p>
  <p class="count">共 {total} 期日報</p>
  <ul>{links}</ul>
  <div class="clinic-section">
    <a href="https://www.leepsyclinic.com/" class="clinic-link" target="_blank">
      <span class="clinic-icon">\U0001f3e5</span>
      <span class="clinic-name">李政洋身心診所</span>
    </a>
    <a href="https://blog.leepsyclinic.com/" class="clinic-link" target="_blank">
      <span class="clinic-icon">\U0001f4e8</span>
      <span class="clinic-name">訂閱電子報</span>
    </a>
  </div>
  <footer>
    <p>Powered by PubMed + Zhipu AI · <a href="https://github.com/u8901006/dyslexia-brain">GitHub</a></p>
  </footer>
</div>
</body>
</html>"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(index)
print("Index page generated")
