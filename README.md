# MHTifier 2
Un/packs a MHT (MHTML) archive into/from separate files, writing/reading them
in directories to match their Content-Location.

A fork from [Modified/MHTifier](https://github.com/Modified/MHTifier).

Under development, so no public API should be assumed.

## Known Issues
1. Cleanest would've been to use stdin/out, but turned out inconvenient,
annoying even, so added command line options.
2. Verify index.html is present!?
3. A few un/Pythonisms, idioms,I guess.
4. Rewrite whole program to provide stable public APIs. Preferably, keep it as
a single file with no dependency other than Python 3 and its standard libraries.
