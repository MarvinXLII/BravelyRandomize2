import sys
sys.path.append('src')
from ROM import ROM
from Data import DATA, QUESTS, ITEMDATA, SHOPDATA, JOBSTATS, JOBDATA, MONSTERPARTY, MONSTERS, TREASURES, TEXT, ACTIONS, SUPPORT
from Items import shuffleItems
from Battles import shuffleResistance
from Jobs import shuffleJobAbilities, randomActionCosts
import random
import os
import shutil

def randomize(settings):

    # Set seed
    random.seed(settings['seed'])
    
    # Load ROM
    rom = ROM(settings['rom'])

    ### TEXT FILES
    actionText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/ActionAbilityTextAsset')
    supportText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/SupportAbilityTextAsset')
    specialText = TEXT(rom, 'L10N/en/DataAsset/Ability/Player/SpecialAbilityTextAsset')
    itemText = TEXT(rom, 'L10N/en/DataAsset/Item/ItemTextAsset')
    monsterText = TEXT(rom, 'L10N/en/DataAsset/Monster/MonsterTextDataAsset')

    ### ASSETS
    support = SUPPORT(rom, supportText)
    actions = ACTIONS(rom, actionText)
    shops = SHOPDATA(rom, itemText)
    items = ITEMDATA(rom, itemText)
    jobstats = JOBSTATS(rom)
    jobdata = JOBDATA(rom, actions, support)
    monsterParty = MONSTERPARTY(rom)
    monsters = MONSTERS(rom, monsterText, itemText, monsterParty)
    treasures = TREASURES(rom, itemText)
    quests = QUESTS(rom, itemText)

    ### STATS
    if settings['job-stats'] == 'swap':
        jobstats.shuffleStats()
    elif settings['job-stats'] == 'random':
        jobstats.randomStats()

    # Job skills
    if settings['job-abilities']:
        count = 0
        while not shuffleJobAbilities(jobdata, settings['late-godspeed-strike']):
            count += 1
        print("Shuffling abilities took ", count, " attempts!")

    # Job skill costs
    if settings['job-costs']:
        randomActionCosts(jobdata)

    ### ITEM SHUFFLER
    if settings['items']:
        shuffleItems(treasures, quests, monsters)

    ### RESISTANCE SHUFFLER
    if settings['resistance']:
        shuffleResistance(monsters)

    ### QOL
    monsters.scaleEXP(int(settings['qol-scale-exp']))
    monsters.scaleJP(int(settings['qol-scale-jp']))
    monsters.scalePG(int(settings['qol-scale-pg']))

    # ITEM COSTS
    if settings['teleport-stone-costs']:
        items.zeroCost('Teleport Stone')
    if settings['magnifying-glass-costs']:
        items.zeroCost('Magnifying Glass')

    # ITEM AVAILABILITY
    if settings['early-access']:
        shops.earlyAccess('Hi-Potion')
        shops.earlyAccess('Ether')

    ### UPDATE SHUFFLED TABLES
    shops.update()
    items.update()
    jobstats.update()
    jobdata.update()
    monsters.update()
    treasures.update()
    quests.update()
    actions.update()
    support.update()

    outdir = f"seed_{settings['seed']}"
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    else:
        shutil.rmtree(outdir)
    
    # Dump pak
    fileName = os.path.join(outdir, '01006DC010326000', 'romfs', 'Sunrise-E', 'Content', 'Paks', 'Sunrise-E-Switch_2_P.pak')
    dirName = os.path.dirname(fileName)
    os.makedirs(dirName)
    rom.buildPak(fileName)

    # Print spoilers
    monsters.spoilers(os.path.join(outdir, 'spoilers_monsters.log'))
    quests.spoilers(os.path.join(outdir, 'spoilers_quests.log'))
    treasures.spoilers(os.path.join(outdir, 'spoilers_treasures.log'))
    jobdata.spoilers(os.path.join(outdir, 'spoilers_jobs.log'))

    return True
