WORD LIST FOR HANGMAN AND WORDLE (optional)
===========================================

Games 57 (Hangman) and 58 (Wordle) read /data/words.txt on the PyGamer drive. Without it they use a
built-in list of about 60 words, so both games always work.

Build   cd tools ; python make_words.py        (no downloads, no packages)
        -> out\words.txt: about 2,500 common words (3-10 letters, ~1,380 of them five letters), one
           lower-case word per line, sorted. Add your own words to EXTRA_WORDS in the script and rerun.
Install 1. PyGamer: Settings > USB drive.
        2. PC: powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Words   (add -Drive E: if needed)
        3. EJECT the drive, press B on the PyGamer. The list is read each time a new word is picked.
File    plain text, ASCII, one word per line; only a-z words of 3-15 letters are used (anything else on a
        line skips that line). Wordle uses 5-letter words, Hangman 4-10 letters depending on the mode.
        Wordle accepts any 5 letters as a guess (the list is for the secret word only).
Other new games (Sudoku mini, Nonogram, Missile Command, Pipe Link) need no files.
