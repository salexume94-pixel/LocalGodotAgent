# Development Log

## Project
Prototype

## Purpose
Historical record of development decisions, completed systems, known issues, and planned work.

## Development History

### 2026-10-02 - Player Defense Verification and Deterministic Source Trace

#### Change
Fixed the LocalGodotAgent's targeted source selection for player-defense questions.

The agent now recognizes player-defense questions and explicitly selects the relevant battle functions:
- `res://battlescreen.gd :: _on_defend_pressed`
- `res://battlescreen.gd :: enemy_turn_after_delay`
- `res://battlescreen.gd :: enemy_attack`

This allows the deterministic player-defense verifier to construct an authoritative source trace before the question is sent to Qwen.

#### Implementation
Added player-defense question detection and targeted source roots in `agent.py`.

The deterministic verification path confirms:
- `_on_defend_pressed()` ends the player's turn.
- `is_defending` is set to `true`.
- The action buttons are updated.
- `enemy_turn_after_delay()` is started.
- `enemy_turn_after_delay()` calls `enemy_attack()`.
- `enemy_attack()` captures the defense state and clears `is_defending`.
- When the player was defending and did not dodge, incoming damage is reduced to 35%.
- A parry chance is calculated from effective luck and effective defense, with the verified range clamped from 10% through 75%.
- A successful parry sets damage to zero.
- Defending therefore reduces incoming damage but does not guarantee zero damage.

#### Verification
Commit `401aa48` (`Fix player defense source path selection`) was verified before this log update.

Checks completed:
- `python -m py_compile .\agent.py` passed.
- `git diff --check` passed.
- The agent successfully detected the player-defense path.
- The run printed `Authoritative verified facts added to summary context.`
- Qwen's final response stayed within the facts established by the deterministic player-defense trace.
- No unsupported enemy-defense interpretation or invented damage formula appeared in the final response.

#### Runtime Diagnostics
Final verification run:
- Final prompt: 13,152 characters.
- Context: 7,401 characters.
- Estimated prompt tokens: ~3,288.
- Ollama prompt tokens: 3,109.
- Ollama generated tokens: 213.
- Ollama total duration: 188.4 seconds.
- Model time: 190.6 seconds.

The runtime is still slow on the current local hardware, but the verification objective for player-defense accuracy was successful.

#### Known Issues
- Qwen can still potentially add claims beyond the deterministic trace when the validator does not explicitly reject them. The successful verification run did not exhibit this problem, but validator coverage remains an accuracy safeguard.
- Ollama prompt evaluation and generation remain relatively slow on the current system.
- The selected enemy resource (`enemies\goblin.tres`) is included in context for combat questions, although the player-defense deterministic trace does not depend on a specific enemy resource.

#### Status
Player-defense deterministic verification is working and has been runtime-tested.

Next development should preserve the deterministic trace and validator architecture while extending verification coverage only where needed.

## 2026-10-02 — Development-Log Retrieval and Qwen 3B Baseline

* Development-history detection now recognizes `dev log` and `devlog` in addition to `development log`.
* Added direct detection for requests asking for the beginning of the development log, including "first few lines", "first lines", "beginning", "start of", "top of", "first part", and "opening lines".
* Added a deterministic development-log answer path so exact beginning-of-log requests read directly from `DEVELOPMENT_LOG.md` instead of invoking the language model.
* Verified the deterministic path successfully returned the first lines of `DEVELOPMENT_LOG.md` without an Ollama request.
* Tested a normal development-history question, "what changes were made to enemy balance", through the existing Qwen 2.5 Coder 3B reasoning path.
* The Qwen 3B test took 344.9 seconds total: 210.9 seconds prompt evaluation, 127.9 seconds response generation, 3.9 seconds model load, with 3,824 prompt tokens and 600 generated tokens.
* The response contained source-mixing and actor attribution errors despite 6,257 characters of targeted source evidence being supplied. In particular, the response incorrectly described the player-defense 35% damage reduction as enemy defense behavior and included additional unsupported enemy/player balance claims.
* This establishes the Qwen 2.5 Coder 3B runtime and answer quality as the baseline for comparison.
* **Attempting to downgrade to see whether a 1.5B–2B model plus our deterministic evidence/validation architecture can give us a sufficiently accurate answer in a fraction of previous times.**

### Verification

* `python -m py_compile .\agent.py` passed.
* `git diff --check` passed.
* Deterministic beginning-of-log retrieval was runtime-tested successfully.
* Qwen 2.5 Coder 3B baseline test completed with the timing and output-quality issues documented above.

### Status

* Development-log retrieval fix is working.
* Qwen 2.5 Coder 3B remains installed as the comparison/control model.
* Smaller-model downgrade testing is the next planned step.

## 2026-10-02 - Qwen 2.5 Coder 1.5B Baseline Test

* Switched the active Ollama model from `qwen2.5-coder:3b` to `qwen2.5-coder:1.5b` for a controlled comparison.
* The 3B model remains installed as the comparison/control model; the 7B model also remains installed.
* Re-ran the exact same development-history question used for the 3B baseline: `ask what changes were made to enemy balance`.
* The 1.5B test used the same targeted source-selection architecture and produced the same 15,897-character final prompt, 10,158-character context, and approximately 3,974 estimated prompt tokens.
* Ollama total duration was 130.6 seconds and the measured model time was 132.8 seconds.
* Ollama HTTP request time was 132.7 seconds.
* Model load time was 2.1 seconds.
* Prompt evaluation took 93.5 seconds.
* Response generation took 35.0 seconds.
* Ollama reported 3,824 prompt tokens and 311 generated tokens.
* Compared with the Qwen 2.5 Coder 3B baseline of 344.9 seconds, the 1.5B model reduced total model time by approximately 61.5%.
* Prompt evaluation decreased from 210.9 seconds to 93.5 seconds, while response generation decreased from 127.9 seconds to 35.0 seconds.
* The 1.5B response remained factually unreliable for historical enemy-balance questions. It presented several specific historical changes as facts without establishing them from the supplied evidence, including claims about Goblin HP, XP, gold, reward items, reward chances, and resource-path changes.
* The response therefore demonstrates a substantial speed improvement but does not by itself solve the source-grounding and historical-attribution problem.
* The result supports continuing to use deterministic retrieval, verified facts, validation, and deterministic fallback paths as the factual authority rather than relying on the language model to independently reconstruct development history.

### Comparison

| Metric | Qwen 2.5 Coder 3B | Qwen 2.5 Coder 1.5B |
|---|---:|---:|
| Total model time | 344.9 s | 132.8 s |
| Prompt evaluation | 210.9 s | 93.5 s |
| Response generation | 127.9 s | 35.0 s |
| Model load | 3.9 s | 2.1 s |
| Prompt tokens | 3,824 | 3,824 |
| Generated tokens | 600 | 311 |

### Verification

* `python -m py_compile .\agent.py` had already passed before the model-selection test.
* The exact same question and retrieval architecture were used for the 1.5B comparison.
* No agent architecture, retrieval logic, validator logic, or deterministic trace logic was changed for this test.
* The 3B baseline remains preserved in the preceding development-log entry.

### Status

* Qwen 2.5 Coder 1.5B is currently the active test model.
* Qwen 2.5 Coder 3B remains installed as the control model.
* Qwen 2.5 Coder 7B remains installed but was not part of this comparison.
* The next diagnostic should test 1.5B against an existing deterministic verification path, such as player-defense, before making architectural changes.


## 2026-10-02 - Qwen 1.5B Player-Defense Repetition Failure

* Tested the active Qwen 2.5 Coder 1.5B model against the existing deterministic player-defense verification path using the question: `ask how does player defense work when the enemy attacks?`.
* The targeted retrieval pipeline remained stable. The final prompt was 15,841 characters, the context was 10,089 characters, and the estimated prompt size was approximately 3,960 tokens.
* Ollama reported 3,826 prompt tokens and 600 generated tokens.
* Ollama total duration was 160.3 seconds and the measured model time was 162.4 seconds.
* Model load time was 2.1 seconds.
* Prompt evaluation took 92.6 seconds.
* Response generation took 65.6 seconds.
* The model did not follow the deterministic player-defense trace. Instead, it repeatedly stated that the player's defense is not reduced by the enemy's attack and continued repeating the same sentence until reaching the 600-token generation limit.
* The response therefore represents a generation/repetition failure rather than a useful interpretation of the supplied verified combat path.
* The failure is notable because the deterministic source trace already established the relevant path: player defense ends the player's turn, sets `is_defending`, leads into `enemy_attack()`, reduces incoming damage to 35% when applicable, and can parry the attack for zero damage.
* No retrieval, prompt, deterministic-trace, or validator architecture changes were made during this test.
* The result confirms that the 1.5B model is substantially faster than 3B but can still fail to terminate coherently even when authoritative deterministic facts are supplied.

### Verification

* Runtime diagnostics were captured from the 1.5B player-defense test.
* The targeted source evidence and deterministic trace were present in the prompt package.
* The response reached the 600-token generation ceiling and exhibited obvious repeated-sentence behavior.
* No source-code or retrieval changes were made for this diagnostic.

### Status

* Qwen 2.5 Coder 1.5B remains the active test model.
* The next controlled change should be limited to deterministic repetition detection in `validate_response()`, with the existing deterministic fallback used when a response contains a clear repetition loop.
* Retrieval, prompt construction, deterministic player-defense tracing, and model selection should remain unchanged for that test.
* After the validator change, rerun the same player-defense question and compare whether the repeated output is rejected and replaced by the verified deterministic fallback.
