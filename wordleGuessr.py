#!/usr/bin/env python3
# Wordle GUI Solver (Entropy + Likelihood)
# - Recommends guess that maximizes expected information gain (entropy)
# - Also shows "most-likely solution" by positional frequencies
# - Click 5 pattern buttons to cycle N → P → C, then "Apply Feedback"
#
# Word lists:
#   - If present in the working dir, the app loads: answers.txt, allowed.txt, or words.txt
#   - Otherwise it uses a small built-in fallback so you can try it immediately.

import os
import string
import tkinter as tk
from tkinter import ttk, messagebox
from collections import Counter, defaultdict
from math import log2
from typing import List, Tuple

# -------------------- fallback words (used if no files found) --------------------
FALLBACK = [
    "arise","adieu","alone","angle","apple","baker","basic","beach","beast","belly",
    "brave","candy","cater","chair","crane","cream","crown","eagle","fancy","flame",
    "glare","grain","grape","graph","great","heart","linen","magma","major","maple",
    "ocean","plant","pride","primo","quiet","raise","ratio","slate","stare","trace",
]
ALPHA = set(string.ascii_lowercase)

# -------------------- word loading --------------------
def load_words() -> Tuple[List[str], List[str]]:
    def read_file(path: str) -> List[str]:
        with open(path, "r", encoding="utf-8") as f:
            words = []
            for line in f:
                w = line.strip().lower()
                if len(w) == 5 and set(w) <= ALPHA:
                    words.append(w)
            return words

    answers, allowed = [], []

    if os.path.exists("words.txt"):
        ws = read_file("words.txt")
        answers = [w for w in ws if len(w) == 5]
        allowed = sorted(set(ws))
    else:
        if os.path.exists("answers.txt"):
            answers = read_file("answers.txt")
        if os.path.exists("allowed.txt"):
            allowed = read_file("allowed.txt")
        if not answers and not allowed:
            answers = FALLBACK[:]
            allowed = sorted(set(FALLBACK))

    allowed = sorted(set(allowed) | set(answers))
    answers = [w for w in answers if len(w) == 5 and set(w) <= ALPHA]
    allowed = [w for w in allowed if len(w) == 5 and set(w) <= ALPHA]
    if not answers:
        answers = allowed[:]
    return answers, allowed

# -------------------- wordle mechanics --------------------
def pattern_for(guess: str, solution: str) -> str:
    g = list(guess)
    s = list(solution)
    res = ["N"] * 5
    remaining = Counter()
    for i in range(5):
        if g[i] == s[i]:
            res[i] = "C"
            s[i] = None
        else:
            remaining[s[i]] += 1
    for i in range(5):
        if res[i] == "C":
            continue
        ch = g[i]
        if remaining[ch] > 0:
            res[i] = "P"
            remaining[ch] -= 1
        else:
            res[i] = "N"
    return "".join(res)

def consistent_with(guess: str, pat: str, candidate: str) -> bool:
    return pattern_for(guess, candidate) == pat

def filter_candidates(cands: List[str], guess: str, pat: str) -> List[str]:
    return [w for w in cands if consistent_with(guess, pat, w)]

# -------------------- scoring --------------------
def position_frequencies(words: List[str]):
    pos = [Counter() for _ in range(5)]
    for w in words:
        for i,ch in enumerate(w):
            pos[i][ch] += 1
    return pos

def likelihood_score(word: str, pos_freq) -> float:
    seen = set()
    score = 0.0
    for i, ch in enumerate(word):
        score += pos_freq[i][ch]
        seen.add(ch)
    score += 0.1 * len(seen)
    return score

def best_likelihood_guess(candidates: List[str]) -> Tuple[str, float]:
    pf = position_frequencies(candidates)
    best, best_s = None, -1.0
    for w in candidates:
        s = likelihood_score(w, pf)
        if s > best_s:
            best, best_s = w, s
    return best, best_s

def entropy_of_guess(guess: str, candidates: List[str]) -> float:
    buckets = defaultdict(int)
    for sol in candidates:
        buckets[pattern_for(guess, sol)] += 1
    n = len(candidates)
    ent = 0.0
    for k in buckets.values():
        p = k / n
        ent += -p * log2(p)
    return ent

def best_entropy_guess(candidates: List[str], allowed: List[str]) -> Tuple[str, float]:
    pool = allowed if len(candidates) > 30 else candidates
    best_g, best_e = None, -1.0
    for g in pool:
        e = entropy_of_guess(g, candidates)
        if e > best_e or (e == best_e and g in candidates and best_g not in candidates):
            best_g, best_e = g, e
    return best_g, best_e

# -------------------- GUI --------------------
class WordleGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wordle Solver (Entropy + Likelihood)")
        self.minsize(720, 520)

        self.answers, self.allowed = load_words()
        self.candidates = self.answers[:]
        self.turn = 1

        self._build_widgets()
        self._refresh_recommendation(initial=True)

    def _build_widgets(self):
        # Top: status
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        self.status_var = tk.StringVar()
        self.status_var.set(f"Loaded {len(self.answers)} answers, {len(self.allowed)} allowed.")
        ttk.Label(top, textvariable=self.status_var).pack(side="left")

        # Recommendation frame
        rec = ttk.LabelFrame(self, text="Recommendation", padding=10)
        rec.pack(fill="x", padx=10, pady=(0,10))

        # Recommended (max info)
        self.ent_guess_var = tk.StringVar(value="—")
        self.ent_bits_var = tk.StringVar(value="—")
        ttk.Label(rec, text="Max-info guess: ").grid(row=0, column=0, sticky="w", padx=(0,4))
        ttk.Label(rec, textvariable=self.ent_guess_var, font=("TkDefaultFont", 12, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(rec, text=" (bits: ").grid(row=0, column=2, sticky="w")
        ttk.Label(rec, textvariable=self.ent_bits_var).grid(row=0, column=3, sticky="w")
        ttk.Label(rec, text=")").grid(row=0, column=4, sticky="w")

        self.use_ent_btn = ttk.Button(rec, text="Use Recommended", command=self._use_recommended)
        self.use_ent_btn.grid(row=0, column=5, padx=8)

        # Most likely solution
        self.like_guess_var = tk.StringVar(value="—")
        ttk.Label(rec, text="Most-likely solution: ").grid(row=1, column=0, sticky="w", pady=(6,0))
        ttk.Label(rec, textvariable=self.like_guess_var).grid(row=1, column=1, sticky="w", pady=(6,0))

        # Input frame
        inp = ttk.LabelFrame(self, text="Enter guess & set feedback", padding=10)
        inp.pack(fill="x", padx=10, pady=(0,10))

        ttk.Label(inp, text="Guess:").grid(row=0, column=0, sticky="e")
        self.guess_entry = ttk.Entry(inp, width=12, font=("TkDefaultFont", 12, "bold"))
        self.guess_entry.grid(row=0, column=1, sticky="w", padx=(6,10))
        self.guess_entry.insert(0, "")

        # Pattern buttons
        ttk.Label(inp, text="Feedback:").grid(row=0, column=2, sticky="e", padx=(10,4))
        self.pattern_states = ["N","P","C"]
        self.pattern_buttons = []
        for i in range(5):
            b = tk.Button(inp, text="N", width=3, relief="raised", command=lambda i=i: self._cycle_pattern(i))
            b.grid(row=0, column=3+i, padx=2)
            self.pattern_buttons.append(b)

        # Reset pattern button
        self.reset_btn = ttk.Button(inp, text="Reset Feedback", command=self._reset_pattern)
        self.reset_btn.grid(row=0, column=8, padx=(10,0))

        # Apply feedback
        controls = ttk.Frame(self, padding=(10,0,10,10))
        controls.pack(fill="x")
        self.apply_btn = ttk.Button(controls, text="Apply Feedback", command=self._apply_feedback)
        self.apply_btn.pack(side="left")
        ttk.Button(controls, text="Show Top Candidates", command=self._show_more).pack(side="left", padx=8)
        ttk.Button(controls, text="Copy All Candidates", command=self._copy_all).pack(side="left")

        # Candidates panel
        cand = ttk.LabelFrame(self, text="Candidates (up to 200 shown)", padding=10)
        cand.pack(fill="both", expand=True, padx=10, pady=(0,10))

        self.cand_var = tk.StringVar(value=[])
        self.cand_list = tk.Listbox(cand, listvariable=self.cand_var, height=12)
        self.cand_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(cand, orient="vertical", command=self.cand_list.yview)
        sb.pack(side="right", fill="y")
        self.cand_list.config(yscrollcommand=sb.set)

        # Footer
        footer = ttk.Frame(self, padding=10)
        footer.pack(fill="x")
        self.turn_var = tk.StringVar(value="Turn 1")
        ttk.Label(footer, textvariable=self.turn_var).pack(side="left")
        ttk.Label(footer, text="Legend: C = green (correct), P = yellow (present), N = gray (absent)").pack(side="right")

        self._update_candidate_list()

    # ---- UI helpers ----
    def _cycle_pattern(self, i: int):
        curr = self.pattern_buttons[i]["text"]
        idx = self.pattern_states.index(curr)
        nxt = self.pattern_states[(idx + 1) % 3]
        self.pattern_buttons[i]["text"] = nxt
        self._style_btn(self.pattern_buttons[i], nxt)

    def _reset_pattern(self):
        for b in self.pattern_buttons:
            b["text"] = "N"
            self._style_btn(b, "N")

    def _style_btn(self, btn: tk.Button, val: str):
        # Neutral colors (works across platforms)
        if val == "N":
            btn.configure(bg=self.cget("bg"))
        elif val == "P":
            btn.configure(bg="#E6D800")  # yellow-ish
        else:
            btn.configure(bg="#6AAA64")  # green-ish

    def _use_recommended(self):
        g = self.ent_guess_var.get()
        if g and g != "—":
            self.guess_entry.delete(0, tk.END)
            self.guess_entry.insert(0, g)

    def _get_pattern_string(self) -> str:
        return "".join(b["text"] for b in self.pattern_buttons)

    def _update_candidate_list(self):
        shown = self.candidates[:200]
        self.cand_var.set(shown)
        self.status_var.set(f"{len(self.candidates)} candidates remaining. Loaded {len(self.answers)} answers, {len(self.allowed)} allowed.")

    def _refresh_recommendation(self, initial=False):
        if not self.candidates:
            self.ent_guess_var.set("—")
            self.ent_bits_var.set("—")
            self.like_guess_var.set("—")
            return
        ent_g, ent_bits = best_entropy_guess(self.candidates, self.allowed)
        self.ent_guess_var.set(ent_g)
        self.ent_bits_var.set(f"{ent_bits:.2f}")
        like_g, _ = best_likelihood_guess(self.candidates)
        self.like_guess_var.set(like_g if like_g != ent_g else "—")
        if initial:
            # pre-fill first recommended guess
            self.guess_entry.delete(0, tk.END)
            self.guess_entry.insert(0, ent_g)

    def _apply_feedback(self):
        guess = self.guess_entry.get().strip().lower()
        pat = self._get_pattern_string()
        if len(guess) != 5 or set(guess) - ALPHA:
            messagebox.showerror("Invalid guess", "Guess must be a 5-letter alphabetical word.")
            return
        if len(pat) != 5 or any(ch not in "CNP" for ch in pat):
            messagebox.showerror("Invalid pattern", "Feedback must be 5 characters from {C, N, P}.")
            return

        before = len(self.candidates)
        self.candidates = filter_candidates(self.candidates, guess, pat)
        after = len(self.candidates)

        if pat == "CCCCC":
            self._update_candidate_list()
            self._refresh_recommendation()
            messagebox.showinfo("Solved", f"🎉 Solved in turn {self.turn} with '{guess.upper()}'!")
            return

        if after == 0:
            self._update_candidate_list()
            messagebox.showwarning("No candidates", "No candidates remain. Check the feedback for typos.")
            return

        self.turn += 1
        self.turn_var.set(f"Turn {self.turn}")
        self._update_candidate_list()
        self._refresh_recommendation()
        # Reset feedback for next turn
        self._reset_pattern()

    def _show_more(self):
        if not self.candidates:
            return
        top = tk.Toplevel(self)
        top.title("All Candidates (first 1000)")
        text = tk.Text(top, wrap="word", height=30, width=80)
        text.pack(fill="both", expand=True)
        text.insert("1.0", ", ".join(self.candidates[:1000]))
        text.config(state="disabled")

    def _copy_all(self):
        self.clipboard_clear()
        self.clipboard_append("\n".join(self.candidates))
        messagebox.showinfo("Copied", f"Copied {len(self.candidates)} candidate(s) to clipboard.")

def main():
    app = WordleGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
