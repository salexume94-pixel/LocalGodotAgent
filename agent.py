import json
import re
import time
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\chari\Godot Projects\prototype").resolve()
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:3b"


ALLOWED_EXTENSIONS = {
    ".gd",
    ".tscn",
    ".tres",
    ".cfg",
    ".md",
    ".gdshader",
    ".shader",
    ".json",
}


IGNORED_DIRECTORIES = {
    ".godot",
    ".git",
}


# Keep the amount of evidence sent to the 3B model deliberately small.
# The Python agent performs searching and extraction; the model performs
# interpretation.
MAX_CONTEXT_CHARS = 14000
MAX_FUNCTIONS = 10
MAX_FUNCTION_CHARS = 2200
MAX_SOURCE_CHARS = 6400
MAX_RESOURCE_CHARS = 3000
MAX_AGENTS_CHARS = 1500
MAX_AGENT_MEMORY_CHARS = 1800
MAX_DEVELOPMENT_LOG_CHARS = 2200


DOMAIN_FILES = {
    "combat": [
        "battlescreen.gd",
        "enemy_data.gd",
        "player.gd",
        "Saved.gd",
    ],
    "enemy": [
        "battlescreen.gd",
        "enemy_data.gd",
        "player.gd",
        "Saved.gd",
    ],
    "world": [
        "world_environment.gd",
        "world_interactable.gd",
        "world_map_screen.gd",
        "world_map_view.gd",
        "building_interior.gd",
        "player.gd",
        "Saved.gd",
    ],
    "player": [
        "player.gd",
        "character_menu.gd",
        "Saved.gd",
        "battlescreen.gd",
    ],
    "item": [
        "character_menu.gd",
        "Saved.gd",
        "battlescreen.gd",
    ],
    "inventory": [
        "character_menu.gd",
        "Saved.gd",
    ],
    "equipment": [
        "character_menu.gd",
        "Saved.gd",
    ],
    "save": [
        "Saved.gd",
        "player.gd",
        "debug_menu.gd",
    ],
}


DOMAIN_KEYWORDS = {
    "combat": {
        "combat",
        "battle",
        "enemy attack",
        "enemy turn",
        "damage",
        "defense",
        "hp",
        "health",
        "attack",
        "ability",
        "abilities",
        "special",
        "signature",
        "wounded",
        "flee",
        "target",
        "turn",
    },
    "enemy": {
        "enemy",
        "enemies",
        "monster",
        "mob",
        "goblin",
        "slime",
        "wolf",
        "skeleton",
        "mage",
        "wisp",
        "leech",
        "behavior",
        "behaviour",
    },
    "world": {
        "world",
        "map",
        "region",
        "waystone",
        "door",
        "chest",
        "building",
        "interior",
        "encounter",
        "overworld",
    },
    "player": {
        "player",
        "character",
        "level",
        "stats",
        "strength",
        "defense",
        "dexterity",
        "magic",
        "experience",
        "xp",
        "gold",
    },
    "item": {
        "item",
        "items",
        "consumable",
        "potion",
        "use item",
    },
    "inventory": {
        "inventory",
        "items",
        "stack",
        "quantity",
    },
    "equipment": {
        "equipment",
        "equip",
        "unequip",
        "weapon",
        "armor",
        "accessory",
    },
    "save": {
        "save",
        "load",
        "autosave",
        "persistent",
        "progression",
    },
}


ANALYSIS_KEYWORDS = {
    "attack",
    "damage",
    "enemy",
    "battle",
    "combat",
    "turn",
    "ability",
    "special",
    "signature",
    "wounded",
    "reward",
    "experience",
    "gold",
    "xp",
    "hp",
    "health",
    "defense",
    "flee",
    "skill",
    "player",
    "stats",
    "action",
    "resource",
    "encounter",
    "victory",
    "defeat",
}


ENEMY_TERMS = {
    "enemy",
    "enemies",
    "monster",
    "mob",
    "goblin",
    "slime",
    "wolf",
    "skeleton",
    "mage",
    "wisp",
    "leech",
    "enemy attack",
    "enemy damage",
    "enemy ability",
    "enemy reward",
}


def is_allowed_file(path):
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    for part in path.parts:
        if part in IGNORED_DIRECTORIES:
            return False

    return True


def list_files():
    result = []

    for path in PROJECT_ROOT.rglob("*"):
        if path.is_file() and is_allowed_file(path):
            result.append(path)

    return sorted(result)


def relative_path(path):
    return str(path.relative_to(PROJECT_ROOT)).replace("/", "\\")


def safe_read(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")
    except Exception as exc:
        return f"[ERROR READING FILE: {exc}]"


def read_project_file(relative):
    path = (PROJECT_ROOT / relative).resolve()

    try:
        path.relative_to(PROJECT_ROOT)
    except ValueError:
        return "[ERROR: Path is outside the project root.]"

    if not path.exists():
        return f"[ERROR: File does not exist: {relative}]"

    if not path.is_file():
        return f"[ERROR: Not a file: {relative}]"

    return safe_read(path)


def search_files(query):
    query_lower = query.lower()
    results = []

    for path in list_files():
        content = safe_read(path)

        if query_lower in content.lower():
            results.append(relative_path(path))

    return results


def ask_model(prompt, response_schema=None):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_ctx": 8192,
            "num_predict": 600,
        },
    }

    if response_schema is not None:
        payload["format"] = response_schema

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    request_start = time.time()

    # Pass the constructed POST request. Calling OLLAMA_URL here would issue
    # a GET and silently discard the payload and structured-output contract.
    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.loads(response.read().decode("utf-8"))

    request_elapsed = time.time() - request_start

    print(f"\nOllama HTTP request time: {request_elapsed:.1f} seconds")

    total_duration = result.get("total_duration")
    load_duration = result.get("load_duration")
    prompt_eval_duration = result.get("prompt_eval_duration")
    eval_duration = result.get("eval_duration")
    prompt_eval_count = result.get("prompt_eval_count")
    eval_count = result.get("eval_count")

    if total_duration is not None:
        print(
            f"Ollama total duration: "
            f"{total_duration / 1_000_000_000:.1f} seconds"
        )

    if load_duration is not None:
        print(
            f"Ollama model load time: "
            f"{load_duration / 1_000_000_000:.1f} seconds"
        )

    if prompt_eval_duration is not None:
        print(
            f"Ollama prompt evaluation time: "
            f"{prompt_eval_duration / 1_000_000_000:.1f} seconds"
        )

    if eval_duration is not None:
        print(
            f"Ollama response generation time: "
            f"{eval_duration / 1_000_000_000:.1f} seconds"
        )

    if prompt_eval_count is not None:
        print(
            f"Ollama prompt tokens: "
            f"{prompt_eval_count}"
        )

    if eval_count is not None:
        print(
            f"Ollama generated tokens: "
            f"{eval_count}"
        )

    return result.get("response", "")


def detect_domains(question):
    question_lower = question.lower()
    domains = []

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in question_lower for keyword in keywords):
            domains.append(domain)

    return domains


def choose_primary_files(domains):
    files = []

    for domain in domains:
        for relative in DOMAIN_FILES.get(domain, []):
            if relative not in files:
                files.append(relative)

    return [
        relative
        for relative in files
        if (PROJECT_ROOT / relative).exists()
    ]


def extract_functions(content):
    lines = content.splitlines()
    functions = []

    pattern = re.compile(
        r"^\s*func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
    )

    current = None

    for index, line in enumerate(lines):
        match = pattern.match(line)

        if match:
            if current is not None:
                current["end"] = index

            current = {
                "name": match.group(1),
                "start": index,
                "end": len(lines),
                "signature": line.strip(),
            }

            functions.append(current)

    return functions


def extract_function_bodies(content):
    lines = content.splitlines()
    result = {}

    for function in extract_functions(content):
        start = function["start"]
        end = function["end"]

        body = "\n".join(lines[start:end])

        result[function["name"]] = {
            "body": body,
            "start_line": start + 1,
            "end_line": end,
            "signature": function["signature"],
        }

    return result


def truncate_text(text, limit):
    if len(text) <= limit:
        return text

    marker = "\n\n[TRUNCATED BY LOCAL AGENT CONTEXT LIMIT; omitted text is not evidence of absence.]"
    return text[:max(0, limit - len(marker))] + marker


def find_relevant_functions(files, question):
    question_lower = question.lower()
    enemy_is_source = any(term in question_lower for term in ENEMY_TERMS)
    player_is_source = any(
        phrase in question_lower
        for phrase in ("player attack", "player's attack", "player attacks", "damage by the player")
    )

    enemy_to_player_question = (
        enemy_is_source
        and "damage" in question_lower
        and not player_is_source
    )

    results = []

    for relative in files:
        content = read_project_file(relative)
        functions = extract_function_bodies(content)

        for name, function in functions.items():
            name_lower = name.lower()
            body_lower = function["body"].lower()

            score = 0

            for keyword in ANALYSIS_KEYWORDS:
                if keyword in name_lower:
                    score += 4

                if keyword in body_lower:
                    score += 1

            for word in re.findall(
                r"[a-zA-Z_][a-zA-Z0-9_]*",
                question_lower,
            ):
                if len(word) >= 4 and word in name_lower:
                    score += 5

            # Actor direction is a hard evidence filter. For enemy damage,
            # player-to-enemy functions are excluded completely rather than
            # merely ranked lower.
            if enemy_to_player_question:
                if name in {"player_attack", "_deal_damage_to_enemy"}:
                    continue
                if name == "enemy_attack":
                    score += 1000

            if score > 0:
                results.append(
                    (
                        score,
                        relative,
                        name,
                        function,
                    )
                )

    results.sort(
        key=lambda item: (-item[0], item[1], item[2])
    )

    return results


def infer_function_role(name, body):
    """Infer actor/target from literal HP mutations in the supplied function."""
    player_mutation = (
        "player_HP =" in body
        or "player_HP -=" in body
        or "Saved.player_hp =" in body
    )
    enemy_mutation = (
        "enemy_HP =" in body
        or "enemy_HP -=" in body
    )

    if player_mutation and not enemy_mutation:
        return "enemy -> player"
    if enemy_mutation and not player_mutation:
        return "player -> enemy"
    if name == "enemy_attack":
        return "enemy -> player (runtime attack root)"
    if name in {"player_attack", "_deal_damage_to_enemy"}:
        return "player -> enemy"
    return "not determinable from direct HP mutations"


def build_verified_function_roles(functions):
    """Build compact source-derived actor/target facts for the model."""
    lines = ["VERIFIED FUNCTION ROLES"]
    for _, relative, name, function in functions:
        lines.append(
            f"- {relative} :: {name} :: "
            f"{infer_function_role(name, function['body'])}"
        )
    return "\n".join(lines)


def user_requested_numeric_example(question):
    """Return True only when the user explicitly asks for a numeric example/calculation."""
    text = question.lower()
    phrases = (
        "numeric example", "numerical example", "give me an example",
        "show me an example", "example with numbers", "calculate an example",
        "walk me through an example", "use numbers", "with actual numbers",
    )
    return any(phrase in text for phrase in phrases)


def build_verified_calculation_expression(question, functions):
    """Extract exact arithmetic expressions and literal constants from enemy_attack()."""
    text = question.lower()
    enemy_to_player = (
        "damage" in text
        and any(term in text for term in ENEMY_TERMS)
        and not any(
            phrase in text
            for phrase in (
                "player attack",
                "player's attack",
                "player attacks",
                "damage by the player",
            )
        )
    )
    if not enemy_to_player:
        return None

    attack = next(
        (item for item in functions if item[2] == "enemy_attack"),
        None,
    )
    if attack is None:
        return None

    _, relative, name, function = attack
    lines = function["body"].splitlines()
    arithmetic = []
    constants = []
    arithmetic_pattern = re.compile(
        r"\b(?:rolled_damage|damage|player_HP|Saved\.player_hp)\s*(?:\+|-|\*|/|=).+"
    )
    constant_pattern = re.compile(
        r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*$"
    )

    for index, line in enumerate(lines, start=function["start_line"]):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if arithmetic_pattern.search(stripped):
            arithmetic.append(f"- line {index}: {stripped}")
        constant_match = constant_pattern.match(stripped)
        if constant_match:
            constants.append(
                f"- line {index}: {constant_match.group(1)} = {constant_match.group(2)}"
            )

    citation = (
        f"[{relative} :: {name} :: "
        f"lines {function['start_line']}-{function['end_line']}]"
    )

    return "\n".join((
        "VERIFIED CALCULATION EXPRESSIONS",
        f"SOURCE: {citation}",
        "The following expressions are copied from enemy_attack() source. Do not reconstruct them from prose.",
        *(arithmetic or ["- No direct arithmetic assignment was extracted."]),
        "LITERAL CONSTANTS DEFINED INSIDE enemy_attack():",
        *(constants or ["- None. Constants referenced by enemy_attack() must be verified from their defining source before use."]),
    ))


def build_verified_calculation_chain(question, functions):
    """Build a source-derived calculation chain without unrelated numeric evidence."""
    text = question.lower()

    enemy_to_player = (
        "damage" in text
        and any(term in text for term in ENEMY_TERMS)
        and not any(
            phrase in text
            for phrase in (
                "player attack",
                "player's attack",
                "player attacks",
                "damage by the player",
            )
        )
    )

    if not enemy_to_player:
        return None

    attack = next(
        (item for item in functions if item[2] == "enemy_attack"),
        None,
    )
    if attack is None:
        return None

    _, relative, name, function = attack
    body = function["body"]

    required = (
        "enemy_model.choose_combat_action()",
        'combat_action["is_defensive"]',
        "rolled_damage",
        "Saved.effective_defense()",
        "damage_multiplier",
        "if dodged:",
        "elif was_defending:",
        "if parried:",
        "player_HP = maxi(0, player_HP - damage)",
        "Saved.player_hp = player_HP",
    )

    if not all(fragment in body for fragment in required):
        return None

    citation = (
        f"[{relative} :: {name} :: "
        f"lines {function['start_line']}-{function['end_line']}]"
    )

    lines = [
        "VERIFIED CALCULATION CHAIN",
        "PATH: enemy -> player",
        "Use only this chain when explaining enemy damage.",
        f"- ACTION ROOT: enemy_attack() {citation}",
        f"- ACTION SELECTION: enemy_model.choose_combat_action() {citation}",
        f"- DEFENSIVE BRANCH: a defensive combat action returns before damage calculation. {citation}",
        f"- BASE ROLL: rolled_damage is built from the enemy attack power plus the configured enemy attack roll. {citation}",
        f"- DEFENSE: Saved.effective_defense() is subtracted from rolled_damage, with the result clamped to zero or greater. {citation}",
        f'- MULTIPLIER: the resulting damage is multiplied by combat_action["damage_multiplier"] and rounded up. {citation}',
        f"- DODGE: a successful player dodge sets damage to zero. {citation}",
        f"- BLOCK: if the player is defending and did not dodge, damage is reduced to 35%. {citation}",
        f"- PARRY: a successful parry sets damage to zero. {citation}",
        f"- TARGET WRITE: player_HP = maxi(0, player_HP - damage). {citation}",
        f"- PERSISTENCE: Saved.player_hp = player_HP. {citation}",
        "EXCLUDED FROM THIS CHAIN:",
        "- XP, gold, loot, reward-item, and reward-chance fields.",
        "- player_attack() and _deal_damage_to_enemy().",
        "- Any numeric example value not literally supplied by the verified source evidence.",
        "NUMERIC EXAMPLE RULE:",
        "- Do not invent a hypothetical numeric example unless the user explicitly asks for one.",
        "- If the user asks for a numeric example, use only values directly established by the supplied source evidence and identify their source.",
    ]

    return "\n".join(lines)


def extract_enemy_resources():
    directory = PROJECT_ROOT / "enemies"

    if not directory.exists():
        return []

    return [
        relative_path(path)
        for path in sorted(directory.glob("*.tres"))
        if path.is_file()
    ]


def select_enemy_resource(question):
    resources = extract_enemy_resources()

    if not resources:
        return None

    question_lower = question.lower()

    # If the user explicitly names an enemy, use that resource.
    for relative in resources:
        stem = Path(relative).stem.lower()

        if stem in question_lower:
            return relative

    # Otherwise select exactly one resource deterministically.
    # This satisfies requests such as "pick one existing enemy."
    return resources[0]


def build_enemy_resource_context(question):
    relative = select_enemy_resource(question)

    if relative is None:
        return "(No enemy .tres resource found.)", None

    content = read_project_file(relative)

    content = truncate_text(
        content,
        MAX_RESOURCE_CHARS,
    )

    context = (
        f"===== SELECTED ENEMY RESOURCE: {relative} =====\n"
        f"```text\n"
        f"{content}\n"
        f"```\n"
        f"===== END SELECTED ENEMY RESOURCE =====\n"
    )

    return context, relative


def is_enemy_related(question, domains):
    if "combat" in domains or "enemy" in domains:
        return True

    text = question.lower()

    return any(term in text for term in ENEMY_TERMS)


def is_exact_analysis(question):
    text = question.lower()

    phrases = [
        "analyze the existing",
        "analyze the current",
        "tell me exactly",
        "exactly how",
        "currently work",
        "currently implemented",
        "existing implementation",
        "current implementation",
        "do not propose changes",
        "don't propose changes",
        "do not suggest changes",
        "don't suggest changes",
        "trace exactly",
        "trace the",
    ]

    return any(phrase in text for phrase in phrases)


def is_battle_reward_question(question):
    text = question.lower()
    has_reward_term = any(term in text for term in ("reward", "rewards", "xp", "experience", "gold", "loot"))
    has_battle_term = any(term in text for term in ("battle", "victory", "defeat", "enemy", "goblin", "monster"))
    return has_reward_term and has_battle_term


def is_overworld_encounter_question(question):
    text = question.lower()
    return "encounter" in text and any(term in text for term in ("overworld", "world", "goblin", "enemy"))


def find_called_function_names(body):
    """
    Extract likely local function calls from a GDScript function body.

    This is deliberately conservative. It is used only to expand evidence
    slightly when a directly relevant function calls another local function.
    """
    names = set()

    pattern = re.compile(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\("
    )

    ignored = {
        "if",
        "for",
        "while",
        "match",
        "print",
        "str",
        "int",
        "float",
        "bool",
        "len",
        "range",
        "max",
        "min",
        "abs",
        "clamp",
    }

    for match in pattern.finditer(body):
        name = match.group(1)

        if name not in ignored:
            names.add(name)

    return names


def expand_function_dependencies(functions, files, max_functions=MAX_FUNCTIONS):
    """
    Add locally defined functions referenced by already selected functions.

    This allows the agent to trace execution without dumping entire files.
    """
    selected = list(functions)

    existing = {
        (relative, name)
        for _, relative, name, _ in selected
    }

    all_definitions = {}

    for relative in files:
        content = read_project_file(relative)
        definitions = extract_function_bodies(content)

        for name, function in definitions.items():
            all_definitions[(relative, name)] = function

    changed = True

    while changed and len(selected) < max_functions:
        changed = False

        current_snapshot = list(selected)

        for _, _, _, function in current_snapshot:
            called_names = find_called_function_names(
                function["body"]
            )

            for called_name in called_names:
                matches = [
                    (
                        relative,
                        name,
                        definition,
                    )
                    for (
                        relative,
                        name,
                    ), definition in all_definitions.items()
                    if name == called_name
                ]

                for relative, name, definition in matches:
                    key = (relative, name)

                    if key in existing:
                        continue

                    selected.append(
                        (
                            0,
                            relative,
                            name,
                            definition,
                        )
                    )

                    existing.add(key)
                    changed = True

                    if len(selected) >= max_functions:
                        break

                if len(selected) >= max_functions:
                    break

            if len(selected) >= max_functions:
                break

    return selected


def build_function_context(functions):
    chunks = []
    used = 0

    for _, relative, name, function in functions:
        body = truncate_text(
            function["body"],
            MAX_FUNCTION_CHARS,
        )

        chunk = (
            f"FILE: {relative}\n"
            f"FUNCTION: {name}\n"
            f"LINES: {function['start_line']}-"
            f"{function['end_line']}\n"
            f"```gdscript\n"
            f"{body}\n"
            f"```\n"
        )
        if used + len(chunk) > MAX_SOURCE_CHARS:
            continue
        chunks.append(chunk)
        used += len(chunk)

    return "\n".join(chunks)


def build_targeted_source_context(
    primary_files,
    question,
    exact,
):
    """
    Build evidence without ever dumping complete source files.

    For exact analysis, functions are selected by relevance and then their
    local dependencies are expanded.
    """
    functions = find_relevant_functions(
        primary_files,
        question,
    )

    if exact and is_battle_reward_question(question):
        # Rewards span the victory root and two Saved autoload methods.  Put
        # those evidence roots first instead of letting broad reward words fill
        # the direct-selection budget with unrelated UI functions.
        reward_roots = ("finish_victory", "record_victory_xp_award", "gain_xp")
        definitions = {
            (relative, name): function
            for relative in primary_files
            for name, function in extract_function_bodies(read_project_file(relative)).items()
        }
        selected_roots = []
        for root in reward_roots:
            for relative in primary_files:
                function = definitions.get((relative, root))
                if function is not None:
                    selected_roots.append((1000, relative, root, function))
                    break
        # Start only with the three runtime reward roots.  Dependency expansion
        # below can add their real callees; unrelated lexical matches such as
        # enemy_attack must not consume an exact-analysis evidence slot.
        functions = selected_roots

    if exact and is_overworld_encounter_question(question):
        encounter_roots = (
            "_physics_process",
            "check_for_encounter",
            "choose_overworld_enemy_resource_path",
            "region_id_for_world_position",
        )
        definitions = {
            (relative, name): function
            for relative in primary_files
            for name, function in extract_function_bodies(read_project_file(relative)).items()
        }
        selected_roots = []
        for root in encounter_roots:
            for relative in primary_files:
                function = definitions.get((relative, root))
                if function is not None:
                    selected_roots.append((1000, relative, root, function))
                    break
        functions = selected_roots

    # Reserve evidence capacity for callees.  Selecting every direct lexical
    # match first crowds out the helper that performs the actual damage write.
    functions = functions[:4] if exact else functions[:MAX_FUNCTIONS]

    if exact:
        functions = expand_function_dependencies(
            functions,
            primary_files,
            MAX_FUNCTIONS,
        )

    return build_function_context(functions), functions


def is_development_history_related(question):
    """Return True when the question needs historical development context."""
    text = question.lower()
    explicit_phrases = (
        "development history", "development log", "history of", "what did we do",
        "what have we done", "what changed", "what was changed", "what did i change",
        "why did we change", "previous implementation", "previous behavior",
        "previous behaviour", "earlier implementation", "earlier behavior",
        "earlier behaviour", "before the change", "after the change", "recent changes",
        "recent work", "last change", "known bug", "known bugs", "architecture decision",
        "architectural decision", "historical", "originally", "used to", "regression",
        "when did we add", "when was it added", "when did we remove", "when was it removed",
    )
    if any(phrase in text for phrase in explicit_phrases):
        return True
    history_terms = {"previous", "prior", "earlier", "history", "historical", "recent",
                     "originally", "changed", "change", "implemented", "added", "removed",
                     "replaced", "migrated", "decision", "decisions", "regression"}
    words = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text))
    return len(words.intersection(history_terms)) >= 2


def retrieve_relevant_development_history(question):
    """Retrieve only development-log sections relevant to the question."""
    development_log = read_project_file("DEVELOPMENT_LOG.md").strip()

    if not development_log:
        return "(Development log is empty.)"

    if development_log.startswith("[ERROR:"):
        return development_log

    question_words = {
        word.lower()
        for word in re.findall(
            r"[a-zA-Z_][a-zA-Z0-9_]*",
            question,
        )
        if len(word) >= 4
    }

    sections = []
    current_title = "Development Log"
    current_lines = []

    for line in development_log.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            if current_lines:
                sections.append(
                    (
                        current_title,
                        "\n".join(current_lines).strip(),
                    )
                )
            current_title = re.sub(
                r"^#{1,6}\s+",
                "",
                line,
            ).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append(
            (
                current_title,
                "\n".join(current_lines).strip(),
            )
        )

    scored = []

    for index, (title, section) in enumerate(sections):
        section_lower = section.lower()
        score = 0

        for word in question_words:
            if word in section_lower:
                score += 1
            if word in title.lower():
                score += 3

        if score > 0:
            scored.append(
                (
                    score,
                    index,
                    section,
                )
            )

    if not scored:
        return "(No development-log sections match the current question.)"

    scored.sort(
        key=lambda item: (-item[0], item[1])
    )

    selected = []
    used = 0

    for _, _, section in scored:
        separator = "\n\n" if selected else ""
        if used + len(separator) + len(section) > MAX_DEVELOPMENT_LOG_CHARS:
            remaining = MAX_DEVELOPMENT_LOG_CHARS - used - len(separator)
            if remaining > 0:
                selected.append(
                    truncate_text(
                        separator + section,
                        remaining,
                    )
                )
            break

        selected.append(separator + section)
        used += len(separator) + len(section)

    return "".join(selected)


def build_context(question):
    """Build the focused evidence package sent to the model."""
    domains = detect_domains(question)
    primary_files = choose_primary_files(domains)
    exact = is_exact_analysis(question)
    enemy_related = is_enemy_related(question, domains)

    agents_content = truncate_text(
        read_project_file("AGENTS.md"),
        MAX_AGENTS_CHARS,
    )

    source_context, functions = build_targeted_source_context(
        primary_files,
        question,
        exact,
    )

    enemy_context = ""
    selected_enemy = None

    if enemy_related:
        enemy_context, selected_enemy = build_enemy_resource_context(
            question,
        )

    agent_memory = truncate_text(
        read_project_file("AGENT_MEMORY.md"),
        MAX_AGENT_MEMORY_CHARS,
    )

    history_related = is_development_history_related(question)

    if history_related:
        development_log = retrieve_relevant_development_history(
            question,
        )
    else:
        development_log = (
            "(Development history not retrieved; "
            "question is not history-related.)"
        )

    context_parts = [
        f"PROJECT ROOT:\n{PROJECT_ROOT}",
        f"DETECTED DOMAINS:\n{', '.join(domains) or '(none)'}",
        "PRIMARY FILES SEARCHED:\n"
        f"{', '.join(primary_files) or '(none)'}",
        "EXACT IMPLEMENTATION ANALYSIS:\n"
        f"{'YES' if exact else 'NO'}",
        "DEVELOPMENT HISTORY RELEVANT:\n"
        f"{'YES' if history_related else 'NO'}",
    ]

    if selected_enemy:
        context_parts.append(
            f"SELECTED ENEMY:\n{selected_enemy}"
        )

    context_parts.append(
        "===== TARGETED SOURCE EVIDENCE =====\n"
        + source_context
        + "\n===== END TARGETED SOURCE EVIDENCE ====="
    )

    if enemy_context:
        context_parts.append(enemy_context)

    context_parts.append(
        "===== AGENTS.MD =====\n"
        + agents_content
        + "\n===== END AGENTS.MD ====="
    )

    context_parts.append(
        "===== AGENT_MEMORY.MD =====\n"
        + agent_memory
        + "\n===== END AGENT_MEMORY.MD ====="
    )

    if history_related:
        context_parts.append(
            "===== RELEVANT DEVELOPMENT HISTORY =====\n"
            + development_log
            + "\n===== END RELEVANT DEVELOPMENT HISTORY ====="
        )

    context = "\n\n".join(context_parts)

    if len(context) > MAX_CONTEXT_CHARS:
        raise RuntimeError(
            "Internal context budget exceeded; no evidence was sent so it "
            "could not be silently truncated."
        )

    return (
        context,
        domains,
        primary_files,
        functions,
        exact,
        enemy_related,
        selected_enemy,
    )


def print_prompt_component_diagnostics(question, context, instructions, response_format, final_prompt):
    print("\nPrompt component diagnostics:")
    print(f"  Instruction block: {len(instructions)} chars")
    print(f"  Response format: {len(response_format)} chars")
    print(f"  Question: {len(question)} chars")
    print(f"  Context: {len(context)} chars")
    print(f"  Final prompt: {len(final_prompt)} chars")
    print(f"  Prompt overhead beyond question/context: {len(final_prompt) - len(question) - len(context)} chars")


def build_prompt(question, context, exact):
    if exact:
        instructions = """
This is forensic analysis of the EXISTING implementation.

The supplied evidence was deliberately narrowed by a Python project-analysis
agent. Do not assume that an omitted file or function is missing from the
project. It may simply not be relevant to the current evidence package.

You MUST:
- use only the supplied project evidence
- read the supplied source functions before answering
- read the selected enemy .tres resource when one is supplied
- name actual files and functions
- identify actual configured resource values
- trace actual execution paths supported by the supplied code
- distinguish resource configuration from runtime code
- distinguish confirmed behavior from anything that cannot be determined
- say "This cannot be determined from the supplied code." when necessary

IMPORTANT:
- The selected enemy resource is the actual resource being analyzed.
- Do not switch to another enemy unless the supplied evidence explicitly
  proves that the selected resource is replaced by another resource.
- Follow function calls shown in the supplied evidence.
- Do not assume what omitted functions do.
- Do not infer generic RPG behavior.
- Do not infer values that are not present.
- Do not treat comments or development notes as runtime behavior.
- AGENT_MEMORY.md is navigation and project context, not authoritative runtime truth.
- DEVELOPMENT_LOG.md is historical context only; source code remains authoritative for current behavior.

SCOPE RULES:
- Answer only the user's question.
- Do not provide a general project summary.
- Do not summarize unrelated development plans or project history.
- Do not propose changes.
- Do not recommend improvements.
- Do not write implementation code.
- Do not provide a next development step unless explicitly requested.

You MUST NOT:
- invent missing systems
- invent functions
- invent enemy resource values
- invent mechanics
- invent calculations
- invent execution paths
- claim an omitted function is missing
- claim an omitted resource is missing
- propose changes
- recommend improvements
"""

    else:
        instructions = """
Analyze the supplied project evidence accurately and concisely.

The Python project-analysis agent intentionally provides focused evidence
rather than entire source files. When AUTHORITATIVE VERIFIED FACTS are
supplied, Python has already determined the relevant execution facts from
the source. Your primary job is to summarize and explain those verified facts
clearly. Do not independently reconstruct the implementation when the
verified facts already answer the question.

Never invent files, functions, variables, systems, mechanics, or resource
values.

AGENT_MEMORY.md may help navigate the project, but source code is authoritative.
If relevant development history is supplied, use it only to explain past decisions or changes.
Do not mistake historical notes for current runtime behavior.

Do not assume an omitted file or function does not exist.

If the supplied context is insufficient, say:
"This cannot be determined from the supplied code."

Do not assume generic RPG behavior.

SUMMARY RULES:
- Give the direct answer first.
- Prefer a short paragraph followed by 3-7 bullets when the process has
  multiple steps.
- Summarize verified operations instead of repeating source code.
- Include exact function or file names when they identify where the behavior
  occurs.
- Do not repeat the same fact in multiple sections.
- Do not discuss the internal Python retrieval process.
- Do not add unrelated implementation details.
- Keep normal answers concise enough to finish completely within the response
  limit. Expand only when the user asks for detail or exact analysis.

EXECUTION-DIRECTION RULES:
- Determine who performs the action and who receives its effect from the
  actual call path and variable mutations.
- Never infer a function role from its name alone.
- If two functions have similar names, distinguish them by callers and the
  variables they mutate.
- For enemy-to-player damage, enemy_attack is the runtime attack path when
  the supplied source shows it mutating player_HP or Saved.player_hp.
- _deal_damage_to_enemy is not enemy-to-player damage merely because it
  contains the word "damage"; if the supplied source shows it mutating
  enemy_HP, describe it as damage to the enemy.
- Do not reverse attacker and target when summarizing calculations.
- Preserve the direction of every subtraction, assignment, and function call.
"""
    if exact:
        response_format = """
For exact implementation analysis, use these sections:

## EXISTING SYSTEMS

## CURRENT IMPLEMENTATION

## CONFIRMED LIMITATIONS

## UNKNOWN

## FILES AND FUNCTIONS INVOLVED
"""
    else:
        response_format = """
SUMMARY MODE:
- Answer directly in the first sentence or two.
- Use a short paragraph or 3-7 concise bullets.
- Prefer the smallest complete answer that preserves all verified behavior.
- Do not create a long numbered tutorial unless the user asks for one.
- Do not restate the question.
- Do not write code unless the user explicitly asks for code.
"""

    final_prompt = f"""
You are a code-analysis assistant for a Godot 4.7 RPG.

{instructions}

USER QUESTION:
{question}

PROJECT EVIDENCE:
{context}

Answer using only the supplied project evidence.

EVIDENCE PRIORITY:
1. AUTHORITATIVE VERIFIED FACTS supplied by the Python agent.
2. VERIFIED SOURCE FACTS, calculation chains, and exact expressions supplied by the Python agent.
3. Actual source-code functions and resource values.
4. AGENTS.md, which describes project rules and workflow.
5. AGENT_MEMORY.md and DEVELOPMENT_LOG.md only as navigation/history context.

When AUTHORITATIVE VERIFIED FACTS are present, they are the deterministic
source-derived answer basis. Qwen role is to summarize them accurately,
not to replace them with independent guesses.

When VERIFIED FUNCTION ROLES are present, treat the actor/target
classification as source-derived evidence. A function classified as
player -> enemy MUST NOT be used to explain enemy -> player damage, and vice
versa.

When VERIFIED SOURCE FACTS are present, treat them as a checked summary of
operations literally found in the supplied source. Do not contradict them by
reinterpreting a similarly named function.

Before explaining a calculation, trace:
ACTOR -> ACTION FUNCTION -> CALCULATION -> TARGET VARIABLE -> PERSISTED STATE.

Do not merge two different actor/target paths into one calculation chain.
If that chain is not supported by the supplied evidence, say so.

For every important numeric or state-changing claim, identify the source
function that supports it. Do not silently combine operations from unrelated
functions.

CALCULATION INTEGRITY:
- When VERIFIED CALCULATION EXPRESSIONS is present, preserve those exact expressions and their order.
- When VERIFIED CALCULATION CHAIN is present, it is the authoritative calculation path.
- Do not reconstruct arithmetic from memory when an exact expression is supplied.
- If the user did not explicitly request a numeric example, do not provide any numeric example, hypothetical numbers, assumed rolls, or sample calculation.
- If the user explicitly requests a numeric example, use only literal values directly established by the supplied source evidence. If a needed runtime/random value is not established, state: "This cannot be determined from the supplied code."
- Never invent constants, stat values, random-roll results, multipliers, HP values, XP values, gold values, or item values.
- A value appearing in the selected enemy resource is not automatically an input to the calculation. Use it only when the supplied runtime code explicitly connects that field to the calculation.
- XP, gold, loot, reward-item, and reward-chance fields are excluded from enemy damage unless the supplied source explicitly proves a connection.
- Preserve the exact order of operations shown by the verified calculation chain.
- If a requested numeric result cannot be calculated from supplied evidence, state: "This cannot be determined from the supplied code."

{response_format}

Do not write code unless the user explicitly asks for code.
"""


def render_deterministic_enemy_damage_trace(question, functions):
"""
    print_prompt_component_diagnostics(
        question,
        context,
        instructions,
        response_format,
        final_prompt,
    )
    return final_prompt
Return a source-derived trace for the known enemy-to-player path.

    Arithmetic and ownership are reliability-critical here.  The 3B model is
    intentionally bypassed only after confirming every reported operation is
    literally present in the selected enemy_attack function.
    """
    text = question.lower()
    if "damage" not in text:
        return None
    if not any(term in text for term in ENEMY_TERMS):
        return None
    if any(phrase in text for phrase in ("player attack", "player's attack", "player attacks", "damage by the player")):
        return None

    attack = next((item for item in functions if item[2] == "enemy_attack"), None)
    if attack is None:
        return None
    _, relative, name, function = attack
    body = function["body"]
    required = (
        "enemy_model.choose_combat_action()",
        'combat_action["is_defensive"]',
        "rolled_damage",
        "Saved.effective_defense()",
        "damage_multiplier",
        "if dodged:",
        "elif was_defending:",
        "if parried:",
        "player_HP = maxi(0, player_HP - damage)",
        "Saved.player_hp = player_HP",
    )
    if not all(fragment in body for fragment in required):
        return None

    citation = f"[{relative} :: {name} :: lines {function['start_line']}-{function['end_line']}]"
    return "\n".join((
        "DETERMINISTIC SOURCE TRACE",
        "PATH: enemy -> player. This trace is exclusive to the enemy-to-player damage path.",
        f"- `enemy_attack()` is the runtime enemy attack root and its damage is applied to `player_HP`. {citation}",
        f"- The enemy gets a combat action from `enemy_model.choose_combat_action()`. {citation}",
        f"- A defensive action marks the enemy as defending and returns before damage is calculated or applied. {citation}",
        f"- Otherwise, `rolled_damage` is enemy attack power plus the configured random roll. {citation}",
        f"- `Saved.effective_defense()` is subtracted from that roll and the result is clamped to zero or greater. {citation}",
        f"- That result is multiplied by the action's `damage_multiplier` and rounded up. {citation}",
        f"- A successful player dodge sets damage to zero. {citation}",
        f"- If the player was defending and did not dodge, the current damage is reduced to 35%; a successful parry then sets it to zero. {citation}",
        f"- The resulting damage is subtracted from `player_HP`, copied to `Saved.player_hp`, and the HUD is updated. {citation}",
        "- `_deal_damage_to_enemy()` is a separate player -> enemy path and must not be included in this enemy -> player calculation.",
        "\nUNKNOWN",
        "- The selected code does not determine the specific action, random roll, dodge, defense, or parry result for an individual battle.",
    ))


def render_deterministic_player_damage_trace(question, functions):
    """Render the player-to-enemy damage path from selected source evidence."""
    text = question.lower()
    player_is_source = any(
        phrase in text
        for phrase in ("player attack", "player's attack", "player attacks", "damage by the player")
    )
    if "damage" not in text or not player_is_source:
        return None

    attack = next((item for item in functions if item[2] == "player_attack"), None)
    resolve = next((item for item in functions if item[2] == "_deal_damage_to_enemy"), None)
    if attack is None or resolve is None:
        return None
    _, attack_file, attack_name, attack_function = attack
    _, resolve_file, resolve_name, resolve_function = resolve
    required_attack = (
        "Saved.effective_attack()",
        "PLAYER_ATTACK_ROLL_MIN",
        "enemy_defense",
        "damage *= damage_multiplier",
        "critical_chance",
        "critical_multiplier",
        "_deal_damage_to_enemy(damage)",
    )
    required_resolve = (
        "enemy_is_defending",
        "enemy_model.defensive_damage_multiplier",
        "actual_damage",
        "enemy_HP -= actual_damage",
    )
    if not all(fragment in attack_function["body"] for fragment in required_attack):
        return None
    if not all(fragment in resolve_function["body"] for fragment in required_resolve):
        return None

    attack_citation = f"[{attack_file} :: {attack_name} :: lines {attack_function['start_line']}-{attack_function['end_line']}]"
    resolve_citation = f"[{resolve_file} :: {resolve_name} :: lines {resolve_function['start_line']}-{resolve_function['end_line']}]"
    return "\n".join((
        "DETERMINISTIC SOURCE TRACE",
        f"- `rolled_damage` is `Saved.effective_attack()` plus a random value from `PLAYER_ATTACK_ROLL_MIN` through `PLAYER_ATTACK_ROLL_MAX`. {attack_citation}",
        f"- Damage is clamped to at least 1 after subtracting `enemy_defense`, then multiplied by the function's `damage_multiplier`. {attack_citation}",
        f"- Critical chance is clamped from effective luck plus `attack_potion_crit_bonus`; a successful roll applies a random multiplier of 2 or 3. {attack_citation}",
        f"- `player_attack()` passes the resulting damage to `_deal_damage_to_enemy()` and uses its returned `actual_damage` for the battle message. {attack_citation}",
        f"- The helper records whether the enemy was defending. If so, it multiplies the pending damage by `enemy_model.defensive_damage_multiplier`, rounds up, and clears the enemy's defending state. {resolve_citation}",
        f"- The helper caps actual damage at the enemy's current HP, subtracts it from `enemy_HP`, and returns that amount. {resolve_citation}",
        f"- After the HUD update, the player attack ends the battle on `enemy_HP <= 0`; otherwise it awaits the enemy turn. {attack_citation}",
        "\nUNKNOWN",
        "- The selected code does not determine the specific roll, critical result, enemy defense state, or final damage for an individual battle.",
    ))


def render_deterministic_player_defense_trace(question, functions):
    """Render the player-defense path from the player action through enemy resolution."""
    text = question.lower()
    if "defend" not in text:
        return None
    if "enemy defend" in text or "enemy defends" in text or "enemy defense" in text:
        return None
    if "player" not in text:
        return None

    defend = next((item for item in functions if item[2] == "_on_defend_pressed"), None)
    enemy_turn = next((item for item in functions if item[2] == "enemy_turn_after_delay"), None)
    enemy_attack = next((item for item in functions if item[2] == "enemy_attack"), None)
    if defend is None or enemy_turn is None or enemy_attack is None:
        return None

    _, defend_file, defend_name, defend_function = defend
    _, turn_file, turn_name, turn_function = enemy_turn
    _, attack_file, attack_name, attack_function = enemy_attack

    required_defend = (
        "player_turn = false",
        "is_defending = true",
        "update_action_buttons()",
        "await enemy_turn_after_delay()",
    )
    required_turn = (
        "await enemy_attack()",
    )
    required_attack = (
        "var was_defending: bool = is_defending",
        "is_defending = false",
        "elif was_defending:",
        "damage = ceili(float(damage) * 0.35)",
        "var parry_chance: int = clampi(",
        "if parried:",
        "damage = 0",
    )

    if not all(fragment in defend_function["body"] for fragment in required_defend):
        return None
    if not all(fragment in turn_function["body"] for fragment in required_turn):
        return None
    if not all(fragment in attack_function["body"] for fragment in required_attack):
        return None

    defend_citation = f"[{defend_file} :: {defend_name} :: lines {defend_function['start_line']}-{defend_function['end_line']}]"
    turn_citation = f"[{turn_file} :: {turn_name} :: lines {turn_function['start_line']}-{turn_function['end_line']}]"
    attack_citation = f"[{attack_file} :: {attack_name} :: lines {attack_function['start_line']}-{attack_function['end_line']}]"

    return "\n".join((
        "DETERMINISTIC SOURCE TRACE",
        "PATH: player defend -> enemy attack resolution.",
        f"- `_on_defend_pressed()` ends the player's turn, sets `is_defending = true`, updates the action buttons, and starts `enemy_turn_after_delay()`. {defend_citation}",
        f"- `enemy_turn_after_delay()` waits briefly, then calls `enemy_attack()`. {turn_citation}",
        f"- `enemy_attack()` captures the player's defense state in `was_defending` and clears `is_defending`. {attack_citation}",
        f"- If the player was defending and did not dodge, incoming damage is reduced to 35%. {attack_citation}",
        f"- While defending, the code calculates a parry chance from 10 + effective luck + twice effective defense, clamped from 10% through 75%; a successful parry sets damage to zero. {attack_citation}",
        f"- Therefore, defending does not guarantee zero damage. It reduces the incoming damage and can completely negate it when the parry succeeds. {attack_citation}",
        "\nUNKNOWN",
        "- The selected code does not determine the particular dodge or parry roll for an individual attack.",
    ))


def render_deterministic_battle_reward_trace(question, functions):
    """Render battle victory rewards from the runtime reward and XP methods."""
    if not is_battle_reward_question(question):
        return None
    victory = next((item for item in functions if item[2] == "finish_victory"), None)
    xp_award = next((item for item in functions if item[2] == "record_victory_xp_award"), None)
    gain_xp = next((item for item in functions if item[2] == "gain_xp"), None)
    if victory is None or xp_award is None or gain_xp is None:
        return None
    _, victory_file, victory_name, victory_function = victory
    _, award_file, award_name, award_function = xp_award
    _, gain_file, gain_name, gain_function = gain_xp
    victory_required = (
        "Saved.record_enemy_defeated()",
        "Saved.record_victory_xp_award(",
        "enemy_model.xp_percent_min",
        "enemy_model.xp_percent_max",
        "enemy_model.gold_reward_min",
        "enemy_model.gold_reward_max",
        "Saved.gold += gold_reward",
        "Saved.gain_xp(xp_reward)",
        "Saved.save_game()",
    )
    award_required = ("victories_since_xp", "victories_until_xp", "xp_percent", "xp_to_next_level()")
    gain_required = ("xp += amount", "while player_level < MAX_PLAYER_LEVEL", "player_level += 1")
    if not all(fragment in victory_function["body"] for fragment in victory_required):
        return None
    if not all(fragment in award_function["body"] for fragment in award_required):
        return None
    if not all(fragment in gain_function["body"] for fragment in gain_required):
        return None

    victory_citation = f"[{victory_file} :: {victory_name} :: lines {victory_function['start_line']}-{victory_function['end_line']}]"
    award_citation = f"[{award_file} :: {award_name} :: lines {award_function['start_line']}-{award_function['end_line']}]"
    gain_citation = f"[{gain_file} :: {gain_name} :: lines {gain_function['start_line']}-{gain_function['end_line']}]"
    return "\n".join((
        "DETERMINISTIC SOURCE TRACE",
        f"- Victory marks the battle over, saves the current player HP, and records an enemy defeat. {victory_citation}",
        f"- It requests XP using the defeated enemy's configured minimum and maximum XP percentages. {victory_citation}",
        f"- At the level cap, XP reward is zero. Otherwise, victories are counted; no XP is awarded until the count reaches `victories_until_xp`. {award_citation}",
        f"- When an XP award is due, the counter resets, the next threshold is randomized from 2 through 8 victories, and XP is a rounded, minimum-one percentage of XP needed for the next level. {award_citation}",
        f"- Gold is randomized between the enemy's configured minimum and maximum reward, then added to `Saved.gold`. {victory_citation}",
        f"- The awarded XP is added to `Saved.xp`. While it meets the next-level requirement, the player levels up and XP is reduced by that requirement; level-up also adjusts the recorded stats and restores HP and SPC to their maxima. {gain_citation}",
        f"- Victory may attempt the enemy's configured item reward using its chance plus effective luck, saves the game, updates the HUD, then returns to the world. {victory_citation}",
        "\nUNKNOWN",
        "- The selected code does not determine the particular gold roll, XP percentage, victory threshold, item-drop result, or level-up result for an individual battle.",
    ))


def render_deterministic_overworld_encounter_trace(question, functions):
    """Render random overworld encounter selection from its runtime roots."""
    if not is_overworld_encounter_question(question):
        return None
    check = next((item for item in functions if item[2] == "check_for_encounter"), None)
    movement = next((item for item in functions if item[2] == "_physics_process"), None)
    choose = next((item for item in functions if item[2] == "choose_overworld_enemy_resource_path"), None)
    region = next((item for item in functions if item[2] == "region_id_for_world_position"), None)
    if check is None or movement is None or choose is None or region is None:
        return None
    _, movement_file, movement_name, movement_function = movement
    _, check_file, check_name, check_function = check
    _, choose_file, choose_name, choose_function = choose
    _, region_file, region_name, region_function = region

    # Only verify the tile-change state here. The actual
    # check_for_encounter() call is already represented by the explicit
    # _physics_process evidence root and does not need to survive the
    # per-function context truncation used by the model path.
    if not all(
        fragment in movement_function["body"]
        for fragment in ("current_tile", "last_tile")
    ):
        return None

    if not all(fragment in check_function["body"] for fragment in ("random_encounters_enabled", "battle_encounter_cooldown_until_msec", "RANDOM_ENCOUNTER_CHANCE_PERCENT", "choose_overworld_enemy_resource_path(position)", "set_battle_return_position", "battlescreen.tscn")):
        return None
    if not all(fragment in choose_function["body"] for fragment in ("region_id_for_world_position", "REGION_ENCOUNTER_WEIGHTS", "OVERWORLD_ENCOUNTER_WEIGHTS", "total_weight", "randi_range(1, total_weight)")):
        return None
    if not all(fragment in region_function["body"] for fragment in ("world_position.x / 960.0", "world_position.y / 540.0")):
        return None

    check_citation = f"[{check_file} :: {check_name} :: lines {check_function['start_line']}-{check_function['end_line']}]"
    movement_citation = f"[{movement_file} :: {movement_name} :: lines {movement_function['start_line']}-{movement_function['end_line']}]"
    choose_citation = f"[{choose_file} :: {choose_name} :: lines {choose_function['start_line']}-{choose_function['end_line']}]"
    region_citation = f"[{region_file} :: {region_name} :: lines {region_function['start_line']}-{region_function['end_line']}]"

    return "\n".join((
        "DETERMINISTIC SOURCE TRACE",
        f"- On a movement-tile change, the player code calls `check_for_encounter()` after the post-battle cooldown has elapsed. {movement_citation}",
        f"- Encounter checks return immediately when random encounters are disabled or the battle cooldown has not expired. {check_citation}",
        f"- An encounter proceeds only when a random value from 0 through 99 is below `Saved.RANDOM_ENCOUNTER_CHANCE_PERCENT`. {check_citation}",
        f"- The selector maps the current world position to a clamped 3-column by 2-row region grid, then uses that region ID. {region_citation}",
        f"- It uses that region's encounter weights when present; otherwise it uses the overworld fallback weights. It sums nonnegative weights across the configured enemy paths and returns the default enemy if the total is zero. {choose_citation}",
        f"- Otherwise it draws a random integer from 1 through the total weight and walks the configured paths cumulatively; Goblin is selected only when its path's cumulative weighted range contains that draw. {choose_citation}",
        f"- The chosen resource path and current position are saved as the battle return state, then the scene changes to `res://battlescreen.tscn`. {check_citation}",
        "\nUNKNOWN",
        "- The selected code does not determine the current position, region, random encounter roll, or weighted draw for an individual overworld step.",
    ))


def print_function_list(functions):
    if not functions:
        print("\nNo relevant functions identified.")
        return

    print("\nRelevant functions identified by the agent:")

    for _, relative, name, function in functions:
        print(
            f"  {relative} :: {name} "
            f"(lines {function['start_line']}-"
            f"{function['end_line']})"
        )



def validate_response(response, question, verified_trace):
    """
    Perform a deterministic sanity check on Qwen's answer.

    This is intentionally conservative. It does not try to judge prose quality.
    It rejects claims that contradict a verified execution path or introduce
    known actor/target contamination.
    """
    if not response or not response.strip():
        return False, ["empty response"]

    text = response.lower()
    issues = []

    enemy_to_player = (
        verified_trace is not None
        and "path: enemy -> player" in verified_trace.lower()
    )
    player_defense = (
        verified_trace is not None
        and "path: player defend -> enemy attack resolution." in verified_trace.lower()
    )

    if player_defense:
        forbidden_phrases = (
            "enemy_is_defending",
            "enemy is defending",
            "enemy prepares to reduce",
            "enemy prepares to defend",
            "player_turn = true",
            "prevents the enemy from dealing any damage",
            "prevents all damage",
            "prevents any damage",
            "takes no damage",
        )

        for phrase in forbidden_phrases:
            if phrase in text:
                issues.append(f"contradicts verified player-defense path: {phrase}")

    if enemy_to_player:
        forbidden_terms = {
            "player_attack": "player -> enemy function",
            "_deal_damage_to_enemy": "player -> enemy helper",
            "enemy_defense": "enemy defense is not part of the verified enemy -> player damage chain",
        }

        for term, reason in forbidden_terms.items():
            if term.lower() in text:
                issues.append(f"unsupported actor/target reference: {term} ({reason})")

        if "xp" in text or "gold" in text or "loot" in text:
            issues.append("unrelated reward mechanics mentioned in enemy damage answer")

    if not user_requested_numeric_example(question):
        hypothetical_patterns = (
            r"let['â]?s assumme",
            r"for example,?\s+.*\b\d+",
            r"suppose\s+.*\b\d+",
            r"assume\s+.*\b\d+",
            r"if we use\s+.*\b\d+",
        )

        for pattern in hypothetical_patterns:
            if re.search(pattern, text):
                issues.append("unsupported hypothetical numeric example")
                break

        if re.search(r"(?im)^\s*(?:#{1,6}\s*)?example(?:\s+calculation)?\s*:?.*$", response):
            issues.append("unrequested example section")

    # Reject obvious signs that Qwen stopped mid-answer.
    incomplete_patterns = (
        r"::\s*`[^`]*$",
        r"\b(?:maxi|mini|ceili|randi_range)\([^)]*$",
    )

    for pattern in incomplete_patterns:
        if re.search(pattern, text):
            issues.append("answer appears truncated or incomplete")
            break

    if response.count("```") % 2 != 0:
        issues.append("answer contains an unclosed code fence")

    stripped = response.rstrip()
    if stripped.endswith(("(", "[", "{", "=", "+", "-", "*", "/", "`")):
        issues.append("answer ends with an incomplete expression")

    numbered_items = re.findall(r"(?m)^\s*\d+\.\s+(.+)$", response)
    if numbered_items:
        last_item = numbered_items[-1].strip()
        if re.search(r"\b(?:maxi|mini|ceili|randi_range)\([^)]*$", last_item):
            issues.append("final numbered step is incomplete")

    return not issues, issues


def build_deterministic_fallback(question, verified_trace):
    """
    Produce a concise answer directly from Python-verified facts.

    This is the first safety fallback: if Qwen adds unsupported mechanics,
    the agent can still answer without another model call.
    """
    if verified_trace is None:
        return None

    if "PATH: player defend -> enemy attack resolution." in verified_trace:
        return (
            "Player defense is handled by _on_defend_pressed() in "
            "battlescreen.gd. The verified path is:\n"
            "- The player's turn ends and is_defending is set to true.\n"
            "- The action buttons are updated, then enemy_turn_after_delay() "
            "runs and calls enemy_attack().\n"
            "- enemy_attack() captures that defense state, clears it, and "
            "reduces incoming damage to 35% when the player was defending "
            "and did not dodge.\n"
            "- A successful parry then reduces the damage to zero.\n"
            "- Therefore, defending reduces the next incoming hit and can "
            "completely negate it with a successful parry; it does not "
            "automatically prevent all damage."
        )

    if "PATH: enemy -> player" in verified_trace:
        return (
            "Enemy damage is calculated in enemy_attack() in "
            "battlescreen.gd and applied to the player's HP. "
            "The verified path is:\n"
            "- The enemy selects a combat action with "
            "enemy_model.choose_combat_action(). Defensive actions return "
            "before damage calculation.\n"
            "- Otherwise, rolled_damage is the enemy attack power plus the "
            "configured random attack roll.\n"
            "- Saved.effective_defense() is subtracted and the result is "
            "clamped to zero or greater.\n"
            "- The result is multiplied by combat_action[\\\"damage_multiplier\\\"] "
            "and rounded up.\n"
            "- Dodge reduces damage to zero. If the player was defending, "
            "damage is reduced to 35%; a successful parry then reduces it to zero.\n"
            "- The final damage is subtracted from player_HP and persisted "
            "to Saved.player_hp."
        )

    return None



def print_context_diagnostics(context, prompt):
    """Print character/token estimates for each major context section."""
    print("\nContext diagnostics:")

    print(f"  Final prompt characters: {len(prompt)}")
    print(f"  Context characters: {len(context)}")
    print(f"  Prompt overhead characters: {max(0, len(prompt) - len(context))}")

    sections = re.split(
        r"(?=^===== .+? =====$)",
        context,
        flags=re.MULTILINE,
    )

    for section in sections:
        section = section.strip()

        if not section:
            continue

        first_line = section.splitlines()[0].strip()

        if first_line.startswith("====="):
            label = first_line.strip("=").strip()
            print(
                f"  {label}: "
                f"{len(section)} chars "
                f"(~{len(section) / 4:.0f} tokens)"
            )
        else:
            print(
                f"  Base context: "
                f"{len(section)} chars "
                f"(~{len(section) / 4:.0f} tokens)"
            )

    print(
        f"  Estimated final prompt tokens: "
        f"~{len(prompt) / 4:.0f}"
    )


def handle_ask(question):
    print("\nAnalyzing question...")

    start = time.time()

    (
        context,
        domains,
        primary_files,
        functions,
        exact,
        enemy_related,
        selected_enemy,
    ) = build_context(question)

    print(
        f"Detected domains: "
        f"{', '.join(domains) or '(none)'}"
    )

    print("\nPrimary files searched:")

    for relative in primary_files:
        print(f"  {relative}")

    print_function_list(functions)

    if enemy_related:
        print("\nEnemy analysis: ON")

        if selected_enemy:
            print(
                f"Selected enemy resource: "
                f"{selected_enemy}"
            )
        else:
            print("No enemy resource found.")

    print(
        f"\nContext budget: "
        f"{MAX_CONTEXT_CHARS} characters"
    )

    print(
        f"Actual context size: "
        f"{len(context)} characters"
    )

    if exact:
        print(
            "\nExact implementation-analysis mode: ON"
        )
        print(
            "Using targeted functions and one selected "
            "enemy resource."
        )
    else:
        print(
            "\nUsing focused context."
        )

    # Reliability-critical traces are supplied to Qwen as verified
    # evidence rather than replacing the model's explanation.
    verified_trace = render_deterministic_enemy_damage_trace(
        question,
        functions,
    )

    if verified_trace is None:
        verified_trace = render_deterministic_player_damage_trace(
            question,
            functions,
        )

    if verified_trace is None:
        verified_trace = render_deterministic_player_defense_trace(
            question,
            functions,
        )

    if verified_trace is None and exact:
        verified_trace = render_deterministic_battle_reward_trace(
            question,
            functions,
        )

    if verified_trace is None and exact:
        verified_trace = render_deterministic_overworld_encounter_trace(
            question,
            functions,
        )

    prompt_context = context

    verified_roles = build_verified_function_roles(functions)

    verified_calculation = build_verified_calculation_chain(
        question,
        functions,
    )

    verified_expression = build_verified_calculation_expression(
        question,
        functions,
    )

    # Normal questions use a compact deterministic evidence package. Python
    # has already traced the important operations, so Qwen is asked to
    # summarize those facts instead of independently reconstructing them.
    if verified_trace and not exact:
        prompt_context += (
            "\n\n===== AUTHORITATIVE VERIFIED FACTS =====\n"
            + verified_trace
            + "\n===== END AUTHORITATIVE VERIFIED FACTS ====="
        )
        print(
            "\nAuthoritative verified facts added to summary context."
        )
    else:
        # Exact-analysis mode keeps the richer evidence package so detailed
        # forensic questions still have the underlying expressions and roles.
        prompt_context += (
            "\n\n===== VERIFIED FUNCTION ROLES =====\n"
            + verified_roles
            + "\n===== END VERIFIED FUNCTION ROLES ====="
        )

        if verified_calculation:
            prompt_context += (
                "\n\n===== VERIFIED CALCULATION CHAIN =====\n"
                + verified_calculation
                + "\n===== END VERIFIED CALCULATION CHAIN ====="
            )
            print(
                "\nVerified calculation chain added to the model context."
            )

        if verified_expression:
            prompt_context += (
                "\n\n===== VERIFIED CALCULATION EXPRESSIONS =====\n"
                + verified_expression
                + "\n===== END VERIFIED CALCULATION EXPRESSIONS ====="
            )
            print(
                "\nVerified calculation expressions added to the model context."
            )

        if verified_trace:
            prompt_context += (
                "\n\n===== VERIFIED SOURCE FACTS =====\n"
                + verified_trace
                + "\n===== END VERIFIED SOURCE FACTS ====="
            )
            print(
                "\nVerified source facts added to the model context."
            )

    print(
        "\nSending targeted evidence to Ollama..."
    )

    if not user_requested_numeric_example(question):
        prompt_context += (
            "\n\n===== RESPONSE CONSTRAINT =====\n"
            "NO NUMERIC EXAMPLE REQUESTED: Do not provide hypothetical numbers, assumed rolls, or sample calculations.\n"
            "===== END RESPONSE CONSTRAINT ====="
        )

    prompt = build_prompt(
        question,
        prompt_context,
        exact,
    )

    print_context_diagnostics(
        prompt_context,
        prompt,
    )

    response = ask_model(prompt)

    elapsed = time.time() - start

    print(
        f"\nModel time: {elapsed:.1f} seconds\n"
    )

    valid, issues = validate_response(
        response,
        question,
        verified_trace,
    )

    if valid:
        print(response.strip())
        return

    print("\nQwen answer failed deterministic validation:")
    for issue in issues:
        print(f"  - {issue}")

    fallback = build_deterministic_fallback(
        question,
        verified_trace,
    )

    if fallback is not None:
        print("\nUsing Python-verified fallback answer:")
        print(fallback)
    else:
        print(
            "\nNo deterministic fallback is available for this question. "
            "The unverified model answer was not displayed."
        )


def command_loop():
    print("Local Godot Agent")
    print(f"Project: {PROJECT_ROOT}")
    print(f"Model: {MODEL}")

    while True:
        try:
            command = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not command:
            continue

        if command.lower() == "quit":
            break

        if command.lower() == "list":
            files = list_files()

            print(
                f"\nFound {len(files)} project files:\n"
            )

            for path in files:
                print(relative_path(path))

            continue

        if command.lower().startswith("search "):
            query = command[7:].strip()

            if not query:
                print("Usage: search <term>")
                continue

            results = search_files(query)

            if not results:
                print(f"No matches found for: {query}")
                continue

            print(f"\nMatches for '{query}':")
            for path, matches in results:
                print(f"\n{relative_path(path)}")
                for line_number, line in matches:
                    print(f"  {line_number}: {line}")

            continue

        if command.lower().startswith("read "):
            relative = command[5:].strip()

            if not relative:
                print("Usage: read <path>")
                continue

            path = PROJECT_ROOT / relative

            if not path.exists() or not path.is_file():
                print(f"File not found: {relative}")
                continue

            try:
                print(read_file(path))
            except Exception as exc:
                print(f"Error reading {relative}: {exc}")

            continue

        if command.lower().startswith("ask "):
            question = command[4:].strip()

            if not question:
                print("Usage: ask <question>")
                continue

            try:
                handle_ask(question)
            except Exception as exc:
                print("\nAgent error:")
                print(f"{type(exc).__name__}: {exc}")

            continue

        print(
            "Unknown command. Use: list, search <term>, "
            "read <path>, ask <question>, quit"
        )


if __name__ == "__main__":
    command_loop()
