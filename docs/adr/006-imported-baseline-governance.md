# ADR-006: Imported Baseline Governance

**Status:** Accepted

Production traces cannot automatically become golden baselines. Administrators import externally curated packages. Validation creates immutable candidate versions; explicit activation changes the baseline used by new scoring jobs.

