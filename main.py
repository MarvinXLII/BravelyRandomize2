import os
import hjson
import sys
sys.path.append('src')
from ROM import ROM
from Data import DATA, QUESTS, JOBSTATS, JOBDATA, MONSTERPARTY, MONSTERS, TREASURES, TEXT, FLAGS, ACTIONS, SUPPORT
from Items import shuffleItems
from Battles import shuffleResistance
from Jobs import shuffleJobAbilities
# from World import WORLD
# from gui import randomize
import random

def main(settings):
    # Set seed
    random.seed(settings['seed'])
    
    # Load ROM
    pak = settings['rom']
    rom = ROM(pak)

    flags = FLAGS(rom)

    ### TEXT FILES
    actionText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/ActionAbilityTextAsset')
    supportText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/SupportAbilityTextAsset')
    specialText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/SpecialAbilityTextAsset')
    itemText = TEXT(rom, 'L10N/en/DataAsset/Item/ItemTextAsset')
    locationText = TEXT(rom, 'L10N/en/DataAsset/Field/LocationTextDataAsset')
    monsterText = TEXT(rom, 'L10N/en/DataAsset/Monster/MonsterTextDataAsset')

    ### ASSETS
    jobstats = JOBSTATS(rom)
    jobdata = JOBDATA(rom, actionText, supportText)
    monsterParty = MONSTERPARTY(rom)
    monsters = MONSTERS(rom, monsterText, itemText, monsterParty)
    treasures = TREASURES(rom, itemText, locationText)
    quests = QUESTS(rom, itemText, locationText)
    actions = ACTIONS(rom, actionText)
    support = SUPPORT(rom, supportText)

    ### STATS
    if settings['job-stats'] == 'swap':
        jobstats.shuffleStats()
    elif settings['job-stats'] == 'random':
        jobstats.randomStats()
    else:
        print('Skipping the job stats randomizer.')

    ### SKILLS AND ABILITIES
    # if settings['job-abilities'] == 'separately':
    #     jobdata.shuffleSupport()
    #     jobdata.shuffleSkills()
    # elif settings['job-abilities'] == 'all':
    #     jobdata.shuffleAll()
    # else:
    #     print('Skipping the action and support ability randomizer.')

    ### JOB TRAITS
    # if settings['job-traits']:
    #     jobdata.shuffleTraits()
    # else:
    #     print('Skipping the job traits randomizer.')
    if settings['job-abilities'] == 'all':
        count = 0
        while not shuffleJobAbilities(jobdata):
            count += 1
        print("Shuffling abilities took ", count, " attempts!")

    ### ITEM SHUFFLER
    if settings['items']:
        shuffleItems(treasures, quests, monsters)

    ### RESISTANCE SHUFFLER
    if settings['resistance']:
        shuffleResistance(monsters, settings['resistance-boss-separately'])

    ### QOL
    try:
        print('Scaling EXP, JP and pg')
        monsters.scaleEXP(int(settings['qol-scale-exp']))
        monsters.scaleJP(int(settings['qol-scale-jp']))
        monsters.scalePG(int(settings['qol-scale-pg']))
    except:
        print('Scales must be numbers!')
        sys.exit('Terminating program!')

    ### UPDATE SHUFFLED TABLES
    jobstats.update()
    jobdata.update()
    monsters.update()
    actionText.update()
    supportText.update()
    specialText.update()
    itemText.update()
    treasures.update()
    quests.update()
    actions.update()
    support.update()

    ## TESTING
    flags.update()

    # Dump pak
    rom.buildPak('Sunrise-E-Switch_2_P.pak')
    print('Done!')

    # Print spoilers
    monsters.spoilers('spoilers_monsters.log')
    quests.spoilers('spoilers_quests.log')
    treasures.spoilers('spoilers_treasures.log')


if __name__=='__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python main.py settings.json')
    with open(sys.argv[1], 'r') as file:
        settings = hjson.load(file)

    main(settings)
