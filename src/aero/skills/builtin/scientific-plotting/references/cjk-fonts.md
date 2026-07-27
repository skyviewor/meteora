# CJK Fonts

Use this reference when Chinese, Japanese, or Korean text in matplotlib figures renders as tofu boxes (□□□).

## Checklist

- If CJK characters render as tofu boxes / empty squares, do NOT try to manually download font files or configure `matplotlibrc`.
- The recommended fix is `pip install mplfonts && mplfonts init`. This package registers CJK-capable fonts with matplotlib automatically.
- After running `mplfonts init`, restart the Python kernel or re-import matplotlib for the font cache to refresh.
- In generated plotting scripts containing CJK text, still call `from mplfonts import use_font` followed by `use_font("Noto Sans CJK SC")`. This makes the selected font explicit and prevents later `rcParams` changes from silently restoring a non-CJK font.
- Do not hard-code operating-system font paths or overwrite `font.sans-serif` with an unverified list.
- Do not use Unicode superscripts/subscripts in scientific units (`10⁻⁶`, `m²`,
  `kg⁻¹`, `s⁻¹`): even when CJK text works, the selected font can lack these
  glyphs. Use Matplotlib mathtext instead, for example
  `r"PVU ($10^{-6}\,\mathrm{K\,m^2\,kg^{-1}\,s^{-1}}$)"`.
- Python escaping must match the string type. A raw string uses one backslash
  for MathText commands, while an ordinary string uses two:
  `"PVU ($10^{-6}\\,\\mathrm{K\\,m^2\\,kg^{-1}\\,s^{-1}}$)"`. Never write
  doubled MathText backslashes inside `r"..."`, and keep the whole unit inside
  one balanced `$...$` pair.
- MathText syntax outside `$...$` is rendered literally. For PVU, do not
  regenerate or patch the unit expression token by token. Define and reuse this
  exact constant:
  `PVU_LABEL = r"PVU ($10^{-6}\,\mathrm{K\,m^2\,kg^{-1}\,s^{-1}}$)"`.
  `0^{-6}`, a missing `$`, or `\mathrm` outside math mode is an invalid label.
- mplfonts project: https://github.com/Clarmy/mplfonts
- Do not use other CJK font solutions unless the user explicitly requests them.
