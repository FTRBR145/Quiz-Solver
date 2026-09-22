import os
import json
from typing import Optional, List
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import models as genai_models

from src.models import ExtractionAndAnswerOutput, ProcessedQuestion, QuestionItem, AnswerResult, OptionItem

# Nonaktifkan warning AFC internal SDK
genai_models.Models._logged_afc_warning = True

load_dotenv()


class GeminiSolver:
    """Kelas untuk mengekstrak dan memecahkan soal kuis menggunakan Gemini AI dengan multi-model fallback."""

    # Urutan model cadangan jika salah satu model mengalami 503 high demand / rate limit
    FALLBACK_MODELS = [
        "gemini-3.5-flash-lite",  # Sangat cepat, stabil, tahan lonjakan traffic
        "gemini-3.8-flash",       # Model cerdas mutakhir
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite"
    ]

    def __init__(self, api_key: Optional[str] = None, allow_demo: bool = False):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.is_demo = False
        if not self.api_key or self.api_key.strip() == "" or "your_gemini_api_key_here" in self.api_key:
            if allow_demo:
                self.is_demo = True
            else:
                raise ValueError(
                    "GEMINI_API_KEY belum disetel!\n"
                    "Silakan buka file .env dan isi GEMINI_API_KEY Anda.\n"
                    "Dapatkan API key gratis di: https://aistudio.google.com/"
                )
        if not self.is_demo:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = self.FALLBACK_MODELS[0]

    def solve_question_content(self, raw_content: str, question_hint_number: Optional[int] = None) -> ProcessedQuestion:
        """
        Menerima teks mentah atau HTML potongan soal yang sedang aktif pada layar,
        kemudian mengekstrak pertanyaan, opsi, dan menentukan jawaban yang benar beserta penjelasannya.
        Otomatis berpindah model cadangan jika model utama mengalami 503 (high demand).
        """
        if self.is_demo:
            # Mode demo tanpa API key untuk uji coba browser
            lines = [l.strip() for l in raw_content.splitlines() if l.strip()]
            q_text = lines[0] if lines else "Pertanyaan Uji Coba Demo"
            opts = []
            for line in lines[1:]:
                if any(line.startswith(prefix) for prefix in ["A.", "B.", "C.", "D.", "a.", "b.", "c.", "d."]):
                    lbl = line[0].upper()
                    txt = line[2:].strip()
                    opts.append(OptionItem(label=lbl, text=txt))

            best_opt = "B" if len(opts) > 1 else (opts[0].label if opts else None)
            ans_text = "Opsi terpilih (Simulasi Demo)"
            if best_opt:
                for opt in opts:
                    if opt.label == best_opt:
                        ans_text = opt.text

            return ProcessedQuestion(
                question=QuestionItem(
                    number=question_hint_number or 1,
                    question_text=q_text,
                    options=opts,
                    question_type="multiple_choice" if opts else "essay"
                ),
                result=AnswerResult(
                    best_option=best_opt,
                    answer_text=ans_text,
                    explanation="Ini adalah jawaban simulasi demo. Masukkan GEMINI_API_KEY di file .env untuk analisis AI Gemini secara real.",
                    confidence=0.99
                )
            )

        system_instruction = (
            "Anda adalah asisten cerdas ahli pemecah soal ujian dan kuis akademis/profesional. "
            "Tugas Anda adalah membaca potongan teks atau HTML soal berikut ini, lalu:\n"
            "1. Ekstrak nomor soal (jika tertera), teks pertanyaan lengkap yang bersih, dan semua opsi jawaban (jika pilihan ganda).\n"
            "2. Tentukan kunci jawaban yang paling tepat dan akurat.\n"
            "3. Berikan pembahasan atau penjelasan singkat, padat, dan meyakinkan mengapa jawaban tersebut benar.\n"
            "4. Berikan tingkat keyakinan (confidence score 0.0 - 1.0).\n"
            "Gunakan bahasa Indonesia yang jelas dan formal."
        )

        prompt = (
            f"Berikut adalah teks/elemen halaman soal aktif yang sedang ditampilkan:\n"
            f"'''\n{raw_content}\n'''\n\n"
        )
        if question_hint_number:
            prompt += f"Petunjuk nomor urut soal di sistem saat ini: Soal ke-{question_hint_number}.\n"

        prompt += "Analisis soal tersebut dan hasilkan format JSON sesuai skema yang diminta."

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=ExtractionAndAnswerOutput,
            temperature=0.2,
        )

        response = None
        last_error = None

        # Coba model dari daftar fallback
        for model_to_try in self.FALLBACK_MODELS:
            try:
                response = self.client.models.generate_content(
                    model=model_to_try,
                    contents=prompt,
                    config=config
                )
                self.model_name = model_to_try
                break
            except Exception as e:
                err_str = str(e)
                last_error = e
                # Jika 503 high demand atau 429 rate limit, coba model berikutnya
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    continue
                else:
                    raise e

        if not response:
            raise RuntimeError(f"Semua model Gemini sedang sibuk atau mengalami kendala: {last_error}")

        try:
            parsed_data = ExtractionAndAnswerOutput.model_validate_json(response.text)
        except Exception:
            data_dict = json.loads(response.text)
            parsed_data = ExtractionAndAnswerOutput.model_validate(data_dict)

        q_number = parsed_data.number or question_hint_number

        question_item = QuestionItem(
            number=q_number,
            question_text=parsed_data.question_text,
            options=parsed_data.options,
            question_type=parsed_data.question_type or "multiple_choice"
        )

        answer_result = AnswerResult(
            best_option=parsed_data.best_option,
            answer_text=parsed_data.answer_text,
            explanation=parsed_data.explanation,
            confidence=parsed_data.confidence
        )

        return ProcessedQuestion(
            question=question_item,
            result=answer_result
        )

