

* **Trader API (Individual Developer)** with two products you can enable:

  * **Accounts & Trading** → balances, positions, order history, place/cancel orders. ([schwab-py.readthedocs.io][1])
  * **Market Data** → quotes and price history; there’s also a **streaming WebSocket** for real-time data. ([Medium][2], [schwab-py.readthedocs.io][3])
* **OAuth 2.0 (authorization\_code flow only)** with strict callback URL rules. ([developer.schwab.com][4])
* **Eligibility/limits**: you need a Schwab brokerage account; as an **Individual Developer** you can create **one** app. ([developer.schwab.com][5])
* If you were using TD Ameritrade’s API, it was shut down in **May 2024**—migration is to Schwab’s API. ([GitHub][6])

**How to get access (10-minute setup, approval can take longer)**

1. Register on the **Schwab Developer Portal** and choose the Trader API products you want. ([developer.schwab.com][7])
2. Create your app and set an allowed **callback URL** (localhost is fine for initial dev). ([developer.schwab.com][4])
3. Complete the OAuth flow to obtain refresh/access tokens and start calling endpoints. ([developer.schwab.com][8])
4. For realtime data, connect to the **Streamer** (WebSocket) after you have an access token. ([Scribd][9])

**What you can pull/do (examples)**

* Get **account numbers, balances, positions, orders**. ([schwab-py.readthedocs.io][1])
* Fetch **quotes/price history**; subscribe to **real-time** updates via streaming. ([Medium][2], [schwab-py.readthedocs.io][3])

**FYI for RIAs**
If you’re operating as an advisory firm, Schwab Advisor Services has a separate integration stack (OpenView Gateway, SSO, etc.). Different program, different capabilities. ([Schwab Brokerage][10])

If you tell me exactly what you want to pull (e.g., balances + latest quotes + option chains), I’ll sketch the endpoints and a minimal Python example you can drop into your project.

[1]: https://schwab-py.readthedocs.io/en/latest/client.html?utm_source=chatgpt.com "HTTP Client — schwab-py documentation"
[2]: https://medium.com/%40carstensavage/the-unofficial-guide-to-charles-schwabs-trader-apis-14c1f5bc1d57?utm_source=chatgpt.com "The (Unofficial) Guide to Charles Schwab's Trader APIs"
[3]: https://schwab-py.readthedocs.io/en/latest/streaming.html?utm_source=chatgpt.com "Streaming Client — schwab-py documentation"
[4]: https://developer.schwab.com/user-guides/apis-and-apps/app-callback-url-requirements?utm_source=chatgpt.com "App Callback URL Requirements and Limitations"
[5]: https://developer.schwab.com/user-guides/individual-developer/about-individual-developer-role?utm_source=chatgpt.com "About the Individual Developer Role"
[6]: https://github.com/alexgolec/tda-api?utm_source=chatgpt.com "alexgolec/tda-api: A TD Ameritrade API client for Python. ..."
[7]: https://developer.schwab.com/?utm_source=chatgpt.com "Charles Schwab Developer Portal"
[8]: https://developer.schwab.com/user-guides/get-started/authenticate-with-oauth?utm_source=chatgpt.com "Authenticate with OAuth"
[9]: https://www.scribd.com/document/756325334/Schwab-Trader-API-Streamer-Guide?utm_source=chatgpt.com "Schwab Trader API - Streamer Guide | PDF"
[10]: https://advisorservices.schwab.com/managing-your-business/tech-integration/api-integration?utm_source=chatgpt.com "API Integration - Schwab Advisor Services"


**Problem:** you want to pull the Schwab Equity Ratings® report (the same PDF you see on schwab.com) via an API.

**Short answer:** there isn’t a documented API for those research PDFs. Schwab’s public Trader API covers accounts/trading and market data—**not** proprietary research reports—so the per-ticker *Schwab Equity Ratings® Report* remains website/mobile-only behind login. ([developer.schwab.com][1], [Medium][2])

**What you *can* do today**

* Use the Trader API for quotes, price history, options, positions, orders, etc. (but not SER PDFs or the A–F rating feed). Community wrappers list exactly these capabilities. ([PyPI][3])
* Fetch **public** Schwab Equity Ratings *Model Performance* PDFs (aggregate, not ticker-specific). Those are downloadable without login if that helps your research notes. Examples from Apr–Aug 2025: ([Schwab Wall Street][4])
* If you’re an RIA, Schwab Advisor Services integrates with third-party research/analytics via **OpenView Gateway** (SSO + data pipes), but that’s a different program and still doesn’t expose SER PDFs directly. ([Schwab Brokerage][5])

**Why not just scrape it?**
Automating downloads from the client site (headless browser, cookies, etc.) risks violating Schwab’s online terms and the developer portal terms (they explicitly restrict automated access outside approved APIs). I wouldn’t go there. ([Schwab Brokerage][6], [developer.schwab.com][7])

**Practical next steps**

1. Tell me exactly which *data points* from the report you need (e.g., overall A–F rating, Fundamentals/Valuation/Momentum grades, peer list). I’ll map the closest equivalents you can pull via the Market Data API or suggest compliant alternatives. ([developer.schwab.com][1])
2. If you truly need the PDF itself programmatically, your best bet is to ask Schwab whether there’s a licensable feed or partner route for research distribution under your account type. Start via the Developer Portal user guides/contact or your Schwab rep. ([developer.schwab.com][8], [Schwab Brokerage][9])

If you want, I can sketch a small Python client that grabs what’s available (quotes/fundamentals/options) and cleanly stores links/metadata alongside any **manually** downloaded SER PDFs.

[1]: https://developer.schwab.com/products/trader-api--individual?utm_source=chatgpt.com "Charles Schwab Trader API"
[2]: https://medium.com/%40carstensavage/the-unofficial-guide-to-charles-schwabs-trader-apis-14c1f5bc1d57?utm_source=chatgpt.com "The (Unofficial) Guide to Charles Schwab's Trader APIs"
[3]: https://pypi.org/project/schwab-py/?utm_source=chatgpt.com "schwab-py"
[4]: https://www.schwab.wallst.com/ser/perfMonitor/public/dmFetch.asp?doctag=SERP_C_1176_20250416&feed=7276&pageID=C&utm_source=chatgpt.com "Schwab Equity Ratings Model Performance"
[5]: https://advisorservices.schwab.com/managing-your-business/tech-integration/api-integration?utm_source=chatgpt.com "API Integration - Schwab Advisor Services"
[6]: https://www.schwab.com/legal/terms?utm_source=chatgpt.com "Schwab Online Services Agreement"
[7]: https://developer.schwab.com/terms-and-conditions?utm_source=chatgpt.com "Terms and Conditions"
[8]: https://developer.schwab.com/user-guides?utm_source=chatgpt.com "User Guides"
[9]: https://www.schwab.com/contact-us?utm_source=chatgpt.com "Contact Us | Customer Service"


https://www.schwab.wallst.com/client/Reports/ReportRetrieve?reportType=SchwabEquityRatings&symbol=BLK

https://appweekly.marketedge.com/#!/stocks/second_opinion/QS

