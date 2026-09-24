### Milestone M3: Experiment Results

| Config | Temperature | Turns | Total Tokens | Seconds | Judge Score | Success | Stop Reason |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `configs/exp-temp00.yaml` | 0.0 | 8 | 3,847 | 24.52 | 2/5 | False | `max_turns` |
| `configs/exp-temp07.yaml` | 0.7 | 8 | 3,570 | 24.14 | 2/5 | False | `max_turns` |
| `configs/exp-temp10.yaml` | 1.0 | 8 | 3,547 | 24.27 | 4/5 | True | `max_turns` |

Varying the temperature from 0.0 to 1.0 demonstrated that higher generation randomness surprisingly improved the overall progression of the interrogation. At lower temperatures (0.0 and 0.7), the engine consumed more tokens (up to 3,847) but failed to satisfy the success criteria, scoring only 2/5, likely because the smaller model became trapped in rigid, repetitive conversational loops. Raising the temperature to 1.0 slightly decreased total token consumption (3,547) while achieving a successful 4/5 judge score, suggesting that the added variance helped the agents break out of stalling patterns and advance the dialogue toward a resolution. However, because the LLM-as-a-judge is a noisy estimator with documented biases, and generative output at non-zero temperatures is stochastic, evaluating multiple runs per configuration would be necessary to definitively confirm this trend.