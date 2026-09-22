import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

from src.models import ProcessedQuestion
from src.gemini_solver import GeminiSolver
from src.browser_agent import BrowserAgent
from src.exporter import Exporter

console = Console()


def show_banner():
    console.print(
        Panel.fit(
            "[bold cyan]AUTO QUIZ EXTRACTOR & SOLVER[/bold cyan]\n"
            "[yellow]Ekstraksi Soal Bertahap (1 per 1) & Penjawab Otomatis AI (Gemini 3.8 Flash)[/yellow]",
            border_style="cyan"
        )
    )


def display_processed_question(pq: ProcessedQuestion):
    """Menampilkan pertanyaan, pilihan, dan kunci jawaban dengan format kartu yang rapi."""
    q = pq.question
    res = pq.result

    q_title = f"[bold green]Soal #{q.number or '?'}[/bold green]"
    content = f"[bold white]{q.question_text}[/bold white]\n\n"

    if q.options:
        content += "[bold]Pilihan Jawaban:[/bold]\n"
        for opt in q.options:
            is_best = res.best_option and (opt.label.strip().upper() == res.best_option.strip().upper())
            if is_best:
                content += f"  [bold green]✅ {opt.label}. {opt.text}  <-- KUNCI[/bold green]\n"
            else:
                content += f"  [dim]- {opt.label}. {opt.text}[/dim]\n"
        content += "\n"

    best_label = f"({res.best_option}) " if res.best_option else ""
    content += f"[bold yellow]💡 Rekomendasi Jawaban:[/bold yellow] [bold]{best_label}{res.answer_text}[/bold]\n"
    content += f"[bold cyan]📖 Pembahasan:[/bold cyan]\n{res.explanation}\n"
    content += f"[dim]Keyakinan AI: {int(res.confidence * 100)}%[/dim]"

    console.print(Panel(content, title=q_title, border_style="green", expand=False))


def run_browser_session(solver: GeminiSolver):
    """Menjalankan sesi ekstraksi kuis bertahap melalui browser Playwright."""
    console.print("\n[bold]1. Konfigurasi Browser[/bold]")
    url_input = Prompt.ask(
        "[cyan]Masukkan URL website kuis[/cyan] (kosongkan jika ingin membuka browser manual)"
    ).strip()

    initial_url = url_input if url_input else None

    console.print("\n[bold]2. Pilih Mode Operasi:[/bold]")
    console.print("  [1] [green]Mode Semi-Otomatis (Direkomendasikan)[/green]: Anda dapat melihat jawaban di terminal, lalu tekan [Enter] untuk klik Next.")
    console.print("  [2] [yellow]Mode Otomatis Penuh[/yellow]: Program otomatis memilih jawaban dan klik tombol Next.")
    mode_choice = Prompt.ask("Pilih mode", choices=["1", "2"], default="1")
    is_auto = (mode_choice == "2")

    auto_delay = 2.5
    if is_auto:
        delay_str = Prompt.ask("Jeda waktu antar soal (detik)", default="2.5")
        try:
            auto_delay = float(delay_str)
        except ValueError:
            auto_delay = 2.5

    browser = BrowserAgent()
    try:
        with console.status("[bold green]Membuka browser...[/bold green]"):
            browser.start(headless=False, initial_url=initial_url)

        console.print("\n[bold green]✓ Browser berhasil dibuka![/bold green]")
        console.print("[dim]Tips: Silakan login atau navigasikan ke halaman kuis jika belum dimulai.[/dim]")
        Prompt.ask("\n[bold magenta]Tekan [ENTER] di sini jika Anda SUDAH BERADA di halaman Soal #1 untuk mulai mengekstrak[/bold magenta]")

        session_questions: List[ProcessedQuestion] = []
        question_counter = 1

        while True:
            console.print(f"\n[bold cyan]─── Memproses Soal #{question_counter} ───[/bold cyan]")
            
            with console.status("[bold yellow]Membaca teks soal dari browser...[/bold yellow]"):
                content = browser.get_current_question_content()

            if not content or len(content.strip()) < 10:
                console.print("[yellow]⚠️ Konten soal kosong atau belum termuat sempurna.[/yellow]")
                retry = Confirm.ask("Coba baca ulang halaman saat ini?", default=True)
                if retry:
                    continue
                else:
                    break

            with console.status("[bold yellow]Menganalisis soal & mencari jawaban via Gemini 3.8 Flash...[/bold yellow]"):
                try:
                    pq = solver.solve_question_content(content, question_hint_number=question_counter)
                except Exception as e:
                    console.print(f"[bold red]Gagal menganalisis via AI: {e}[/bold red]")
                    action = Prompt.ask("Pilihan: (r) Coba lagi, (s) Lewati nomor ini, (q) Selesai kuis", choices=["r", "s", "q"], default="r")
                    if action == "r":
                        continue
                    elif action == "s":
                        browser.click_next()
                        question_counter += 1
                        continue
                    else:
                        break

            # Tampilkan hasil di terminal
            display_processed_question(pq)
            session_questions.append(pq)

            # Cek apakah sudah selesai
            has_finish = browser.is_finish_available()
            if has_finish:
                console.print("[bold green]🏁 Terdeteksi tombol Selesai/Submit pada halaman kuis![/bold green]")

            # Jika mode otomatis:
            if is_auto:
                if pq.result.best_option:
                    browser.select_option(pq.result.best_option, pq.result.answer_text)
                
                time.sleep(auto_delay)

                clicked = browser.click_next()
                if not clicked:
                    console.print("[yellow]Tidak menemukan tombol 'Next' lagi. Kemungkinan soal sudah habis.[/yellow]")
                    break
                question_counter += 1
            else:
                # Mode Semi-Otomatis
                cmd = Prompt.ask(
                    "\n[bold]Navigasi:[/bold] [green][ENTER] = Klik Next & proses soal berikutnya[/green] | [yellow]'s' = Lewati klik Next[/yellow] | [red]'q' = Selesai[/red]",
                    default=""
                ).strip().lower()

                if cmd == 'q':
                    console.print("[yellow]Menghentikan sesi ekstraksi atas permintaan pengguna.[/yellow]")
                    break
                elif cmd == 's':
                    console.print("[dim]Melewati auto-click Next (silakan navigasi manual di browser).[/dim]")
                    question_counter += 1
                else:
                    with console.status("[dim]Mengklik tombol Next...[/dim]"):
                        clicked = browser.click_next()
                    if not clicked:
                        console.print("[yellow]Tombol 'Next' otomatis tidak ditemukan di halaman.[/yellow]")
                        console.print("[dim]Silakan klik tombol berikutnya di browser secara manual, lalu tekan ENTER.[/dim]")
                        Prompt.ask("Tekan [ENTER] jika halaman soal berikutnya sudah tampil...")
                    question_counter += 1

        # Kuis Selesai: Ekspor
        if session_questions:
            console.print(f"\n[bold green]🎉 Selesai! Berhasil merekap {len(session_questions)} soal.[/bold green]")
            md_file = Exporter.save_to_markdown(session_questions, "hasil_kuis.md")
            json_file = Exporter.save_to_json(session_questions, "hasil_kuis.json")

            console.print(f"📄 Rekap tersimpan di: [bold cyan]{md_file}[/bold cyan]")
            console.print(f"📊 Data JSON tersimpan di: [bold cyan]{json_file}[/bold cyan]")
        else:
            console.print("[yellow]Tidak ada soal yang tersimpan dalam sesi ini.[/yellow]")

    finally:
        keep_browser = Confirm.ask("Tutup browser Playwright sekarang?", default=True)
        if keep_browser:
            browser.close()


def run_manual_paste_session(solver: GeminiSolver):
    """Mode manual: Tempel teks atau cuplikan HTML soal langsung di terminal."""
    console.print("\n[bold]Mode Tempel Teks / Manual Paste[/bold]")
    console.print("Tempel teks soal atau pilihan jawaban di bawah ini.")
    console.print("[dim](Ketik baris kosong lalu tekan Ctrl+Z / Enter untuk selesai menginput)[/dim]\n")

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    raw_text = "\n".join(lines).strip()
    if not raw_text:
        console.print("[yellow]Teks kosong.[/yellow]")
        return

    with console.status("[bold yellow]Menganalisis soal via Gemini...[/bold yellow]"):
        pq = solver.solve_question_content(raw_text)

    display_processed_question(pq)

    save = Confirm.ask("Simpan ke file Markdown?", default=True)
    if save:
        Exporter.save_to_markdown([pq], "soal_terpilih.md")
        console.print("Tersimpan di [bold cyan]soal_terpilih.md[/bold cyan]")


def run_simulation(solver: GeminiSolver):
    """Menjalankan simulasi kuis bertahap menggunakan file mock_quiz.html lokal."""
    mock_file = Path(__file__).resolve().parent / "tests" / "mock_quiz.html"
    file_url = mock_file.as_uri()

    console.print(Panel(
        f"[bold green]Memulai Simulasi Kuis Bertahap[/bold green]\n"
        f"File simulasi: [cyan]{mock_file}[/cyan]\n"
        f"Kuis simulasi ini berisi 60 soal pilihan ganda dengan tombol 'Berikutnya' dan tombol 'Selesai'.",
        border_style="green"
    ))

    console.print("\n[bold]Pilih Mode Operasi Simulasi:[/bold]")
    console.print("  [1] [green]Mode Semi-Otomatis[/green]: Lihat jawaban di terminal, lalu tekan [Enter] untuk klik Next.")
    console.print("  [2] [yellow]Mode Otomatis Penuh[/yellow]: Program otomatis memilih jawaban dan klik Next.")
    mode_choice = Prompt.ask("Pilih mode", choices=["1", "2"], default="1")
    is_auto = (mode_choice == "2")

    browser = BrowserAgent()
    try:
        with console.status("[bold green]Membuka browser simulasi...[/bold green]"):
            browser.start(headless=False, initial_url=file_url)

        session_questions: List[ProcessedQuestion] = []
        question_counter = 1

        while True:
            console.print(f"\n[bold cyan]─── Memproses Soal #{question_counter} ───[/bold cyan]")
            time.sleep(0.5)
            content = browser.get_current_question_content()

            with console.status("[bold yellow]Menganalisis soal & mencari kunci jawaban...[/bold yellow]"):
                try:
                    pq = solver.solve_question_content(content, question_hint_number=question_counter)
                except Exception as e:
                    console.print(f"[bold red]Gagal menganalisis via AI: {e}[/bold red]")
                    action = Prompt.ask("Pilihan: (r) Coba lagi, (s) Lewati nomor ini, (q) Selesai", choices=["r", "s", "q"], default="r")
                    if action == "r":
                        continue
                    elif action == "s":
                        browser.click_next()
                        question_counter += 1
                        continue
                    else:
                        break

            display_processed_question(pq)
            session_questions.append(pq)

            has_finish = browser.is_finish_available()
            if has_finish:
                console.print("[bold green]🏁 Terdeteksi tombol 'Selesai Ujian' pada halaman kuis![/bold green]")

            if is_auto:
                if pq.result.best_option:
                    browser.select_option(pq.result.best_option, pq.result.answer_text)
                time.sleep(2.0)
                clicked = browser.click_next()
                if not clicked:
                    console.print("[yellow]Semua soal simulasi telah selesai diproses.[/yellow]")
                    break
                question_counter += 1
            else:
                cmd = Prompt.ask(
                    "\n[bold]Navigasi:[/bold] [green][ENTER] = Klik Next ke nomor berikutnya[/green] | [red]'q' = Selesai[/red]",
                    default=""
                ).strip().lower()

                if cmd == 'q':
                    break

                with console.status("[dim]Mengklik tombol Berikutnya...[/dim]"):
                    clicked = browser.click_next()
                if not clicked:
                    console.print("[green]Tidak ada tombol 'Berikutnya' lagi. Simulasi selesai![/green]")
                    break
                question_counter += 1

        if session_questions:
            console.print(f"\n[bold green]🎉 Simulasi selesai! {len(session_questions)} soal terekap.[/bold green]")
            md_file = Exporter.save_to_markdown(session_questions, "hasil_simulasi.md", title="Hasil Simulasi Ujian Bertahap")
            json_file = Exporter.save_to_json(session_questions, "hasil_simulasi.json")
            console.print(f"📄 Rekap tersimpan di: [bold cyan]{md_file}[/bold cyan]")
            console.print(f"📊 Data JSON tersimpan di: [bold cyan]{json_file}[/bold cyan]")

    finally:
        browser.close()


def get_or_setup_solver() -> GeminiSolver:
    """Menginisialisasi solver dengan opsi input API key atau mode demo jika belum ada."""
    try:
        return GeminiSolver()
    except ValueError:
        console.print(Panel(
            "[bold yellow]⚠️ GEMINI_API_KEY belum ditemukan di file .env![/bold yellow]\n\n"
            "Dapatkan API Key gratis di: [cyan]https://aistudio.google.com/[/cyan]\n"
            "Anda dapat memasukkan API Key sekarang (akan otomatis disimpan ke .env),\n"
            "atau memilih [bold]Mode Demo[/bold] untuk menguji otomatisasi browser terlebih dahulu.",
            border_style="yellow"
        ))

        key_input = Prompt.ask("[cyan]Masukkan GEMINI_API_KEY[/cyan] (tekan Enter untuk Mode Demo)", default="").strip()
        if key_input:
            env_file = Path(".env")
            env_file.write_text(f"GEMINI_API_KEY={key_input}\n", encoding="utf-8")
            os.environ["GEMINI_API_KEY"] = key_input
            console.print("[bold green]✓ API Key berhasil disimpan ke file .env![/bold green]")
            return GeminiSolver(api_key=key_input)
        else:
            console.print("[dim]Mengaktifkan Mode Demo (tanpa kuota API, menggunakan solver simulasi)...[/dim]")
            return GeminiSolver(allow_demo=True)


def main():
    show_banner()
    solver = get_or_setup_solver()

    while True:
        console.print("\n[bold]Menu Utama:[/bold]")
        console.print("  [1] [cyan]Mulai Kuis Browser (Website Kuis Target Asli)[/cyan]")
        console.print("  [2] [green]Jalankan Simulasi Demo (Uji Coba Otomatis di Layar)[/green]")
        console.print("  [3] [yellow]Mode Tempel Teks / HTML Manual (1 Soal Cepat)[/yellow]")
        console.print("  [4] [red]Keluar[/red]")

        pilihan = Prompt.ask("Pilih menu", choices=["1", "2", "3", "4"], default="1")
        if pilihan == "1":
            run_browser_session(solver)
        elif pilihan == "2":
            run_simulation(solver)
        elif pilihan == "3":
            run_manual_paste_session(solver)
        else:
            console.print("[cyan]Terima kasih dan semoga sukses![/cyan]")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Program dihentikan oleh pengguna.[/yellow]")
        sys.exit(0)


