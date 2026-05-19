#!/usr/bin/env python3
"""Extrae preguntas de los PDFs y genera data/questions.json."""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ETICA_TXT = ROOT / "etica_extracted.txt"
RESUMEN_TXT = ROOT / "Resumen de Todos los Test_extracted.txt"
OUT = ROOT / "data" / "questions.json"

TEMA_NAMES = {
    1: "Ética, deontología e informática jurídica",
    2: "Protección de datos (RGPD/LOPDGDD)",
    3: "Propiedad intelectual y software",
    4: "Delitos informáticos y derecho penal",
    5: "Contratación electrónica y comercio digital",
    6: "Derecho del consumidor y responsabilidad",
    7: "Contratos y formación contractual",
    8: "Prueba electrónica y pagos digitales",
}

OPTION_RE = re.compile(r"^([a-d])\.\s*(.+)$", re.IGNORECASE)
QUESTION_RE = re.compile(r"^(\d+)\.\s*(.+)$")
ANSWER_PAIR_RE = re.compile(r"(\d+)\.\s*([A-Da-d])")
TEST_RE = re.compile(r"^TEST\s+(\d+)\s*$", re.MULTILINE)
TABLA_RE = re.compile(
    r"TABLA(?:\s+DE\s+RESPUESTAS|\s+RESULTADOS|\s+DE\s+RESULTADOS)?(?:\s+TEMA\s+(\d+))?",
    re.IGNORECASE,
)
EXPL_RE = re.compile(
    r"La\s+respuesta\s+correcta\s+es\s+la\s+([A-Da-d])\s*,\s*(.+?)(?=La\s+respuesta\s+correcta|Preguntas\s+Test|\d+\.-|\Z)",
    re.IGNORECASE | re.DOTALL,
)
TEMA_BLOCK_RE = re.compile(
    r"Preguntas\s+Test\s+TEMA\s+(\d+)\.|Preguntas\s+TEST\s+Tema\s+(\d+)\.|Preguntas\s+Test\s+Tema\s+(\d+)\.",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_answer_table(block: str) -> dict[int, str]:
    answers: dict[int, str] = {}
    for num, letter in ANSWER_PAIR_RE.findall(block):
        answers[int(num)] = letter.upper()
    return answers


def parse_questions_block(block: str) -> list[dict]:
    questions: list[dict] = []
    current_num = None
    current_q: list[str] = []
    current_opts: dict[str, str] = {}

    def flush():
        nonlocal current_num, current_q, current_opts
        if current_num is None:
            return
        qtext = normalize(" ".join(current_q))
        if qtext and len(current_opts) >= 2:
            questions.append(
                {
                    "number": current_num,
                    "question": qtext,
                    "options": [
                        {"key": k, "text": normalize(v)}
                        for k, v in sorted(current_opts.items())
                    ],
                }
            )
        current_num = None
        current_q = []
        current_opts = {}

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("===") or "Ética y Derecho" in line:
            continue
        if re.match(r"^\d+$", line):
            continue

        mq = QUESTION_RE.match(line)
        if mq:
            flush()
            current_num = int(mq.group(1))
            rest = mq.group(2).strip()
            current_q = [rest] if rest else []
            continue

        mo = OPTION_RE.match(line)
        if mo and current_num is not None:
            key = mo.group(1).lower()
            current_opts[key] = mo.group(2).strip()
            continue

        if current_num is not None and not current_opts:
            current_q.append(line)
        elif current_num is not None and current_opts:
            last_key = max(current_opts.keys())
            current_opts[last_key] += " " + line

    flush()
    return questions


def parse_etica_tests(text: str) -> dict[int, list[dict]]:
    by_tema: dict[int, list[dict]] = {}
    test_positions = [(m.start(), int(m.group(1))) for m in TEST_RE.finditer(text)]
    tabla_positions = [(m.start(), m.group(0), m.group(1)) for m in TABLA_RE.finditer(text)]

    for i, (start, test_num) in enumerate(test_positions):
        end = test_positions[i + 1][0] if i + 1 < len(test_positions) else len(text)
        chunk = text[start:end]

        tabla_match = None
        for tpos, tlabel, tema_from_tabla in tabla_positions:
            if start < tpos < end:
                tabla_match = (tpos - start, tlabel, tema_from_tabla)
                break

        if tabla_match:
            qpart = chunk[: tabla_match[0]]
            apart = chunk[tabla_match[0] :]
        else:
            qpart, apart = chunk, ""

        tema = int(tabla_match[2]) if tabla_match and tabla_match[2] else test_num
        answers = parse_answer_table(apart)
        questions = parse_questions_block(qpart)

        for q in questions:
            num = q["number"]
            letter = answers.get(num)
            if letter:
                q["correct"] = letter.lower()
            else:
                q["correct"] = None

        by_tema[tema] = questions

    return by_tema


def parse_resumen_explanations(text: str) -> dict[tuple[int, int], dict]:
    """Map (tema, question_number) -> {correct, explanation} from resumen PDF."""
    result: dict[tuple[int, int], dict] = {}
    tema_splits = list(TEMA_BLOCK_RE.finditer(text))
    blocks: list[tuple[int, str]] = []

    for i, m in enumerate(tema_splits):
        tema = int(next(g for g in m.groups() if g))
        start = m.end()
        end = tema_splits[i + 1].start() if i + 1 < len(tema_splits) else len(text)
        blocks.append((tema, text[start:end]))

    q_pattern = re.compile(
        r"(\d+)\.-\s*(.+?)\s+Seleccione\s+una:\s*(.+?)(?=\d+\.-|La\s+respuesta\s+correcta|Preguntas\s+Test|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    opt_pattern = re.compile(r"([a-d])\.\s*([^a-d\.]+?)(?=\s+[a-d]\.|\s+La\s+respuesta|$)", re.IGNORECASE)

    for tema, block in blocks:
        for expl in EXPL_RE.finditer(block):
            letter = expl.group(1).lower()
            explanation = normalize(expl.group(2))
            before = block[: expl.start()]
            nums = re.findall(r"(\d+)\.-", before)
            if nums:
                qnum = int(nums[-1])
                result[(tema, qnum)] = {
                    "correct": letter,
                    "explanation": explanation,
                }

        for m in q_pattern.finditer(block):
            qnum = int(m.group(1))
            body = m.group(3)
            inline = re.search(
                r"La\s+respuesta\s+correcta\s+es\s+la\s+([A-Da-d])\s*,\s*(.+)$",
                body,
                re.IGNORECASE | re.DOTALL,
            )
            if inline:
                key = (tema, qnum)
                if key not in result:
                    result[key] = {
                        "correct": inline.group(1).lower(),
                        "explanation": normalize(inline.group(2)),
                    }

    return result


def build_explanation(q: dict) -> str:
    correct = q.get("correct")
    if not correct:
        return "Consulta el material del tema para repasar esta pregunta."
    opt = next((o for o in q["options"] if o["key"] == correct), None)
    if opt:
        return f"La respuesta correcta es la {correct.upper()}: {opt['text']}"
    return f"La respuesta correcta es la {correct.upper()}."


def _option_texts(options: list[dict]) -> list[str]:
    return [normalize(o.get("text", "")) for o in options if o.get("text")]


def _word_overlap(question: str, tail: str) -> float:
    stop = {
        "que", "los", "las", "una", "como", "para", "con", "del", "al",
        "por", "sin", "sobre", "entre", "desde", "hasta", "esta", "este",
        "estas", "estos", "más", "menos", "todo", "toda", "todos", "todas",
        "ser", "son", "sido", "han", "hay", "debe", "deben", "cual", "cuando",
    }
    words_tail = {
        w
        for w in re.findall(r"[a-záéíóúñü]{4,}", tail.lower())
        if w not in stop
    }
    words_q = {
        w
        for w in re.findall(r"[a-záéíóúñü]{4,}", question.lower())
        if w not in stop
    }
    if not words_tail:
        return 1.0
    inter = len(words_q & words_tail)
    return inter / len(words_tail)


def build_hint(
    explanation: str,
    tema_name: str,
    question: str,
    options: list[dict],
    correct: str,
) -> str:
    """Teoría orientativa sin revelar la letra de la opción correcta."""

    expl = normalize(explanation)
    correct_opt = next((o["text"] for o in options if o.get("key") == correct), "")
    norm_correct = normalize(correct_opt).lower() if correct_opt else ""

    tail = re.sub(
        r"(?i)^La\s+respuesta\s+correcta\s+es\s+la\s+[a-d]\s*[,:.\-–]\s*",
        "",
        expl,
    ).strip()
    tail = re.sub(r"(?i)^Respuesta\s+correcta\s*[,:.\-–]?\s*[a-d]?\s*[,:.\-–]?\s*", "", tail).strip()

    def fallback() -> str:
        qshort = normalize(question)
        if len(qshort) > 220:
            qshort = qshort[:217] + "…"
        return (
            f"Estás en «{tema_name}». Repasa la pregunta: «{qshort}» "
            "Identifica qué pide exactamente (definición, sujeto obligado, principio, plazo, tipo de dato, "
            "requisito formal, etc.) y contrasta cada opción con el vocabulario y criterios habituales del temario. "
            "Descarta respuestas que mezclen materias, confundan órganos o contradigan el marco general de la materia."
        )

    if not tail or len(tail) < 28:
        return fallback()

    low = tail.lower()
    if norm_correct and (low == norm_correct or norm_correct == low):
        return fallback()
    if norm_correct and len(norm_correct) > 15:
        if low.startswith(norm_correct[: min(24, len(norm_correct))]):
            return fallback()
        if norm_correct.startswith(low[: min(24, len(low))]) and len(tail) < 80:
            return fallback()

    for ot in _option_texts(options):
        olow = ot.lower()
        if len(olow) < 12:
            continue
        if low == olow or (len(tail) < 100 and olow in low and low in olow):
            return fallback()

    tail_compact = re.sub(r"\s+", "", low)
    for o in options:
        ot = normalize(o.get("text", ""))
        if len(ot) < 18:
            continue
        o_compact = re.sub(r"\s+", "", ot.lower())
        if len(o_compact) < 18:
            continue
        if o_compact in tail_compact or tail_compact in o_compact:
            return fallback()
        if len(tail_compact) > 35 and len(o_compact) > 35:
            if SequenceMatcher(None, tail_compact, o_compact).ratio() > 0.82:
                return fallback()

    if len(tail) > 90 and _word_overlap(question, tail) < 0.14:
        return fallback()

    if norm_correct and len(norm_correct) > 35:
        cc = re.sub(r"\s+", "", norm_correct)
        if len(cc) > 35 and SequenceMatcher(None, tail_compact, cc).ratio() > 0.82:
            return fallback()

    return tail


def main():
    etica_text = ETICA_TXT.read_text(encoding="utf-8")
    resumen_text = RESUMEN_TXT.read_text(encoding="utf-8")

    by_tema = parse_etica_tests(etica_text)
    explanations = parse_resumen_explanations(resumen_text)

    questions_out = []
    qid = 1

    for tema in sorted(by_tema.keys()):
        for q in by_tema[tema]:
            num = q["number"]
            expl_data = explanations.get((tema, num))
            explanation = (
                expl_data["explanation"]
                if expl_data and expl_data.get("explanation")
                else build_explanation(q)
            )
            if expl_data and expl_data.get("correct") and not q.get("correct"):
                q["correct"] = expl_data["correct"]

            if not q.get("correct"):
                continue

            hint = build_hint(
                explanation,
                TEMA_NAMES.get(tema, f"Tema {tema}"),
                q["question"],
                q["options"],
                q["correct"],
            )

            questions_out.append(
                {
                    "id": qid,
                    "tema": tema,
                    "temaName": TEMA_NAMES.get(tema, f"Tema {tema}"),
                    "number": num,
                    "question": q["question"],
                    "options": q["options"],
                    "correct": q["correct"],
                    "explanation": explanation,
                    "hint": hint,
                }
            )
            qid += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "title": "Ética y Derecho Informático",
        "examSize": 60,
        "totalQuestions": len(questions_out),
        "temas": [
            {"id": t, "name": TEMA_NAMES.get(t, f"Tema {t}"), "count": sum(1 for q in questions_out if q["tema"] == t)}
            for t in sorted(set(q["tema"] for q in questions_out))
        ],
    }
    payload = {"meta": meta, "questions": questions_out}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generadas {len(questions_out)} preguntas en {OUT}")
    for t in meta["temas"]:
        print(f"  Tema {t['id']}: {t['count']} preguntas — {t['name']}")


if __name__ == "__main__":
    main()
