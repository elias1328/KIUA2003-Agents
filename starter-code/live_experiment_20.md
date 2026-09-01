# 📊 Multi-Agent Interrogation Benchmark Report

**Generated:** 2026-08-31 17:40:36  
**Total Iterations:** 9  

---

## 1. Executive Summary Table

| Metric Category | Metric Name | Value | Description |
| :--- | :--- | :---: | :--- |
| **Judicial Accuracy** | **Overall Accuracy** | **55.56%** | Overall correct verdict rate ($TP + TN$) |
| | **Guilty Conviction Rate (Recall)** | **50.00%** | Percent of guilty suspects caught and convicted |
| | **Guilty Suspect Escape Rate** | **50.00%** | Percent of guilty suspects who evaded detection |
| | **Innocent Exoneration Rate** | **57.14%** | Percent of innocent suspects correctly cleared |
| | **Wrongful Accusation Rate (FP)** | **42.86%** | False accusation / miscarriage of justice rate |
| **Grade Distribution** | **Grade A (Justice Served)** | **55.6%** | Flawless deduction and correct verdict |
| | **Grade B / C (Unsolved / Minor)** | **11.1%** | Suspect escaped or insufficient evidence |
| | **Grade F (False Conviction)** | **33.3%** | Bullying / false imprisonment of innocent |
| **Efficiency** | **Average Dialogue Turns** | **6.44** | Turns utilized per interrogation |
| | **Early Exit Rate** | **0.0%** | Interrogations concluded early via confession/clearance |
| | **Average Token Usage** | **9665 tokens** | Mean token budget consumed per case |
| | **Average Execution Time** | **243.76s** | Wall-clock execution duration per case |

---

## 2. Parameter Sensitivity: Performance by Turn Limit

| Turn Budget | Sample Runs | Accuracy (%) | Escape Rate (%) | Conviction Rate (%) | Avg Tokens | Early Halt (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **4 Turns** | 2 | **100.0%** | 0.0% | 0.0% | 4564 | 0.0% |
| **6 Turns** | 2 | **50.0%** | 0.0% | 0.0% | 8526 | 0.0% |
| **8 Turns** | 2 | **50.0%** | 50.0% | 50.0% | 10969 | 0.0% |
| **10 Turns** | 2 | **50.0%** | 0.0% | 0.0% | 12934 | 0.0% |
| **12 Turns** | 1 | **0.0%** | 0.0% | 0.0% | 12999 | 0.0% |

---

## 3. Confusion Matrix

| Ground Truth \ Detective Verdict | Arrested / Guilty | Exonerated / Innocent | Total |
| :--- | :---: | :---: | :---: |
| **Actual Guilty** | **1 (True Positive)** | **1 (False Negative / Escaped)** | **2** |
| **Actual Innocent** | **3 (False Positive / Bullied)** | **4 (True Negative)** | **7** |
