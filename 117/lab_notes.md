# AO-111 lander — onboard lab, run 1

AsterOre Inc. The lander carries a small chemistry lab for checking the metal. Nobody expected it to be used for anything else.

## What went in the oven

- During touchdown the anchor broke through a thin dark streak on the metal patch. The camera says the streak is not from `2041 QM23`. It matches the colour of the small dark moonlet that orbits it. Binary rocks swap dust. The sampler took a scoop.
- Hot-water extract, hydrolysed, derivatized (TFA / isopropyl esters), one injection on the chiral column. Results in `moonlet_sample.csv`.
- Before launch, the same lab ran a procedural blank in the clean room: same steps, no rock. Results in `procedural_blank.csv`. Whatever the blank sees came from us.
- A separate injection went to the isotope-ratio line. Results per peak in `isotopes.csv`.

## How the lab reports

- Each peak has a total ion area and the areas of a few selected ions.
- The reference run of known compounds on the same column is `standards.csv`. Each compound is measured on its own quant ion. Peaks within about 0.03 min of a standard are that compound.
- Enantiomeric excess, for whoever asks: ee = (L − D) / (L + D) × 100, from the quant-ion areas.
- Isotopes: life on Earth sits around δ13C −20 to −30 ‰ and δ15N 0 to +10 ‰. Organics made in space come out strongly heavy in both.

## Desk

- Kaito: "Left-handed alanine. That's biology. Those are ALIENS. Call the press."
- Sunniva: "It's not aliens. Nobody calls anyone."
- Kaito: "It's a little bit aliens."
- Sunniva: "Then show me which molecule, and how left-handed, and prove it didn't come off our gloves."
