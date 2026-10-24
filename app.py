import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
import soundfile as sf
from pedalboard import (
    Pedalboard,
    Reverb,
    Delay,
    Compressor,
    LowpassFilter,
    Gain,
)


BG = "#171321"
PANEL = "#241d31"
PURPLE = "#7046a8"
TEXT = "#e6d8ff"
MUTED = "#b9a9d3"


class VeryRareStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("VeryRare AI Studio")
        self.root.geometry("720x760")
        self.root.minsize(600, 650)
        self.root.configure(bg=BG)

        self.vocal_path = None
        self.music_path = None

        tk.Label(
            root,
            text="VeryRare AI Studio",
            font=("Arial", 24, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(pady=(18, 3))

        tk.Label(
            root,
            text="Dreamy Lo-fi Vocal Mixing Studio",
            fg=MUTED,
            bg=BG,
        ).pack(pady=(0, 15))

        self.vocal_label = self.file_row(
            "Import Vocal WAV", self.load_vocal
        )
        self.music_label = self.file_row(
            "Import Instrumental WAV", self.load_music
        )

        tk.Label(
            root,
            text="Describe the sound you want",
            font=("Arial", 11, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(anchor="w", padx=25, pady=(12, 5))

        self.prompt = tk.Text(
            root,
            height=3,
            wrap="word",
            font=("Arial", 11),
            bg=PANEL,
            fg="white",
            insertbackground="white",
            relief="flat",
            padx=10,
            pady=8,
        )
        self.prompt.pack(fill="x", padx=25)
        self.prompt.insert(
            "1.0",
            "Dreamcore mix, warm soft vocal, light reverb"
        )

        tk.Button(
            root,
            text="Apply Prompt",
            command=self.apply_prompt,
            bg=PURPLE,
            fg="white",
            relief="flat",
            padx=18,
            pady=7,
        ).pack(pady=8)

        effects = tk.LabelFrame(
            root,
            text="Vocal Effects",
            bg=BG,
            fg=TEXT,
            padx=8,
            pady=6,
        )
        effects.pack(fill="x", padx=25, pady=5)

        self.fx = {}
        options = [
            ("warm", "Warm / Soft", True),
            ("reverb", "Reverb", True),
            ("delay", "Delay", False),
            ("compress", "Compressor", True),
            ("dreamcore", "Dreamcore", False),
            ("natural", "Natural Vocal", False),
        ]

        for key, label, default in options:
            var = tk.BooleanVar(value=default)
            self.fx[key] = var

            tk.Checkbutton(
                effects,
                text=label,
                variable=var,
                bg=BG,
                fg="white",
                selectcolor=PANEL,
                activebackground=BG,
                activeforeground="white",
            ).pack(anchor="w", padx=8)

        self.vocal_volume = self.slider(
            "Vocal Volume (%)", 0, 150, 100
        )
        self.music_volume = self.slider(
            "Music Volume (%)", 0, 150, 72
        )

        self.status = tk.Label(
            root,
            text="Import your vocal and instrumental WAV files.",
            fg=MUTED,
            bg=BG,
            wraplength=650,
        )
        self.status.pack(pady=12)

        tk.Button(
            root,
            text="Export Mixed WAV",
            command=self.export_mix,
            font=("Arial", 12, "bold"),
            bg=PURPLE,
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
        ).pack(pady=5)

        tk.Label(
            root,
            text="Prompt matching is rule-based in this version.",
            fg="#887b9c",
            bg=BG,
            font=("Arial", 9),
        ).pack(side="bottom", pady=10)

    def file_row(self, label, command):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="x", padx=25, pady=5)

        tk.Button(
            frame,
            text=label,
            command=command,
            width=22,
            bg=PANEL,
            fg="white",
            relief="flat",
            pady=7,
        ).pack(side="left")

        name = tk.Label(
            frame,
            text="No file selected",
            fg=MUTED,
            bg=BG,
            anchor="w",
            wraplength=400,
        )
        name.pack(side="left", padx=10)

        return name

    def slider(self, label, low, high, initial):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="x", padx=25, pady=3)

        tk.Label(
            frame,
            text=label,
            width=22,
            anchor="w",
            fg="white",
            bg=BG,
        ).pack(side="left")

        control = tk.Scale(
            frame,
            from_=low,
            to=high,
            orient="horizontal",
            bg=BG,
            fg="white",
            troughcolor="#49365d",
            highlightthickness=0,
        )
        control.set(initial)
        control.pack(side="left", fill="x", expand=True)

        return control

    def choose_wav(self):
        return filedialog.askopenfilename(
            title="Choose WAV audio",
            filetypes=[
                ("WAV audio", "*.wav"),
                ("All files", "*.*"),
            ],
        )

    def load_vocal(self):
        path = self.choose_wav()
        if path:
            self.vocal_path = path
            self.vocal_label.config(
                text=os.path.basename(path)
            )
            self.status.config(text="Vocal loaded.")

    def load_music(self):
        path = self.choose_wav()
        if path:
            self.music_path = path
            self.music_label.config(
                text=os.path.basename(path)
            )
            self.status.config(text="Instrumental loaded.")

    def apply_prompt(self):
        prompt = self.prompt.get("1.0", "end").strip().lower()

        if not prompt:
            self.status.config(text="Write a prompt first.")
            return

        if any(x in prompt for x in (
            "natural", "less effects", "dry vocal",
            "طبيعي", "بدون مؤثرات", "خفف المؤثرات",
            "صوت طبيعي",
        )):
            self.fx["natural"].set(True)
            self.fx["reverb"].set(False)
            self.fx["delay"].set(False)
            self.fx["dreamcore"].set(False)

        if any(x in prompt for x in (
            "warm", "soft", "warmth",
            "ناعم", "دافئ", "دفء",
        )):
            self.fx["warm"].set(True)

        if any(x in prompt for x in (
            "reverb", "صدى", "ريفيرب",
        )):
            self.fx["reverb"].set(True)
            self.fx["natural"].set(False)

        if any(x in prompt for x in (
            "delay", "distant echo",
            "ديلاي", "تأخير",
        )):
            self.fx["delay"].set(True)
            self.fx["natural"].set(False)

        if any(x in prompt for x in (
            "compress", "steady vocal",
            "ضغط الصوت", "ثبات الصوت",
        )):
            self.fx["compress"].set(True)

        if any(x in prompt for x in (
            "dreamcore", "otherworldly",
            "from another world",
            "دريمكور", "عالم آخر",
        )):
            self.fx["dreamcore"].set(True)
            self.fx["reverb"].set(True)
            self.fx["delay"].set(True)
            self.fx["natural"].set(False)

        if any(x in prompt for x in (
            "music lower", "quieter music",
            "lower instrumental",
            "الموسيقى أخفض", "وطي الموسيقى",
            "الموسيقى اوطى",
        )):
            self.music_volume.set(55)

        if any(x in prompt for x in (
            "vocal louder", "voice louder",
            "علي صوتي", "صوتي أعلى",
        )):
            self.vocal_volume.set(110)

        self.status.config(
            text="Prompt applied. Review effects before exporting."
        )

    @staticmethod
    def to_stereo(audio):
        if audio.ndim == 1:
            return np.column_stack((audio, audio))

        if audio.shape[1] == 1:
            return np.repeat(audio, 2, axis=1)

        return audio[:, :2]

    @staticmethod
    def resample(audio, old_rate, new_rate):
        if old_rate == new_rate:
            return audio

        new_length = max(
            1, round(len(audio) * new_rate / old_rate)
        )

        old_x = np.arange(len(audio))
        new_x = np.linspace(
            0, len(audio) - 1, new_length
        )

        return np.column_stack([
            np.interp(new_x, old_x, audio[:, channel])
            for channel in range(audio.shape[1])
        ])

    def make_effects(self):
        chain = []

        if self.fx["warm"].get():
            chain.append(
                LowpassFilter(cutoff_frequency_hz=16000)
            )
            chain.append(Gain(gain_db=0.5))

        if self.fx["compress"].get():
            chain.append(
                Compressor(
                    threshold_db=-20,
                    ratio=2.0,
                    attack_ms=15,
                    release_ms=120,
                )
            )

        if self.fx["natural"].get():
            return Pedalboard(chain)

        if self.fx["dreamcore"].get():
            chain.append(
                Delay(
                    delay_seconds=0.38,
                    feedback=0.18,
                    mix=0.09,
                )
            )
            chain.append(
                Reverb(
                    room_size=0.62,
                    damping=0.55,
                    wet_level=0.17,
                    dry_level=0.83,
                )
            )
        else:
            if self.fx["delay"].get():
                chain.append(
                    Delay(
                        delay_seconds=0.28,
                        feedback=0.12,
                        mix=0.08,
                    )
                )

            if self.fx["reverb"].get():
                chain.append(
                    Reverb(
                        room_size=0.28,
                        damping=0.6,
                        wet_level=0.11,
                        dry_level=0.89,
                    )
                )

        return Pedalboard(chain)

    def export_mix(self):
        if not self.vocal_path or not self.music_path:
            messagebox.showwarning(
                "Missing audio",
                "Import both vocal and instrumental WAV files first.",
            )
            return

        output = filedialog.asksaveasfilename(
            title="Save mixed audio",
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav")],
            initialfile="VeryRare_Mix.wav",
        )

        if not output:
            return

        self.status.config(text="Processing audio... please wait.")

        vocal_path = self.vocal_path
        music_path = self.music_path
        vocal_gain = self.vocal_volume.get() / 100.0
        music_gain = self.music_volume.get() / 100.0
        board = self.make_effects()

        thread = threading.Thread(
            target=self.process_audio,
            args=(
                vocal_path,
                music_path,
                output,
                vocal_gain,
                music_gain,
                board,
            ),
            daemon=True,
        )
        thread.start()

    def process_audio(
        self,
        vocal_path,
        music_path,
        output,
        vocal_gain,
        music_gain,
        board,
    ):
        try:
            vocal, vocal_rate = sf.read(
                vocal_path, dtype="float32", always_2d=False
            )
            music, music_rate = sf.read(
                music_path, dtype="float32", always_2d=False
            )

            vocal = self.to_stereo(vocal)
            music = self.to_stereo(music)

            # Use the vocal sample rate as the output rate.
            music = self.resample(
                music, music_rate, vocal_rate
            )

            # Apply effects to the vocal only.
            processed_vocal = board(
                vocal.T, vocal_rate
            ).T

            # Match both tracks to the same duration.
            length = max(
                len(processed_vocal), len(music)
            )

            vocal_mix = np.zeros((length, 2), dtype=np.float32)
            music_mix = np.zeros((length, 2), dtype=np.float32)

            vocal_mix[:len(processed_vocal)] = processed_vocal
            music_mix[:len(music)] = music

            mixed = (
                vocal_mix * vocal_gain
                + music_mix * music_gain
            )

            # Prevent digital clipping while retaining dynamics.
            peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
            if peak > 0.99:
                mixed *= 0.99 / peak

            sf.write(
                output,
                mixed,
                vocal_rate,
                subtype="PCM_16",
            )

            self.root.after(
                0,
                lambda: self.finish_success(output),
            )

        except Exception as exc:
            error = str(exc)
            self.root.after(
                0,
                lambda err=error: self.finish_error(err),
            )

    def finish_success(self, output):
        self.status.config(
            text=f"Export complete: {os.path.basename(output)}"
        )
        messagebox.showinfo(
            "VeryRare AI Studio",
            f"Your WAV mix was saved:\n{output}",
        )

    def finish_error(self, error):
        self.status.config(text="Processing failed.")
        messagebox.showerror(
            "Audio processing error",
            error,
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = VeryRareStudio(root)
    root.mainloop()
