import os
import hjson
import sys
sys.path.append('src')
from ROM import ROM
from Data import DATA, QUESTS, ITEMDATA, SHOPDATA, JOBSTATS, JOBDATA, MONSTERPARTY, MONSTERS, TREASURES, TEXT, ACTIONS, SUPPORT
from Items import shuffleItems
from Battles import shuffleResistance
from Jobs import shuffleJobAbilities, randomActionCosts
# from World import WORLD
# from gui import randomize
import random
from randomize import randomize

def main(settings):
    try:
        randomize(settings)
    except:
        print('Randomizer failed!')

if __name__=='__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python main.py settings.json')
    with open(sys.argv[1], 'r') as file:
        settings = hjson.load(file)

    main(settings)
