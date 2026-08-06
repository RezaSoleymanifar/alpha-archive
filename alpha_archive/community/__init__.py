"""Community / crowdsourcing layer.

Modules:
- screening:  Gate 1 LLM-based spam + on-topic + evidence checker
- backtest_delta:  Gate 2: re-run pipeline with proposed change, measure impact
- voting:     Gate 3: vote tally + reputation-weighted aggregation
- bipartisan: Gate 4: Community-Notes-style faction-spanning agreement check
- merge:      Gate 5: governance tiers (T1 auto, T2 mod, T3 multi-mod + window)
- reputation: rep math + faction inference from voting history
- scraper:    autonomous external-mention finder (Twitter / Reddit / GitHub / Substack)

All modules are STUBS in v0.1.0, schema + interfaces ready for Phase 4 build-out.
See meta/community.md for governance spec.
"""
