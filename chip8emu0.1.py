"""ac's CHIP-8 emu 0.1 — 600×400 tkinter shell, mGBA-style blue / black UI."""
from __future__ import annotations

import random
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

MEMORY_SIZE = 4096
START_ADDRESS = 0x200
NUM_REGISTERS = 16
DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 32
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 400
FPS = 60
INSTRUCTIONS_PER_FRAME = 10

# mGBA-inspired palette
MGBA_BLUE = "#4DA6FF"
MGBA_BLUE_DIM = "#2E7FD4"
BLACK = "#000000"
BG_HUE = "#0B1A33"
PANEL_BG = "#061220"
BEZEL = "#1A3A6B"

BUTTON_BG = BLACK
BUTTON_ACTIVE = "#0D2138"
BUTTON_OUTLINE = MGBA_BLUE

KEYS = {
    "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xC,
    "q": 0x4, "w": 0x5, "e": 0x6, "r": 0xD,
    "a": 0x7, "s": 0x8, "d": 0x9, "f": 0xE,
    "z": 0xA, "x": 0x0, "c": 0xB, "v": 0xF,
}

KEY_LABELS = {
    0x1: "1", 0x2: "2", 0x3: "3", 0xC: "C",
    0x4: "4", 0x5: "5", 0x6: "6", 0xD: "D",
    0x7: "7", 0x8: "8", 0x9: "9", 0xE: "E",
    0xA: "A", 0x0: "0", 0xB: "B", 0xF: "F",
}

FONTSET = [
    0xF0, 0x90, 0x90, 0x90, 0xF0,
    0x20, 0x60, 0x20, 0x20, 0x70,
    0xF0, 0x10, 0xF0, 0x80, 0xF0,
    0xF0, 0x10, 0xF0, 0x10, 0xF0,
    0x90, 0x90, 0xF0, 0x10, 0x10,
    0xF0, 0x80, 0xF0, 0x10, 0xF0,
    0xF0, 0x80, 0xF0, 0x90, 0xF0,
    0xF0, 0x10, 0x20, 0x40, 0x40,
    0xF0, 0x90, 0xF0, 0x90, 0xF0,
    0xF0, 0x90, 0xF0, 0x10, 0xF0,
    0xF0, 0x90, 0xF0, 0x90, 0x90,
    0xE0, 0x90, 0xE0, 0x90, 0xE0,
    0xF0, 0x80, 0x80, 0x80, 0xF0,
    0xE0, 0x90, 0x90, 0x90, 0xE0,
    0xF0, 0x80, 0xF0, 0x80, 0xF0,
    0xF0, 0x80, 0xF0, 0x80, 0x80,
]

KEYPAD_LAYOUT = [
    [0x1, 0x2, 0x3, 0xC],
    [0x4, 0x5, 0x6, 0xD],
    [0x7, 0x8, 0x9, 0xE],
    [0xA, 0x0, 0xB, 0xF],
]


class Chip8:
    def __init__(self):
        self.memory = [0] * MEMORY_SIZE
        self.registers = [0] * NUM_REGISTERS
        self.index = 0
        self.pc = START_ADDRESS
        self.stack = []
        self.display = [[0] * DISPLAY_WIDTH for _ in range(DISPLAY_HEIGHT)]
        self.delay_timer = 0
        self.sound_timer = 0
        self.keypad = [0] * 16
        self.waiting_for_key = False
        self.wait_key_register = 0
        self.draw_flag = False
        for i, font in enumerate(FONTSET):
            self.memory[i] = font

    def load_rom(self, rom_path: str) -> None:
        with open(rom_path, "rb") as f:
            rom_data = f.read()
        for i, byte in enumerate(rom_data):
            if START_ADDRESS + i >= MEMORY_SIZE:
                raise ValueError("ROM too large for CHIP-8 memory")
            self.memory[START_ADDRESS + i] = byte
        self.pc = START_ADDRESS
        self.stack.clear()
        for row in range(DISPLAY_HEIGHT):
            for col in range(DISPLAY_WIDTH):
                self.display[row][col] = 0

    def cycle(self):
        if self.waiting_for_key:
            return

        opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 2

        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F
        nn = opcode & 0x00FF
        nnn = opcode & 0x0FFF

        if opcode == 0x00E0:
            for row in range(DISPLAY_HEIGHT):
                for col in range(DISPLAY_WIDTH):
                    self.display[row][col] = 0
            self.draw_flag = True
        elif opcode == 0x00EE:
            self.pc = self.stack.pop()
        elif (opcode & 0xF000) == 0x1000:
            self.pc = nnn
        elif (opcode & 0xF000) == 0x2000:
            self.stack.append(self.pc)
            self.pc = nnn
        elif (opcode & 0xF000) == 0x3000:
            if self.registers[x] == nn:
                self.pc += 2
        elif (opcode & 0xF000) == 0x4000:
            if self.registers[x] != nn:
                self.pc += 2
        elif (opcode & 0xF00F) == 0x5000:
            if self.registers[x] == self.registers[y]:
                self.pc += 2
        elif (opcode & 0xF000) == 0x6000:
            self.registers[x] = nn
        elif (opcode & 0xF000) == 0x7000:
            self.registers[x] = (self.registers[x] + nn) & 0xFF
        elif (opcode & 0xF00F) == 0x8000:
            self.registers[x] = self.registers[y]
        elif (opcode & 0xF00F) == 0x8001:
            self.registers[x] |= self.registers[y]
        elif (opcode & 0xF00F) == 0x8002:
            self.registers[x] &= self.registers[y]
        elif (opcode & 0xF00F) == 0x8003:
            self.registers[x] ^= self.registers[y]
        elif (opcode & 0xF00F) == 0x8004:
            total = self.registers[x] + self.registers[y]
            self.registers[0xF] = 1 if total > 0xFF else 0
            self.registers[x] = total & 0xFF
        elif (opcode & 0xF00F) == 0x8005:
            self.registers[0xF] = 1 if self.registers[x] >= self.registers[y] else 0
            self.registers[x] = (self.registers[x] - self.registers[y]) & 0xFF
        elif (opcode & 0xF00F) == 0x8006:
            self.registers[0xF] = self.registers[x] & 1
            self.registers[x] >>= 1
        elif (opcode & 0xF00F) == 0x8007:
            self.registers[0xF] = 1 if self.registers[y] >= self.registers[x] else 0
            self.registers[x] = (self.registers[y] - self.registers[x]) & 0xFF
        elif (opcode & 0xF00F) == 0x800E:
            self.registers[0xF] = (self.registers[x] >> 7) & 1
            self.registers[x] = (self.registers[x] << 1) & 0xFF
        elif (opcode & 0xF00F) == 0x9000:
            if self.registers[x] != self.registers[y]:
                self.pc += 2
        elif (opcode & 0xF000) == 0xA000:
            self.index = nnn
        elif (opcode & 0xF000) == 0xB000:
            self.pc = nnn + self.registers[0]
        elif (opcode & 0xF000) == 0xC000:
            self.registers[x] = random.randint(0, 255) & nn
        elif (opcode & 0xF000) == 0xD000:
            x_pos = self.registers[x] % DISPLAY_WIDTH
            y_pos = self.registers[y] % DISPLAY_HEIGHT
            self.registers[0xF] = 0
            for row in range(n):
                if y_pos + row >= DISPLAY_HEIGHT:
                    break
                sprite_byte = self.memory[self.index + row]
                for col in range(8):
                    if x_pos + col >= DISPLAY_WIDTH:
                        break
                    if (sprite_byte >> (7 - col)) & 1:
                        if self.display[y_pos + row][x_pos + col] == 1:
                            self.registers[0xF] = 1
                        self.display[y_pos + row][x_pos + col] ^= 1
            self.draw_flag = True
        elif (opcode & 0xF0FF) == 0xE09E:
            if self.keypad[self.registers[x]]:
                self.pc += 2
        elif (opcode & 0xF0FF) == 0xE0A1:
            if not self.keypad[self.registers[x]]:
                self.pc += 2
        elif (opcode & 0xF0FF) == 0xF007:
            self.registers[x] = self.delay_timer
        elif (opcode & 0xF0FF) == 0xF00A:
            self.waiting_for_key = True
            self.wait_key_register = x
        elif (opcode & 0xF0FF) == 0xF015:
            self.delay_timer = self.registers[x]
        elif (opcode & 0xF0FF) == 0xF018:
            self.sound_timer = self.registers[x]
        elif (opcode & 0xF0FF) == 0xF01E:
            self.index = (self.index + self.registers[x]) & 0xFFFF
        elif (opcode & 0xF0FF) == 0xF029:
            self.index = self.registers[x] * 5
        elif (opcode & 0xF0FF) == 0xF033:
            val = self.registers[x]
            self.memory[self.index] = val // 100
            self.memory[self.index + 1] = (val // 10) % 10
            self.memory[self.index + 2] = val % 10
        elif (opcode & 0xF0FF) == 0xF055:
            for i in range(x + 1):
                self.memory[self.index + i] = self.registers[i]
        elif (opcode & 0xF0FF) == 0xF065:
            for i in range(x + 1):
                self.registers[i] = self.memory[self.index + i]

    def decrement_timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1

    def press_key(self, key_val: int) -> None:
        self.keypad[key_val] = 1
        if self.waiting_for_key:
            self.registers[self.wait_key_register] = key_val
            self.waiting_for_key = False

    def release_key(self, key_val: int) -> None:
        self.keypad[key_val] = 0


class Chip8Emulator(tk.Tk):
    DISPLAY_W = 384
    KEYPAD_W = WINDOW_WIDTH - DISPLAY_W - 24

    def __init__(self):
        super().__init__()
        self.title("ac's chip 8 emu 0.1")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.configure(bg=BG_HUE)
        self.resizable(False, False)

        self.chip8 = Chip8()
        self.paused = False
        self._after_id: str | None = None
        self._rom_path: str | None = None

        self._btn_style = {
            "bg": BUTTON_BG,
            "fg": MGBA_BLUE,
            "activebackground": BUTTON_ACTIVE,
            "activeforeground": MGBA_BLUE,
            "highlightbackground": BEZEL,
            "highlightcolor": MGBA_BLUE,
            "relief": tk.FLAT,
            "bd": 1,
            "font": ("Helvetica", 10, "bold"),
            "cursor": "hand2",
        }

        self._build_ui()
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        if len(sys.argv) > 1:
            self._load_rom_path(sys.argv[1])
        else:
            self.after(100, self.open_rom)

    def _build_ui(self) -> None:
        top = tk.Frame(self, bg=PANEL_BG, height=36)
        top.pack(fill=tk.X, side=tk.TOP)
        top.pack_propagate(False)

        tk.Label(
            top,
            text="CHIP-8",
            bg=PANEL_BG,
            fg=MGBA_BLUE,
            font=("Helvetica", 11, "bold"),
        ).pack(side=tk.LEFT, padx=10, pady=6)

        tk.Button(top, text="Open ROM…", command=self.open_rom, **self._btn_style).pack(
            side=tk.LEFT, padx=4, pady=4
        )
        tk.Button(top, text="Pause", command=self.toggle_pause, **self._btn_style).pack(
            side=tk.LEFT, padx=4, pady=4
        )

        body = tk.Frame(self, bg=BG_HUE)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        screen_frame = tk.Frame(body, bg=PANEL_BG, bd=0, highlightthickness=2, highlightbackground=BEZEL)
        screen_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            screen_frame,
            width=self.DISPLAY_W,
            height=WINDOW_HEIGHT - 36 - 28 - 20,
            bg=BLACK,
            highlightthickness=0,
        )
        self.canvas.pack(padx=6, pady=6)

        pad_frame = tk.Frame(body, bg=BG_HUE, width=self.KEYPAD_W)
        pad_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        pad_frame.pack_propagate(False)

        tk.Label(
            pad_frame,
            text="Keypad",
            bg=BG_HUE,
            fg=MGBA_BLUE_DIM,
            font=("Helvetica", 9),
        ).pack(anchor=tk.W, pady=(0, 4))

        pad_grid = tk.Frame(pad_frame, bg=BG_HUE)
        pad_grid.pack()

        self._pad_buttons: dict[int, tk.Button] = {}
        for row_keys in KEYPAD_LAYOUT:
            row = tk.Frame(pad_grid, bg=BG_HUE)
            row.pack(pady=2)
            for key_val in row_keys:
                btn = tk.Button(
                    row,
                    text=KEY_LABELS[key_val],
                    width=3,
                    height=1,
                    command=lambda k=key_val: self._tap_key(k),
                    **self._btn_style,
                )
                btn.pack(side=tk.LEFT, padx=2)
                btn.bind("<ButtonPress-1>", lambda e, k=key_val: self.chip8.press_key(k))
                btn.bind("<ButtonRelease-1>", lambda e, k=key_val: self.chip8.release_key(k))
                self._pad_buttons[key_val] = btn

        self.status = tk.Label(
            self,
            text="Load a .ch8 ROM — keyboard: 1-4, Q-R, A-F, Z-V  •  Space: pause",
            bg=BLACK,
            fg=MGBA_BLUE,
            anchor=tk.W,
            font=("Helvetica", 9),
            padx=10,
            pady=6,
        )
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        self.update_emulation()

    def _tap_key(self, key_val: int) -> None:
        self.chip8.press_key(key_val)
        self.after(80, lambda: self.chip8.release_key(key_val))

    def _load_rom_path(self, path: str) -> None:
        try:
            self.chip8.load_rom(path)
            self._rom_path = path
            name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            self.status.config(text=f"ROM: {name}  •  Space: pause  •  Esc: quit")
            self.paused = False
        except OSError as ex:
            messagebox.showerror("ROM error", str(ex), parent=self)
        except ValueError as ex:
            messagebox.showerror("ROM error", str(ex), parent=self)

    def open_rom(self) -> None:
        path = filedialog.askopenfilename(
            title="Open CHIP-8 ROM",
            filetypes=[("CHIP-8 ROM", "*.ch8"), ("All files", "*.*")],
        )
        if path:
            self._load_rom_path(path)

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self._refresh_status()

    def _refresh_status(self) -> None:
        base = self._rom_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] if self._rom_path else "No ROM"
        state = "PAUSED" if self.paused else "RUNNING"
        self.status.config(text=f"{base}  •  {state}  •  Space: pause  •  Esc: quit")

    def on_key_press(self, event) -> None:
        if event.keysym == "Escape":
            self.on_close()
        elif event.keysym == "space":
            self.toggle_pause()
        elif event.char in KEYS:
            self.chip8.press_key(KEYS[event.char])

    def on_key_release(self, event) -> None:
        if event.char in KEYS:
            self.chip8.release_key(KEYS[event.char])

    def on_close(self) -> None:
        if self._after_id:
            self.after_cancel(self._after_id)
        self.destroy()

    def _display_geometry(self) -> tuple[int, int, int, int]:
        cw = int(self.canvas.winfo_width() or self.DISPLAY_W)
        ch = int(self.canvas.winfo_height() or (WINDOW_HEIGHT - 84))
        scale = min(cw // DISPLAY_WIDTH, ch // DISPLAY_HEIGHT)
        scale = max(scale, 1)
        w = DISPLAY_WIDTH * scale
        h = DISPLAY_HEIGHT * scale
        ox = (cw - w) // 2
        oy = (ch - h) // 2
        return scale, ox, oy, w

    def draw_display(self) -> None:
        self.canvas.delete("display")
        scale, ox, oy, _ = self._display_geometry()
        h = DISPLAY_HEIGHT * scale

        self.canvas.create_rectangle(
            ox - 3, oy - 3, ox + DISPLAY_WIDTH * scale + 3, oy + h + 3,
            outline=BEZEL, fill=BLACK, tags="display",
        )

        for row in range(DISPLAY_HEIGHT):
            for col in range(DISPLAY_WIDTH):
                if self.chip8.display[row][col]:
                    x1 = ox + col * scale
                    y1 = oy + row * scale
                    self.canvas.create_rectangle(
                        x1, y1, x1 + scale, y1 + scale,
                        fill=MGBA_BLUE, outline="",
                        tags="display",
                    )

    def draw_buttons(self) -> None:
        for key_val, btn in self._pad_buttons.items():
            if self.chip8.keypad[key_val]:
                btn.configure(bg=BUTTON_ACTIVE, fg=MGBA_BLUE)
            else:
                btn.configure(bg=BUTTON_BG, fg=MGBA_BLUE)

    def update_emulation(self) -> None:
        if self._rom_path and not self.paused:
            for _ in range(INSTRUCTIONS_PER_FRAME):
                self.chip8.cycle()
            self.chip8.decrement_timers()

        self.draw_display()
        self.draw_buttons()

        self._after_id = self.after(1000 // FPS, self.update_emulation)


if __name__ == "__main__":
    Chip8Emulator().mainloop()
