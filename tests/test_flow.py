import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import QuestionItem, OptionItem, AnswerResult, ProcessedQuestion
from src.browser_agent import BrowserAgent
from src.exporter import Exporter


def test_browser_step_by_step():
    print("[1] Menguji BrowserAgent pada mock kuis bertahap...")
    mock_file = Path(__file__).resolve().parent / "mock_quiz.html"
    file_url = mock_file.as_uri()

    agent = BrowserAgent(user_data_dir=str(Path("./test_profile").resolve()))
    try:
        # Jalankan headless untuk automated test
        agent.start(headless=True, initial_url=file_url)

        # Cek Soal 1
        content1 = agent.get_current_question_content()
        assert "fotosintesis" in content1.lower(), f"Gagal mengekstrak soal 1: {content1}"
        assert "kloroplas" in content1.lower(), "Opsi soal 1 tidak terdeteksi"
        print("    [OK] Ekstraksi Soal 1 Berhasil!")

        # Klik Berikutnya -> Soal 2
        clicked = agent.click_next()
        assert clicked, "Gagal mengklik tombol Berikutnya pada Soal 1"

        content2 = agent.get_current_question_content()
        assert "nusantara" in content2.lower() or "ibu kota" in content2.lower(), f"Gagal masuk soal 2: {content2}"
        print("    [OK] Navigasi ke Soal 2 Berhasil!")

        # Klik Berikutnya -> Soal 3
        clicked2 = agent.click_next()
        assert clicked2, "Gagal mengklik tombol Berikutnya pada Soal 2"

        content3 = agent.get_current_question_content()
        assert "(15 * 4)" in content3, f"Gagal masuk soal 3: {content3}"
        print("    [OK] Navigasi ke Soal 3 Berhasil!")

        # Lanjutkan sampai soal terakhir dari total 60 soal
        for question_number in range(4, 61):
            clicked_next = agent.click_next()
            assert clicked_next, f"Gagal berpindah ke soal {question_number}"

        final_content = agent.get_current_question_content()
        assert "Soal No. 60 dari 60" in final_content, "Soal terakhir bukan nomor 60"

        # Cek tombol Selesai / Finish pada soal terakhir
        has_finish = agent.is_finish_available()
        assert has_finish, "Tombol Selesai Ujian tidak terdeteksi pada nomor terakhir"
        print("    [OK] Deteksi Tombol Selesai Ujian Berhasil!")

    finally:
        agent.close()


def test_exporter():
    print("\n[2] Menguji Exporter (Markdown & JSON)...")
    sample_pq = ProcessedQuestion(
        question=QuestionItem(
            number=1,
            question_text="Organel sel manakah yang berfungsi sebagai tempat fotosintesis?",
            options=[
                OptionItem(label="A", text="Mitokondria"),
                OptionItem(label="B", text="Kloroplas"),
                OptionItem(label="C", text="Ribosom"),
                OptionItem(label="D", text="Badan Golgi"),
            ],
            question_type="multiple_choice"
        ),
        result=AnswerResult(
            best_option="B",
            answer_text="Kloroplas",
            explanation="Kloroplas mengandung klorofil yang menyerap energi cahaya untuk reaksi fotosintesis.",
            confidence=0.99
        )
    )

    md_path = Exporter.save_to_markdown([sample_pq], "test_output/hasil_test.md")
    json_path = Exporter.save_to_json([sample_pq], "test_output/hasil_test.json")

    assert Path(md_path).exists(), "File MD tidak terbuat"
    assert Path(json_path).exists(), "File JSON tidak terbuat"

    md_text = Path(md_path).read_text(encoding="utf-8")
    assert "Kloroplas" in md_text
    assert "[KUNCI JAWABAN]" in md_text
    print("    [OK] Ekspor Markdown dan JSON Berhasil!")


if __name__ == "__main__":
    test_browser_step_by_step()
    test_exporter()
    print("\n[SUKSES] SEMUA PENGUJIAN OTOMATIS BERHASIL DILALUI DENGAN BAIK!")

