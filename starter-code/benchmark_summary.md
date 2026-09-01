# 📊 Multi-Agent Interrogation Benchmark Report

**Generated:** 2026-08-31 18:37:14  
**Total Iterations:** 9  

---

## 1. Executive Summary Table

| Metric Category | Metric Name | Value | Description |
| :--- | :--- | :---: | :--- |
| **Judicial Accuracy** | **Overall Accuracy** | **55.56%** | Overall correct verdict rate ($TP + TN$) |
| | **Guilty Conviction Rate (Recall)** | **25.00%** | Percent of guilty suspects caught and convicted |
| | **Guilty Suspect Escape Rate** | **75.00%** | Percent of guilty suspects who evaded detection |
| | **Innocent Exoneration Rate** | **80.00%** | Percent of innocent suspects correctly cleared |
| | **Wrongful Accusation Rate (FP)** | **20.00%** | False accusation / miscarriage of justice rate |
| **Grade Distribution** | **Grade A (Justice Served)** | **55.6%** | Flawless deduction and correct verdict |
| | **Grade B / C (Unsolved / Minor)** | **0.0%** | Suspect escaped or insufficient evidence |
| | **Grade F (False Conviction)** | **44.4%** | Bullying / false imprisonment of innocent |
| **Efficiency** | **Average Dialogue Turns** | **6.89** | Turns utilized per interrogation |
| | **Early Exit Rate** | **11.1%** | Interrogations concluded early via confession/clearance |
| | **Average Token Usage** | **10728 tokens** | Mean token budget consumed per case |
| | **Average Execution Time** | **268.23s** | Wall-clock execution duration per case |

---

## 2. Parameter Sensitivity: Performance by Turn Limit

| Turn Budget | Sample Runs | Accuracy (%) | Escape Rate (%) | Conviction Rate (%) | Avg Tokens | Early Halt (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **4 Turns** | 2 | **50.0%** | 100.0% | 0.0% | 4676 | 0.0% |
| **6 Turns** | 2 | **0.0%** | 100.0% | 0.0% | 10061 | 0.0% |
| **8 Turns** | 2 | **100.0%** | 0.0% | 0.0% | 13259 | 50.0% |
| **10 Turns** | 2 | **50.0%** | 0.0% | 100.0% | 13170 | 0.0% |
| **12 Turns** | 1 | **100.0%** | 0.0% | 0.0% | 14223 | 0.0% |

---

## 3. Confusion Matrix

| Ground Truth \ Detective Verdict | Arrested / Guilty | Exonerated / Innocent | Total |
| :--- | :---: | :---: | :---: |
| **Actual Guilty** | **1 (True Positive)** | **3 (False Negative / Escaped)** | **4** |
| **Actual Innocent** | **1 (False Positive / Bullied)** | **4 (True Negative)** | **5** |
