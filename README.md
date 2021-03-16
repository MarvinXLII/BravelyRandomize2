## ABOUT

This is the beginnings of a randomizer for Bravely Default II. It's code only for the foreseeable future.

Play this at your own risk. I bear no responsibility if anything goes
wrong hacking your Switch, etc.

## USAGE

You'll have to run this from the command line. First, install various
libraries: `hashlib`, `zlib`, `zstandard`, `struct`, and
`hjson`. Modify `settings.json` as desired and run

```
python main.py settings.json
```

Copy the output pak file to the appropriate location on your SD card (e.g. `atmosphere/contents/titleID/romfs/Sunrise-E/Content/Paks`).