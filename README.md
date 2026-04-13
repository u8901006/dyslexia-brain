# Dyslexia Brain

閱讀障礙（Dyslexia）文獻日報 — 每日自動更新

## 運作方式

1. **GitHub Actions** 每天台北時間 13:00 自動觸發
2. 從 **PubMed** 抓取最新閱讀障礙相關文獻
3. 透過 **Zhipu AI (GLM-5.1)** 進行繁體中文摘要、分類與 PICO 分析
4. 生成靜態 HTML 報告並部署至 **GitHub Pages**

## 架構

```
scripts/
├── fetch_papers.py      # PubMed E-utilities 文獻抓取
├── generate_report.py   # Zhipu AI 分析 + HTML 生成
├── generate_index.py    # 首頁索引生成
└── requirements.txt     # Python 依賴
```

## 網站

- 首頁: https://u8901006.github.io/dyslexia-brain/
- 李政洋身心診所: https://www.leepsyclinic.com/
- 電子報: https://blog.leepsyclinic.com/
