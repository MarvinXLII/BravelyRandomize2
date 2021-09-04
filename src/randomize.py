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
import hjson

class MOD:
    def __init__(self, rom, settings):
        self.settings = settings

        # Outputs
        self.outPath = f"seed_{self.settings['seed']}"
        if os.path.isdir(self.outPath):
            shutil.rmtree(self.outPath)
        os.makedirs(self.outPath)

        # Load ROM
        self.rom = rom

        # Text files
        self.actionText = TEXT(self.rom, 'L10N/en/DataAsset/Ability/Player/ActionAbilityTextAsset')
        self.supportText = TEXT(self.rom, 'L10N/en/DataAsset/Ability/Player/SupportAbilityTextAsset')
        self.specialText = TEXT(self.rom, 'L10N/en/DataAsset/Ability/Player/SpecialAbilityTextAsset')
        self.itemText = TEXT(self.rom, 'L10N/en/DataAsset/Item/ItemTextAsset')
        self.monsterText = TEXT(self.rom, 'L10N/en/DataAsset/Monster/MonsterTextDataAsset')

        # Assets
        self.support = SUPPORT(self.rom, self.supportText)
        self.actions = ACTIONS(self.rom, self.actionText)
        self.shops = SHOPDATA(self.rom, self.itemText)
        self.items = ITEMDATA(self.rom, self.itemText)
        self.jobstats = JOBSTATS(self.rom)
        self.jobdata = JOBDATA(self.rom, self.actions, self.support)
        self.monsterParty = MONSTERPARTY(self.rom)
        self.monsters = MONSTERS(self.rom, self.monsterText, self.itemText, self.monsterParty)
        self.treasures = TREASURES(self.rom, self.itemText)
        self.quests = QUESTS(self.rom, self.itemText)

    def failed(self):
        print(f"Randomizer failed! Removing directory {self.outPath}.")
        shutil.rmtree(self.outPath)

    def randomize(self):
        ### STATS
        if self.settings['job-stats']:
            random.seed(self.settings['seed'])
            if self.settings['job-stats-option'] == 'swap':
                self.jobstats.shuffleStats()
            elif self.settings['job-stats-option'] == 'random':
                self.jobstats.randomStats()
            else:
                sys.exit(f"{self.settings['job-stats-option']} is not a valid option for job stats")

        ### AFFINITIES
        if self.settings['job-affinities']:
            random.seed(self.settings['seed']*2)
            if self.settings['job-affinities-option'] == 'swap':
                self.jobstats.shuffleAffinities()
            elif self.settings['job-affinities-option'] == 'random':
                self.jobstats.randomAffinities()
            else:
                sys.exit(f"{self.settings['job-affinities-option']} is not a valid option for job affinities")

        # Job skills
        if self.settings['job-abilities']:
            count = 1
            random.seed(self.settings['seed']*3)
            if 'late-godspeed-strike' in self.settings:
                lategodspeedstrike = self.settings['late-godspeed-strike']
            else:
                lategodspeedstrike = False
            while not shuffleJobAbilities(self.jobdata, lategodspeedstrike):
                count += 1
            if count == 1:
                print("Shuffling abilities took ", count, " attempt!")
            else:
                print("Shuffling abilities took ", count, " attempts!")

        # Job skill costs
        if self.settings['job-costs']:
            random.seed(self.settings['seed']*4)
            randomActionCosts(self.jobdata)

        ### ITEM SHUFFLER
        if self.settings['items']:
            random.seed(self.settings['seed']*5)
            shuffleItems(self.treasures, self.quests, self.monsters)

        ### RESISTANCE SHUFFLER
        if self.settings['resistance']:
            random.seed(self.settings['seed']*6)
            shuffleResistance(self.monsters)


    def qualityOfLife(self):
        self.monsters.scaleEXP(int(self.settings['qol-scale-exp']))
        self.monsters.scaleJP(int(self.settings['qol-scale-jp']))
        self.monsters.scalePG(int(self.settings['qol-scale-pg']))
        
        # ITEM COSTS
        if self.settings['teleport-stone-costs']:
            self.items.zeroCost('Teleport Stone')
        if self.settings['magnifying-glass-costs']:
            self.items.zeroCost('Magnifying Glass')

        # ITEM AVAILABILITY
        if self.settings['early-access']:
            self.shops.earlyAccess('Hi-Potion')
            self.shops.earlyAccess('Ether')

    def _spoilerLog(self):
        self.monsters.spoilers(os.path.join(self.outPath, 'spoilers_monsters.log'))
        self.quests.spoilers(os.path.join(self.outPath, 'spoilers_quests.log'))
        self.treasures.spoilers(os.path.join(self.outPath, 'spoilers_treasures.log'))
        self.jobdata.spoilers(os.path.join(self.outPath, 'spoilers_jobs.log'))
        self.jobstats.spoilers_stats(os.path.join(self.outPath, 'spoilers_stats.log'))
        self.jobstats.spoilers_affinities(os.path.join(self.outPath, 'spoilers_affinities.log'))

    def dump(self, fileName):
        ### UPDATE SHUFFLED TABLES
        self.shops.update()
        self.items.update()
        self.jobstats.update()
        self.jobdata.update()
        self.monsters.update()
        self.treasures.update()
        self.quests.update()
        self.actions.update()
        self.support.update()

        # Dump pak
        self.rom.buildPak(fileName)

        # Print spoiler logs
        self._spoilerLog()
        
        # Print settings
        with open(os.path.join(self.outPath, 'settings.json'), 'w') as file:
            hjson.dump(self.settings, file)


class STEAM(MOD):
    def __init__(self, rom, settings):
        super(STEAM, self).__init__(rom, settings)

    def dump(self):
        pakName = os.path.join(self.outPath, 'random_P.pak')
        super(STEAM, self).dump(pakName)


class SWITCH(MOD):
    def __init__(self, rom, settings):
        super(SWITCH, self).__init__(rom, settings)

    def dump(self):
        pakPath = os.path.join(self.outPath, '01006DC010326000', 'romfs', 'Sunrise-E', 'Content', 'Paks')
        os.makedirs(pakPath)
        pakName = os.path.join(pakPath, 'Sunrise-E-Switch_2_P.pak')
        super(SWITCH, self).dump(pakName)
