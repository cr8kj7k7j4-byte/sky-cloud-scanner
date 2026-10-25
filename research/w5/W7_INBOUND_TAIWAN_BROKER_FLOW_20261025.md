# W7 → W5 Candidate Brief — Taiwan Broker Flow / Identity Aggregation

## A. Identification
- Candidate 名稱：Taiwan Broker-Identity / Skill-Conditioned Flow
- 提出日期：2026-10-25
- 研究類型：Cross-sectional / Flow / Microstructure
- 來源：Chang (2026) SSRN; Taiwan broker-network/order-flow literature.

## B. Core hypothesis
1. Hypothesis：券商/分點身分與過去可觀察交易行為，可能使相同淨買賣流呈現不同資訊含量。
2. 要解決的問題：目前 Sky 有成交量/相對強弱，但沒有 identity-conditioned broker flow。
3. 市場：TWSE/TPEx。
4. Horizon：先 1D–5D evidence layer；若資料允許再研究 intraday，不預設。
5. Target：future residual return / reversal conditional on broker-flow identity.
6. 機制：資訊不對稱、投資人 clientele、broker network / branch specialization。

## C. Data
7. Data source：需要合法、PIT、歷史 broker-branch transaction data。
8. Feature：broker/branch net flow, concentration, persistence, historical skill estimated using expanding/rolling past-only windows.
9. PIT 可得性：UNKNOWN / main blocker.
10. 歷史覆蓋：外部研究使用 2018–2024 identity-tagged trades；Sky 尚未確認可取得同等資料。
11. Missing：no identity mapping => no candidate.
12. Corporate action：canonical.
13. Survivorship：canonical PIT universe.

## D. Decision / Execution
14. Trigger/Ranking：flow feature first; no direct production trigger.
15. Entry：next session / next observable timestamp depending dataset.
16. Exit：1D/3D/5D pre-registered.
17. Stop/Target：not part of first-stage evidence test.
18. Execution：PIT-only broker scores; no full-sample skill estimates.
19. Cost：0.45% / 0.65% if tradable.
20. Capacity：must avoid concentration in low-liquidity names.

## E. Risk
21. Main risk：data licensing/access, survivorship of branches, broker-code changes.
22. Leakage：broker "skill" computed with future outcomes.
23. Regime：broker clientele/behavior may drift.
24. Concentration：one broker/branch dominating candidate.
25. Cost：medium-high depending turnover.

## F. Structural difference
26. Production difference：new identity-tagged data family.
27. Existing candidate difference：not generic flow or volume.
28. Frozen-family difference：new PIT data family and broker-conditioned aggregation; not local threshold tuning.
29. Local retune only：NO.
30. Structural novelty：identity-conditioned flow aggregation.

## G. Feasibility
- PIT：UNKNOWN
- untouched OOS：UNKNOWN until data coverage known
- after-cost：PASS in principle
- portfolio/capacity：PASS in principle
- explainability：MEDIUM-HIGH
- complexity：HIGH due data

## W7 recommendation
- 新資訊增益：VERY HIGH if data is accessible
- 與 Sky 重複度：LOW
- 值得測嗎：YES, but data gate first
- 值得買嗎：DO NOT BUY any vendor until sample export + license + PIT history are verified
- 送哪個視窗：W5 → W3 data feasibility → W1/W2 depending horizon
- Status：SEND_TO_W5
