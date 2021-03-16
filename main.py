import os
import hjson
import sys
sys.path.append('src')
from ROM import ROM
from Data import DATA, JOBS, JOBDATA, MONSTERS, TREASURES, TEXT
# from World import WORLD
# from gui import randomize

def main(settings):
    # Load ROM
    pak = settings['rom']
    rom = ROM(pak)

    ### TEXT FILES
    actionText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/ActionAbilityTextAsset')
    supportText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/SupportAbilityTextAsset')
    specialText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/SpecialAbilityTextAsset')
    itemText = TEXT(rom, 'L10N/en/DataAsset/Item/ItemTextAsset')
    locationText = TEXT(rom, 'L10N/en/DataAsset/Field/LocationTextDataAsset')

    ### ASSETS
    job = JOBS(rom)
    jobdata = JOBDATA(rom)
    monsters = MONSTERS(rom)
    treasures = TREASURES(rom, itemText, locationText)
    treasures.print('treasures.csv')

    ### STATS
    if settings['job-stats'] == 'swap':
        job.shuffleStats()
    elif settings['job-stats'] == 'random':
        job.randomStats()
    else:
        print('Skipping the job stats randomizer.')

    ### SKILLS AND ABILITIES
    if settings['job-abilities'] == 'separately':
        jobdata.shuffleSupport()
        jobdata.shuffleSkills()
    elif settings['job-abilities'] == 'all':
        jobdata.shuffleAll()
    else:
        print('Skipping the action and support ability randomizer.')

    ### JOB TRAITS
    if settings['job-traits']:
        jobdata.shuffleTraits()
    else:
        print('Skipping the job traits randomizer.')

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
    job.update()
    jobdata.update()
    monsters.update()
    actionText.update()
    supportText.update()
    specialText.update()
    itemText.update()
    treasures.update()

    # Dump pak
    rom.buildPak('Sunrise-E-Switch_2_P.pak')
    print('Done!')


if __name__=='__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python main.py settings.json')
    with open(sys.argv[1], 'r') as file:
        settings = hjson.load(file)

    main(settings)
