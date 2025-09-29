# TextEditor (Python/Tkinter)

Jednostavan tekstualni editor u Pythonu s Tkinterom. Implementira model–view–observer pristup, undo/redo mehanizam, selekciju, interni “clipboard” stog i dinamičke dodatke (plugins).

## Značajke
- Uređivanje teksta monospaced fontom na Canvas prikazu
- Selekcija s vizualnim isticanjem
- Undo/Redo (umetanje, brisanje znaka, brisanje raspona)
- Interni clipboard: Cut, Copy, Paste, Paste and Take
- Učitavanje/spremanje tekstualnih datoteka
- Izbornici, alatna traka, statusna traka
- Dinamičko učitavanje pluginova iz `plugins/`

## Zahtjevi
- Python 3.10+
- Tkinter (na Linuxu po potrebi instalirati `python3-tk`)

## Pokretanje
1. Spremite projekt (npr. `text_editor.py` + opcionalno mapu `plugins/`).
2. Pokrenite: `python text_editor.py`.

## Korištenje
- Tipkanjem se umeću znakovi na poziciji kursora.
- Selekcija se širi pomoću Shift + strelice.
- Enter umeće novi red.
- Delete/Backspace brišu znak ili aktivnu selekciju.
- U izborniku **File** otvorite ili spremite dokument.
- U **Edit** koristite Undo/Redo, Cut/Copy/Paste, brisanje selekcije, čišćenje dokumenta.
- U **Move** pomaknite kursor na početak/kraj dokumenta.

## Tipkovnički prečaci
- Ctrl+Z (Undo), Ctrl+Y (Redo)
- Ctrl+C (Copy), Ctrl+X (Cut), Ctrl+V (Paste), Ctrl+Shift+V (Paste and Take)
- Strelice za kretanje, Shift+Strelice za selekciju, Enter za novi red
- Delete/Backspace za brisanje

## Pluginovi
- Svaka `.py` datoteka u `plugins/` koja izlaže sučelje `getName`, `getDescription`, `execute(model, undoManager, clipboardStack)` automatski se učitava i pojavljuje u izborniku **Plugins**.

## Arhitektura (sažeto)
- `TextEditorModel`: linije teksta, lokacija kursora, raspon selekcije, operacije uređivanja, obavještavanje promatrača.
- `TextEditor` (Canvas): renderiranje teksta/kursora/selektiranog područja, rukovanje tipkovnicom, izbornici, alatna i statusna traka.
- `UndoManager` + akcije uređivanja: upravljanje undo/redo stogovima.
- `ClipboardStack`: interni stog tekstualnih isječaka.

## Ograničenja
- Nema word-wrapa; performanse padaju na vrlo velikim datotekama.
- Clipboard je interni (ne koristi OS međuspremnik).
- Pluginovi se učitavaju bez sandboxinga.


