import os
import hjson
import sys
import glob
sys.path.append('src')
from gui import randomize
from ROM import ROM_SWITCH, ROM_PC

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
            rom = ROM_SWITCH(pak)
            break
        elif os.path.basename(pak) == 'Bravely_Default_II-WindowsNoEditor.pak':
            settings['system'] = 'Steam'
            rom = ROM_PC(pak)
            break

    if 'system' not in settings:
        sys.exit('System neither specified nor found in pak.')

    randomize(rom, settings)
