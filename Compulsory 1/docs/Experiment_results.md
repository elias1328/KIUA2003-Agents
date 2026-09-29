### Experiment Results

| Config | Temperature | Turns | Total Tokens | Seconds | Judge Score | Success | Stop Reason |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `configs/final.yaml` | 0.3 / 0.7 | 8 | 2,862 | 51.29 | 4/5 | True | `max_turns` |
| `configs/exp-temp00.yaml` | 0.0 | 8 | 3,847 | 24.52 | 2/5 | False | `max_turns` |
| `configs/exp-temp07.yaml` | 0.7 | 8 | 3,570 | 24.14 | 2/5 | False | `max_turns` |
| `configs/exp-temp10.yaml` | 1.0 | 8 | 3,547 | 24.27 | 4/5 | True | `max_turns` |
| `configs/fail-drift.yaml` | 1.5 | 8 | 3,308 | 23.83 | 2/5 | False | `max_turns` |
| `configs/fail-forgetting.yaml` | 0.7 | 12 | 4,136 | 36.63 | 2/5 | False | `max_tokens` |
| `configs/fail-sycophancy.yaml` | 0.3 / 0.7 | 8 | 2,912 | 24.52 | 4/5 | True | `max_turns` |

M3 Milestone & Final Baseline:
Our agreed baseline configuration (`configs/final.yaml`) pairs a disciplined, analytical interrogator (Detective Cross at $T=0.3$) with a defensive, creative suspect (Julian Vance at $T=0.7$). In our controlled temperature sweep ($0.0 \le T \le 1.0$), higher generation randomness improved overall narrative progression. At lower temperatures (0.0 and 0.7), the engine consumed more tokens (up to 3,847) but scored 2/5 because the model became trapped in rigid, repetitive loops. Raising the temperature to 1.0 slightly decreased token consumption (3,547) while achieving a 4/5 score. In the final baseline (`final.yaml`), the decoupled temperatures produced a focused adversarial interrogation: Detective Cross caught Vance in a 15-minute arrival discrepancy at the Grand Bistro and questioned an unexplained unmarked box package, earning a 4/5 judge score while Vance successfully defended his alibi without confessing.

