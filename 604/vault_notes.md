# Vault lock — field notes

The survey vault is a standard AES-encrypted 7z archive (headers encrypted too, so
even the file list is sealed until the passphrase is right).

What the field team let slip about the passphrase:

- exactly five characters
- all lowercase letters, a-z
- not a dictionary word (they "mash the keyboard" each sortie)

So: no wordlist, no rules — a mask over the full five-letter lowercase space.

Recovering the crackable hash from the archive and running the mask:

    7z2john mission_vault.7z > vault.hash
    hashcat -m 11600 -a 3 vault.hash ?l?l?l?l?l
    # or:  john --format=7z --mask='?l?l?l?l?l' vault.hash

This is deliberately a grind. Budget a few hours on a normal multi-core desktop.
Once the passphrase falls out, open the archive and read `ice_site.txt`.
