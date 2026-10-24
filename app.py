
import tkinter as tk
from tkinter import filedialog, messagebox
import threading

try:
    import numpy as np
    import soundfile as sf
except ImportError:
    np = None
    sf = None


class VeryRareStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("VeryRare AI Studio")
        self.root.geometry("620x520")
        self.root.minsize(500, 450)
        self.root.configure(bg="#171321")

        self.vocal_path = None
        self.music_path = None

        self.title_label = tk.Label(
            root, text="VeryRare AI Studio",
            font=("Arial", 23, "bold"),
            fg="#e6d8ff", bg="#171321"
        )
        self.title_label.pack(pady=(22, 4))

        tk.Label(
            root, text="Dreamy Lo-fi • Vocal Mixing",
            font=("Arial", 10),
            fg="#b9a9d3", bg="#171321"
        ).pack(pady=(0, 20))

        self.vocal_label = self.make_file_button(
            "Import Vocal", self.load_vocal
        )
        self.music_label = self.make_file_button(
            "Import Instrumental", self.load_music
        )

        self.vocal_volume = self.make_slider(
            "Vocal volume", 0, 150, 100
        )
        self.music_volume = self.make_slider(
            "Instrumental volume", 0, 150, 80
        )

        self.status = tk.Label(
            root, text="Ready to create your mix",
            fg="#c7b6dc", bg="#171321",
            wraplength=550
        )
        self.status.pack(pady=15)

        tk.Button(
            root, text="Export Mixed WAV",
            command=self.export_mix,
            font=("Arial", 12, "bold"),
            bg="#7046a8", fg="white",
            activebackground="#8c5bc7",
            activeforeground="white",
            relief="flat", padx=18, pady=10
        ).pack(pady=8)

        tk.Label(
            root,
            text="First version: WAV import and export",
            fg="#887b9c", bg="#171321",
            font=("Arial", 9)
        ).pack(side="bottom", pady=15)

    def make_file_button(self, text, command):
        frame = tk.Frame(self.root, bg="#171321")
        frame.pack(fill="x", padx=35, pady=7)

        button = tk.Button(
            frame, text=text, command=command,
            width=20, bg="#30263e", fg="white",
            activebackground="#49365d",
            relief="flat", pady=8
        )
        button.pack(side="left")

        label = tk.Label(
            frame, text="No file selected",
            fg="#b9a9d3", bg="#171321",
            anchor="w", wraplength=260
        )
        label.pack(side="left", padx=12)

        return label

    def make_slider(self, title, minimum, maximum, initial):
        frame = tk.Frame(self.root, bg="#171321")
        frame.pack(fill="x", padx=35, pady=5)

        tk.Label(
            frame, text=title, fg="white",
            bg="#171321", width=20, anchor="w"
        ).pack(side="left")

        slider = tk.Scale(
            frame, from_=minimum, to=maximum,
            orient="horizontal", showvalue=True,
            bg="#171321", fg="white",
            troughcolor="#49365d",
            highlightthickness=0,
            activebackground="#b18ae8"
        )
        slider.set(initial)
        slider.pack(side="left", fill="x", expand=True)
        return slider

    def choose_audio(self):
        return filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[
                ("WAV audio", "*.wav"),
                ("All files", "*.*")
            ]
        )

    def load_vocal(self):
        path = self.choose_audio()
        if path:
            self.vocal_path = path
            self.vocal_label.config(
                text=path.split("/")[-1]
            )
            self.status.config(text="Vocal loaded")

    def load_music(self):
        path = self.choose_audio()
        if path:
            self.music_path = path
            self.music_label.config(
                text=path.split("/")[-1]
            )
            self.status.config(text="Instrumental loaded")

    @staticmethod
    def to_stereo(audio):
        if audio.ndim == 1:
            return np.column_stack((audio, audio))
        if audio.shape[1] == 1:
            return np.repeat(audio, 2, axis=1)
        return audio[:, :2]

    @staticmethod
    def resample_audio(audio, old_rate, new_rate):
        if old_rate == new_rate:
            return audio

        new_length = max(
            1, round(len(audio) * new_rate / old_rate)
        )
        old_positions = np.arange(len(audio))
        new_positions = np.linspace(
            0, max(0, len(audio) - 1), new_length
        )

        if audio.ndim == 1:
            return np.interp(
                new_positions, old_positions, audio
            )

        return np.column_stack([
            np.interp(
                new_positions, old_positions, audio[:, channel]
            )
            for channel in range(audio.shape[1])
        ])

    def export_mix(self):
        if np is None or sf is None:
            messagebox.showerror(
                "Missing libraries",
                "Install the required libraries first:\n"
                "pip install numpy soundfile"
            )
            return

        if not self.vocal_path or not self.music_path:
            messagebox.showwarning(
                "Missing audio",
                "Please import both a vocal and an instrumental."
            )
            return

        output = filedialog.asksaveasfilename(
            title="Save mixed audio",
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav")]
        )
        if not output:
            return

        self.status.config(text="Mixing audio...")

        threading.Thread(
            target=self.mix_worker,
            args=(output,),
            daemon=True
        ).start()

    def mix_worker(self, output):
        try:
            vocal, vocal_rate = sf.read(
                self.vocal_path, dtype="float32",
                always_2d=False
            )
            music, music_rate = sf.read(
                self.music_path, dtype="float32",
                always_2d=False
            )

            vocal = self.to_stereo(vocal)
            music = self.to_stereo(music)

            music = self.resample_audio(
                music, music_rate, vocal_rate
            )

            length = max(len(vocal), len(music))
            mix = np.zeros((length, 2), dtype=np.float32)

            vocal_gain = self.vocal_volume.get() / 100.0
            music_gain = self.music_volume.get() / 100.0

            mix[:len(music)] += music * music_gain
            mix[:len(vocal)] += vocal * vocal_gain

            peak = float(np.max(np.abs(mix)))
            if peak > 0.99:
                mix *= 0.99 / peak

            sf.write(output, mix, vocal_rate, subtype="PCM_16")

            self.root.after(
                0, lambda: self.status.config(
                    text="Mix exported successfully!"
                )
            )
            self.root.after(
                0, lambda: messagebox.showinfo(
                    "VeryRare AI Studio",
                    "Your mixed WAV file has been saved."
                )
            )

        except Exception as error:
            message = str(error)
            self.root.after(
                0, lambda: self.status.config(
                    text="Mixing failed"
                )
            )
            self.root.after(
                0, lambda: messagebox.showerror(
                    "Mixing error", message
                )
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = VeryRareStudio(root)
    root.mainloop()
