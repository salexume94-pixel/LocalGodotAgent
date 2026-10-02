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
