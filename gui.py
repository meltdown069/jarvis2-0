import tkinter as tk


class JarvisGUI:
    def __init__(self, on_submit):
        self.on_submit = on_submit
        self.pulse_phase = 0

        self.root = tk.Tk()
        self.root.title("JARVIS")
        self.root.geometry("920x560+20+20")
        self.root.configure(bg="#020914")
        self.root.attributes("-topmost", True)

        self.status_var = tk.StringVar(value="Booting systems…")
        self.input_var = tk.StringVar()
        self.last_heard_var = tk.StringVar(value="Heard: -")
        self.mode_var = tk.StringVar(value="Listening for wake word")

        self._build_ui()
        self._animate_orb()

    def _build_ui(self) -> None:
        shell = tk.Frame(self.root, bg="#040E1D", highlightbackground="#113554", highlightthickness=1)
        shell.pack(fill="both", expand=True, padx=10, pady=10)

        topbar = tk.Frame(shell, bg="#040E1D")
        topbar.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(topbar, text="J.A.R.V.I.S", fg="#5EE6FF", bg="#040E1D", font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(topbar, text="LOCAL MODE", fg="#A8D9FF", bg="#0E2640", padx=10, pady=3, font=("Segoe UI", 9, "bold")).pack(side="right")

        body = tk.Frame(shell, bg="#040E1D")
        body.pack(fill="both", expand=True, padx=10, pady=8)

        left = tk.Frame(body, bg="#040E1D")
        left.pack(side="left", fill="both", expand=True)

        self.orb = tk.Canvas(left, width=430, height=410, bg="#040E1D", highlightthickness=0)
        self.orb.pack(pady=(8, 0))
        self._draw_orb(0)

        tk.Label(left, text="J.A.R.V.I.S", fg="#DDF3FF", bg="#040E1D", font=("Segoe UI", 20, "bold")).pack(pady=(8, 2))
        tk.Label(left, textvariable=self.mode_var, fg="#9EE7FF", bg="#092035", padx=12, pady=4, font=("Segoe UI", 9)).pack()

        right = tk.Frame(body, bg="#071425", highlightbackground="#113554", highlightthickness=1)
        right.pack(side="right", fill="both", expand=False, padx=(8, 0))
        right.configure(width=360)

        tk.Label(right, text="Conversation", fg="#D7EEFF", bg="#071425", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

        status_wrap = tk.Frame(right, bg="#0A1D33", highlightbackground="#1E3F63", highlightthickness=1)
        status_wrap.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(status_wrap, textvariable=self.status_var, fg="#D5EAFF", bg="#0A1D33", justify="left", wraplength=320, padx=8, pady=8, font=("Segoe UI", 10)).pack(fill="x")

        heard_wrap = tk.Frame(right, bg="#081528")
        heard_wrap.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(heard_wrap, textvariable=self.last_heard_var, fg="#8FBEE8", bg="#081528", anchor="w", padx=8, pady=6, font=("Consolas", 10)).pack(fill="x")

        entry_wrap = tk.Frame(right, bg="#071425")
        entry_wrap.pack(side="bottom", fill="x", padx=10, pady=10)

        entry = tk.Entry(entry_wrap, textvariable=self.input_var, font=("Segoe UI", 11), bg="#05101D", fg="#E6F5FF", insertbackground="#E6F5FF", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.bind("<Return>", self._on_submit)
        tk.Button(entry_wrap, text="SEND", command=self._on_submit, bg="#28C3FF", fg="#01101A", relief="flat", padx=12, pady=6, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 0))

    def _on_submit(self, _event=None):
        txt = self.input_var.get().strip()
        if not txt:
            return
        self.input_var.set("")
        self.last_heard_var.set(f"Manual: {txt}")
        self.on_submit(txt)

    def _draw_orb(self, phase: int) -> None:
        self.orb.delete("all")
        cx, cy = 215, 190
        r1 = 44 + (phase % 8)
        r2 = 72 + ((phase * 2) % 10)
        r3 = 102 + ((phase * 3) % 12)
        self.orb.create_oval(cx - r3, cy - r3, cx + r3, cy + r3, outline="#11385A", width=2)
        self.orb.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline="#1A5A87", width=2)
        self.orb.create_oval(cx - r1, cy - r1, cx + r1, cy + r1, outline="#2A8CC4", width=2)
        self.orb.create_oval(cx - 34, cy - 34, cx + 34, cy + 34, fill="#0B4D7B", outline="#4BC3FF", width=2)

    def _animate_orb(self):
        self.pulse_phase = (self.pulse_phase + 1) % 60
        self._draw_orb(self.pulse_phase)
        self.root.after(130, self._animate_orb)

    def set_status(self, text: str):
        self.status_var.set(text)

    def set_mode(self, text: str):
        self.mode_var.set(text)

    def set_heard(self, text: str):
        self.last_heard_var.set(text)
