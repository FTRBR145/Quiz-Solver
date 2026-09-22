import json
import datetime
from pathlib import Path
from typing import List
from src.models import ProcessedQuestion


class Exporter:
    """Modul untuk mengekspor hasil kuis ke berbagai format file."""

    @staticmethod
    def save_to_markdown(questions: List[ProcessedQuestion], filepath: str, title: str = "Hasil Rekap Soal & Kunci Jawaban") -> str:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md_lines = [
            f"# {title}",
            f"\n*Dibuat pada: {now_str}*",
            f"*Total Soal Terjawab: {len(questions)}*",
            "\n---\n"
        ]

        for idx, item in enumerate(questions, 1):
            q_num = item.question.number if item.question.number is not None else idx
            md_lines.append(f"## Soal No. {q_num}")
            md_lines.append(f"\n**Pertanyaan:**\n{item.question.question_text}\n")

            if item.question.options:
                md_lines.append("**Pilihan Jawaban:**")
                for opt in item.question.options:
                    is_key = False
                    if item.result.best_option and (
                        opt.label.strip().lower() == item.result.best_option.strip().lower()
                    ):
                        is_key = True

                    badge = "✅ **[KUNCI JAWABAN]** " if is_key else "- "
                    md_lines.append(f"{badge}{opt.label}. {opt.text}")
                md_lines.append("")

            md_lines.append(f"> **Kunci Jawaban:** {item.result.best_option or ''} {item.result.answer_text}")
            md_lines.append(f">\n> **Pembahasan:**\n> {item.result.explanation}")
            md_lines.append(f">\n> **Keyakinan AI:** {int(item.result.confidence * 100)}%")
            md_lines.append("\n---\n")

        content = "\n".join(md_lines)
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())

    @staticmethod
    def save_to_json(questions: List[ProcessedQuestion], filepath: str) -> str:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = [item.model_dump() for item in questions]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path.resolve())

