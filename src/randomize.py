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
    if settings['job-stats']:
        random.seed(settings['seed'])
        if settings['job-stats-option'] == 'swap':
            jobstats.shuffleStats()
        elif settings['job-stats-option'] == 'random':
            jobstats.randomStats()
        else:
            sys.exit(f"{settings['job-stats-option']} is not a valid option for job stats")

    ### AFFINITIES
    if settings['job-affinities']:
        random.seed(settings['seed'])
        if settings['job-affinities-option'] == 'swap':
            jobstats.shuffleAffinities()
        elif settings['job-affinities-option'] == 'random':
            jobstats.randomAffinities()
        else:
            sys.exit(f"{settings['job-affinities-option']} is not a valid option for job affinities")

    # Job skills
    if settings['job-abilities']:
        count = 1
        random.seed(settings['seed'])
        while not shuffleJobAbilities(jobdata, settings['late-godspeed-strike']):
            count += 1
        if count == 1:
            print("Shuffling abilities took ", count, " attempt!")
        else:
            print("Shuffling abilities took ", count, " attempts!")

    # Job skill costs
    if settings['job-costs']:
        random.seed(settings['seed'])
        randomActionCosts(jobdata)

    ### ITEM SHUFFLER
    if settings['items']:
        random.seed(settings['seed'])
        shuffleItems(treasures, quests, monsters)

    ### RESISTANCE SHUFFLER
    if settings['resistance']:
        random.seed(settings['seed'])
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
    jobstats.spoilers_stats(os.path.join(outdir, 'spoilers_stats.log'))
    jobstats.spoilers_affinities(os.path.join(outdir, 'spoilers_affinities.log'))

    return True
