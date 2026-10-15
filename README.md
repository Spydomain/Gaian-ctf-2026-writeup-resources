# GaianSpace CTF 2026 — challenge resources

The numbered directories contain the challenge inputs, decoder scripts, and recovered artifacts. `challenge_prompts/` contains the recovered challenge descriptions, while `osint_sources/` holds archived public pages. `challenge_board_public.html` is a copy of the challenge board with account details removed.

Read the [GaianSpace CTF 2026 writeup on Medium](https://medium.com/@spydomain1/gaianspace-ctf-2026-how-i-worked-through-68-challenges-ba6e3decc093?sharedUserId=spydomain1).

Install [Git LFS](https://git-lfs.com/) before cloning to retrieve the SDR captures and models. The assets in `.gitattributes` are tracked with LFS. To remain within GitHub Free's 2 GB per-file limit, two GGUF models are stored as numbered 1 GiB parts; reassemble and verify them with:

```sh
cat 404/solitaire.gguf.part* > 404/solitaire.gguf
cat 405/solitaire-home.gguf.part* > 405/solitaire-home.gguf
sha256sum 404/solitaire.gguf 405/solitaire-home.gguf
```

Expected SHA-256 values:

```text
25c1be8673d74908cb874aa34285128f4c5e2affeda9a98512e00bd31abad17b  404/solitaire.gguf
dceefff3ec4e8e040f2022daf83dafdd69ca9b96cdc2f9a979d631dff968d00a  405/solitaire-home.gguf
```

The following GGUF file is **not** stored in this repository to remain under the included 10 GiB LFS storage quota. Download it to its challenge folder before running its solver:

- [`403/hpld.gguf`](https://huggingface.co/GaianSpace/ctf-2026-403/resolve/main/hpld.gguf)
