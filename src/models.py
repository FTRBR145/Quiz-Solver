from typing import List, Optional
from pydantic import BaseModel, Field


class OptionItem(BaseModel):
    """Pilihan jawaban pada soal pilihan ganda."""
    label: str = Field(description="Label opsi seperti A, B, C, D atau 1, 2, 3")
    text: str = Field(description="Teks isi pilihan jawaban")


class QuestionItem(BaseModel):
    """Representasi satu soal yang diekstrak dari halaman."""
    number: Optional[int] = Field(default=None, description="Nomor urut soal jika terdeteksi")
    question_text: str = Field(description="Teks lengkap pertanyaan atau petunjuk soal")
    options: List[OptionItem] = Field(default_factory=list, description="Daftar opsi pilihan jawaban (jika pilihan ganda)")
    question_type: str = Field(
        default="multiple_choice",
        description="Tipe soal: multiple_choice, essay, true_false, atau fill_blank"
    )


class AnswerResult(BaseModel):
    """Hasil analisis dan jawaban dari AI."""
    best_option: Optional[str] = Field(
        default=None,
        description="Label opsi terbaik (misal: 'A' atau 'B') jika pilihan ganda"
    )
    answer_text: str = Field(description="Jawaban ringkas atau teks jawaban yang benar")
    explanation: str = Field(description="Penjelasan atau pembahasan mengapa jawaban ini benar")
    confidence: float = Field(default=0.95, description="Skor keyakinan (0.0 sampai 1.0)")


class ProcessedQuestion(BaseModel):
    """Gabungan data soal dan hasil analisis jawaban."""
    question: QuestionItem
    result: AnswerResult
    timestamp: Optional[str] = None


class ExtractionAndAnswerOutput(BaseModel):
    """Skema respon dari Gemini untuk ekstraksi sekaligus penjawab."""
    number: Optional[int] = Field(default=None, description="Nomor urut soal jika ada")
    question_text: str = Field(description="Teks pertanyaan utama yang bersih")
    options: List[OptionItem] = Field(default_factory=list, description="Opsi jawaban A, B, C, D")
    question_type: str = Field(default="multiple_choice", description="Tipe pertanyaan")
    best_option: Optional[str] = Field(default=None, description="Label pilihan jawaban terbaik jika pilihan ganda")
    answer_text: str = Field(description="Teks jawaban yang benar")
    explanation: str = Field(description="Pembahasan logis dan akurat")
    confidence: float = Field(default=0.95, description="Tingkat keyakinan (0.0 - 1.0)")

