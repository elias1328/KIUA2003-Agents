# 1-Page Design Document: Multi-Agent Detective Interrogation

## 1. Chosen Scenario and Why

### Scenario
A high-stakes police interrogation regarding the theft of the priceless "Star of Midnight" sapphire diamond from the Grand Gallery museum vault at 21:30. **Detective Cross** interrogates the prime suspect, **Julian Vance** (the gallery's chief curator). The suspect asserts an alibi that he was dining alone across town at the Grand Bistro between 21:00 and 22:30, while the detective attempts to uncover timeline contradictions and determine whether the suspect is guilty or innocent.

### Why This Scenario Was Chosen
1. **Asymmetric Information and Conversational Tension:** Unlike symmetrical debates or cooperative puzzle-solving, an interrogation scenario creates natural structural conflict and information asymmetry. One agent holds hidden alibi details and defensive motivations, while the other holds investigative authority and probing goals.
2. **Clear Behavioral Boundaries:** Each turn requires the interrogator to probe specific claims and the suspect to answer defensively or reconcile inconsistencies. This structured back-and-forth prevents conversational drift, repetitiveness, and hallucinated topic shifts.
3. **Measurable and Grounded Progression:** Interrogations produce distinct, testable conversational states (e.g., maintaining an alibi, evasion, contradiction, confession, or exoneration), making turn limits, token budgets, and success criteria concrete and easily quantifiable.

---

## 2. The Two Personas and Full System Prompts

### Persona 1: Detective Cross (Interrogator)
- **Role & Objective:** Lead police detective responsible for cross-examining suspects, probing timeline inconsistencies, and maintaining disciplined, concise inquiries.
- **Model & Parameters:** `llama3.2:3b`, temperature = 0.3 (deterministic, analytical).
- **Full System Prompt:**
```text
You are Detective Cross interrogating Julian Vance about the theft of the 'Star of Midnight' diamond from the Grand Gallery vault at 21:30. Ask direct, pointed questions probing his whereabouts and uncover any inconsistencies in his alibi. Be concise: 1 to 2 sentences per response.
```

### Persona 2: Julian Vance (Suspect)
- **Role & Objective:** Chief museum curator and prime suspect brought in for questioning; he seeks to protect his reputation by defending his alibi, deflecting suspicion, and resisting premature capitulation.
- **Model & Parameters:** `llama3.2:3b`, temperature = 0.5 (cautious, defensive).
- **Full System Prompt:**
```text
You are Julian Vance, chief curator and prime suspect in the theft of the 'Star of Midnight' diamond. Your alibi is that you were having dinner alone across town at the Grand Bistro between 21:00 and 22:30. Defend your alibi, respond cautiously, and do not admit guilt unless backed into a corner. Be concise: 1 to 2 sentences per response.
```

---

## 3. Measurable Definition of "Goal Reached"

> The goal is reached when either the suspect produces an explicit confession acknowledging theft of the diamond, or exactly N turns are completed without confession, verifying that the suspect successfully defended his alibi across the entire budget.

---

## 4. How We Will Tell Whether the Goal Was Reached

> We will tell whether the goal was reached by inspecting the generated transcript for explicit admission keywords (such as `"confess"`, `"caught me"`, or `"I stole"`) and evaluating the `Budget.stop_reason` attribute to verify whether the dialogue terminated via an early `"goal_reached"` stop or the hard `"max_turns"` guardrail.

