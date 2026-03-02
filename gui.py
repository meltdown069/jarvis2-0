import math
import random
import tkinter as tk


class JarvisGUI:
    def __init__(self, on_submit):
        self.on_submit = on_submit
        self.phase = 0.0
        self.speaking_level = 0.0

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
        self._init_particles()
        self._animate_scene()

    def _build_ui(self) -> None:
        shell = tk.Frame(self.root, bg="#040E1D", highlightbackground="#2D1A10", highlightthickness=1)
        shell.pack(fill="both", expand=True, padx=10, pady=10)

        topbar = tk.Frame(shell, bg="#040E1D")
        topbar.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(topbar, text="J.A.R.V.I.S", fg="#FFBF7A", bg="#040E1D", font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(topbar, text="LOCAL MODE", fg="#FFD7A8", bg="#4A2C12", padx=10, pady=3, font=("Segoe UI", 9, "bold")).pack(side="right")

        body = tk.Frame(shell, bg="#040E1D")
        body.pack(fill="both", expand=True, padx=10, pady=8)

        left = tk.Frame(body, bg="#040E1D")
        left.pack(side="left", fill="both", expand=True)

        self.orb = tk.Canvas(left, width=430, height=410, bg="#040E1D", highlightthickness=0)
        self.orb.pack(pady=(8, 0))

        tk.Label(left, text="J.A.R.V.I.S", fg="#FFE9CC", bg="#040E1D", font=("Segoe UI", 20, "bold")).pack(pady=(8, 2))
        tk.Label(left, textvariable=self.mode_var, fg="#FFD4A3", bg="#3A2210", padx=12, pady=4, font=("Segoe UI", 9)).pack()

        right = tk.Frame(body, bg="#071425", highlightbackground="#553318", highlightthickness=1)
        right.pack(side="right", fill="both", expand=False, padx=(8, 0))
        right.configure(width=360)

        tk.Label(right, text="Conversation", fg="#FFE5C1", bg="#071425", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

        status_wrap = tk.Frame(right, bg="#1A120B", highlightbackground="#8A5928", highlightthickness=1)
        status_wrap.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(status_wrap, textvariable=self.status_var, fg="#FFE5CA", bg="#1A120B", justify="left", wraplength=320, padx=8, pady=8, font=("Segoe UI", 10)).pack(fill="x")

        heard_wrap = tk.Frame(right, bg="#0C0E14")
        heard_wrap.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(heard_wrap, textvariable=self.last_heard_var, fg="#FFD8B0", bg="#0C0E14", anchor="w", padx=8, pady=6, font=("Consolas", 10)).pack(fill="x")

        entry_wrap = tk.Frame(right, bg="#071425")
        entry_wrap.pack(side="bottom", fill="x", padx=10, pady=10)

        entry = tk.Entry(entry_wrap, textvariable=self.input_var, font=("Segoe UI", 11), bg="#120B07", fg="#FFE9D2", insertbackground="#FFE9D2", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.bind("<Return>", self._on_submit)
        tk.Button(entry_wrap, text="SEND", command=self._on_submit, bg="#FF9E4A", fg="#1A0D03", relief="flat", padx=12, pady=6, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 0))

    def _init_particles(self):
        self.cx, self.cy = 215, 190
        self.particles = []
        for _ in range(180):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(55, 150)
            speed = random.uniform(0.004, 0.018)
            drift = random.uniform(-0.20, 0.20)
            size = random.uniform(1.0, 3.0)
            self.particles.append({"a": angle, "r": radius, "s": speed, "d": drift, "size": size})

    def _on_submit(self, _event=None):
        txt = self.input_var.get().strip()
        if not txt:
            return
        self.input_var.set("")
        self.last_heard_var.set(f"Manual: {txt}")
        self.on_submit(txt)

    def _animate_scene(self):
        self.phase += 0.12
        self.orb.delete("all")

        wave_amp = 12 + (28 * self.speaking_level)
        ring_jitter = 5 + (9 * self.speaking_level)

        # background rings
        for i, color in enumerate(["#5F3112", "#8A4618", "#B85D23"]):
            base = 60 + (i * 26)
            dynamic = base + math.sin(self.phase + i) * ring_jitter
            self.orb.create_oval(self.cx - dynamic, self.cy - dynamic, self.cx + dynamic, self.cy + dynamic, outline=color, width=2)

        # waveform ring reacts to speaking
        points = []
        for deg in range(0, 360, 8):
            a = math.radians(deg)
            wav = math.sin((deg / 26.0) + (self.phase * 1.8)) * wave_amp
            r = 95 + wav
            x = self.cx + math.cos(a) * r
            y = self.cy + math.sin(a) * r
            points.extend([x, y])
        self.orb.create_line(points, fill="#FFB066", width=2, smooth=True)

        # particles
        for p in self.particles:
            p["a"] += p["s"] + (self.speaking_level * 0.012)
            p["r"] += p["d"] + math.sin(self.phase + p["a"]) * 0.10
            if p["r"] < 50:
                p["r"] = 50
                p["d"] = abs(p["d"])
            if p["r"] > 170:
                p["r"] = 170
                p["d"] = -abs(p["d"])
            x = self.cx + math.cos(p["a"]) * p["r"]
            y = self.cy + math.sin(p["a"]) * p["r"]
            glow = "#FFDAA8" if self.speaking_level > 0.15 else "#FFB977"
            s = p["size"] + (self.speaking_level * 1.4)
            self.orb.create_oval(x - s, y - s, x + s, y + s, fill=glow, outline="")

        # core
        core = 34 + math.sin(self.phase * 1.7) * (4 + (self.speaking_level * 8))
        self.orb.create_oval(self.cx - core, self.cy - core, self.cx + core, self.cy + core, fill="#FF8E3B", outline="#FFD0A1", width=2)

        # decay speaking level (so voice wave fades)
        self.speaking_level = max(0.0, self.speaking_level - 0.035)
        self.root.after(33, self._animate_scene)

    def set_speaking(self, active: bool):
        self.speaking_level = 1.0 if active else max(self.speaking_level, 0.2)

    def pulse_speaking(self, strength: float = 0.65):
        self.speaking_level = max(self.speaking_level, min(1.0, strength))

    def set_status(self, text: str):
        self.status_var.set(text)

    def set_mode(self, text: str):
        self.mode_var.set(text)

    def set_heard(self, text: str):
        self.last_heard_var.set(text)
