import os
import hjson
import sys
import glob
sys.path.append('src')
from gui import randomize
from ROM import ROM

if __name__=='__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python main.py settings.json')
    with open(sys.argv[1], 'r') as file:
        settings = hjson.load(file)

    # Get pak files from selected directory
    filenames = glob.glob(settings['rom'] + '/**/*.pak', recursive=True)
    for pak in filenames:
        if os.path.basename(pak) == 'Sunrise-E-Switch.pak':
            settings['system'] = 'Switch'
            break

    if 'system' not in settings:
        sys.exit('System neither specified nor found in pak.')

    rom = ROM(pak)
    randomize(rom, settings)
