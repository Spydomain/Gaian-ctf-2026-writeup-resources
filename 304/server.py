#!/usr/bin/env python3
"""304-pcb-puzzle-probe - Foundation One PCB review desk.
Answer every question from the Gerber set to receive the assessment.

The flag is not stored here in the clear: it is sealed and only unsealed once
all answers are correct, using a key derived from the answers themselves. The
accepted answers are stored as hashes, so reading this file does not hand them
over - you still have to read the board."""
import socket, threading, hashlib, random, time

# flag sealed under key = sha256("<a1>|<a2>|...|<a5>") over the canonical answers,
# in the fixed order below. unseal = xor with a sha256-counter keystream.
FLAG_ENC = bytes.fromhex("eb6db0ec34531efa33556c0025c2bb9867348c6c9e287d2217e6637a68")

# (prompt, sha256(canonical normalized answer)) - all readable in a Gerber viewer
QUESTIONS = [
    ("How many copper layers does the board have? (number only)",
     "d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35"),
    ("What is the length of the longer board edge, in mm? (number only)",
     "1a6562590ef19d1045d06c4055742d38288e9e6dcd71ccde5cee80f1d5a774eb"),
    ("What reference designator marks the 4-pad sensor footprint? (e.g. U1)",
     "6ca202c88e549dff68c09bfafbfc60b2fac074debc1e6777e9ba4b6c703ed114"),
    ("What silkscreen label marks the exposed debug header?",
     "49bf43cfff24d2e86381560fb3cb17d44a2a4f8e75a67412c5050fc204b60cc3"),
    ("How many pads does the main microcontroller U1 have? (number only)",
     "e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683"),
]

def norm(s): return s.strip().lower().replace(" ", "")

def keystream(k, n):
    out = b""; i = 0
    while len(out) < n:
        out += hashlib.sha256(k + i.to_bytes(4, "big")).digest(); i += 1
    return out[:n]

def unseal(answers_in_fixed_order):
    key = hashlib.sha256("|".join(answers_in_fixed_order).encode()).digest()
    return bytes(a ^ b for a, b in zip(FLAG_ENC, keystream(key, len(FLAG_ENC)))).decode()

def handle(conn, addr):
    try:
        conn.sendall(b"== Foundation One PCB review desk ==\r\n"
                     b"Open the Gerber set and answer each question. One connection, five questions.\r\n"
                     b"Guessing is slow on purpose. The board does not lie.\r\n\r\n")
        # ask in a random order so position cannot be learned by a scripted guesser
        order = list(range(len(QUESTIONS)))
        random.shuffle(order)
        given = [None] * len(QUESTIONS)   # collected in the FIXED order for the key
        for qi in order:
            prompt, want = QUESTIONS[qi]
            conn.sendall((prompt + "\r\n> ").encode())
            data = conn.recv(256)
            if not data:
                return
            ans = norm(data.decode(errors="ignore"))
            time.sleep(0.5)               # friction against brute-forcing
            if hashlib.sha256(ans.encode()).hexdigest() != want:
                conn.sendall(b"\r\nIncorrect. The board does not lie; check it again.\r\n")
                return
            given[qi] = ans
            conn.sendall(b"ok\r\n")
        flag = unseal(given)
        conn.sendall(("\r\nAll correct. The design is clean on review.\r\n"
                      "Flag: " + flag + "\r\n").encode())
    except Exception:
        pass
    finally:
        try: conn.shutdown(socket.SHUT_WR)
        except Exception: pass
        conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 1337)); s.listen(16)
    print("304 PCB review desk listening on 0.0.0.0:1337")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
