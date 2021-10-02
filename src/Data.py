from dataclasses import dataclass, field
import hjson
import sys
import random
import struct
import io
from Classes import DATA
from ClassData import ITEMASSET, ACTIONSKILL, SUPPORTSKILL, ITEM, ITEMENEMY, CHEST, QUESTREWARD, DROP, STEAL, MAGIC, WEAPONS, EFFECTS, JOB, STATS, AFFINITY, BOSSAI
from Utilities import get_filename
from copy import deepcopy


jobNames= {
    'EJobEnum::JE_Sobriety': 'Freelancer',
    'EJobEnum::JE_Black_Mage': 'Black Mage',
    'EJobEnum::JE_White_Mage': 'White Mage',
    'EJobEnum::JE_Vanguard': 'Vanguard',
    'EJobEnum::JE_Monk': 'Monk',
    'EJobEnum::JE_Troubadour': 'Bard',
    'EJobEnum::JE_Tamer': 'Beastmaster',
    'EJobEnum::JE_Thief': 'Thief',
    'EJobEnum::JE_Gambler': 'Gambler',
    'EJobEnum::JE_Berzerk': 'Berserker',
    'EJobEnum::JE_Red_Mage': 'Red Mage',
    'EJobEnum::JE_Hunter': 'Ranger',
    'EJobEnum::JE_Shield_Master': 'Shieldmaster',
    'EJobEnum::JE_Pictomancer': 'Pictomancer',
    'EJobEnum::JE_Dragoon_Warrior': 'Dragoon',
    'EJobEnum::JE_Master': 'Spiritmaster',
    'EJobEnum::JE_Sword_Master': 'Swordmaster',
    'EJobEnum::JE_Oracle': 'Oracle',
    'EJobEnum::JE_Doctor': 'Salve-Maker',
    'EJobEnum::JE_Demon': 'Arcanist',
    'EJobEnum::JE_Judgement': 'Bastion',
    'EJobEnum::JE_Phantom': 'Phantom',
    'EJobEnum::JE_Cursed_Sword': 'Hellblade',
    'EJobEnum::JE_Brave': 'Bravebearer',
}

class ITEMDATA(DATA):
    def __init__(self, rom, text):
        super().__init__(rom, 'ItemDataAsset')
        self.data = self.table['ConsumeItemDataMap']['data']
        self.text = text

        self.items = {}
        for Id, item in self.data.items():
            name = self.text.getName(Id)
            if not name:
                continue
            if name in self.items:
                print('Repeated name!')
                sys.exit()
            self.items[name] = ITEMASSET(
                Id,
                name,
                item['PurchasePrice'].value,
                item['SellingPrice'].value,
            )

    def zeroCost(self, name):
        self.items[name].PurchasePrice = 0
        self.items[name].SellingPrice = 0

    def update(self):
        for item in self.items.values():
            self.data[item.Id]['PurchasePrice'].value = item.PurchasePrice
            self.data[item.Id]['SellingPrice'].value = item.SellingPrice
        super().update()


class SHOPDATA:
    def __init__(self, rom, text):
        # Currently limited only to shops with hi-potions and ethers
        self.indices = ['001', '101', '111', '121', '131', '141', '151', '201']
        self.data = {}
        self.shops = {}
        for index in self.indices:
            fileName = f'ShopSalesListDataAsset_{index}'
            self.data[index] = DATA(rom, fileName)
            self.shops[index] = {}
            for item in self.data[index].table['ShopSalesListDataMap']['data'].values():
                name = text.getName(item['ItemId'].value)
                if name is None:
                    continue
                self.shops[index][name] = item

    def earlyAccess(self, name):
        for shop in self.shops.values():
            if name in shop:
                shop[name]['Progress'].value = 0

    def update(self):
        for data in self.data.values():
            data.update()


class TIPPING(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'L10N/en/DataAsset/TipsDataAsset')
        self.tips = DATA(self.rom, 'L10N/en/DataAsset/TipsDataAsset')
        self.data = self.table['Tips']['data'].array

    def update(self):
        # Allow all "tips" to be used at any time
        for entry in self.data:
            entry['MinMainProgress'].value = 1

        # Make "tip" display at the start of a new game
        # NB: At least 2 must be accessible for anything to show!!!
        for entry in self.data[:2]:
            entry['Text'].string = '* Randomizing... *'
            entry['MinMainProgress'].value = 0
            entry['MaxMainProgress'].value = 1

        # Demo of overwriting tips with quotes
        # Maybe use for credits for testers?
        quotes = [
            "Mrgrgrgr!",
            "Unacceptable!",
            "Whaaaat!?",
            "Not fashionable! FASHIONAAABLUH!",
            "Coup de gravy!",
            "You're my hope.",
            "The courage to try again.",
            "Oh, hello. I see fire in those eyes! How do I put it?\nThey've a strong sense of duty. Like whatever you start, you'll always see through, no matter what!",
            "Iwon'tbecalledimprudentbyaflounderingfoollikeyou.",
            "It's time to bust some Ba'als!",
        ]
        entries = random.sample(self.data[2:], len(quotes) + 2)
        while quotes:
            entry = entries.pop()
            entry['Text'].string = f"* Quotes *\n{quotes.pop()}"

        # Just for fun
        while entries:
            entry = entries.pop()
            entry['Text'].string = entry['Text'].string[::-1]

        super().update()


class ACTIONS(DATA):
    def __init__(self, rom, text):
        super().__init__(rom, 'ActionAbilityAsset')
        self.data = self.table['ActionAbilityDataMap']['data']        
        self.text = text # Might need to update descriptions at some point!

        self.skills = {}
        for Id, skill in self.data.items():
            name = self.text.getName(Id)
            if not name:
                continue
            description = self.text.getDescription(Id)
            self.skills[Id] = ACTIONSKILL(
                Id,
                skill['JobId'].value,
                skill['Cost'].value,
                skill['CostValue'].value,
                skill['CostType'].value,
                name,
                description,
            )

    def update(self):
        for Id, skill in self.skills.items():
            self.data[Id]['JobId'].value = skill.Job
            self.data[Id]['Cost'].value = skill.Cost
            self.data[Id]['CostValue'].value = skill.CostValue
            self.data[Id]['CostType'].value = skill.CostType
        super().update()


class SUPPORT(DATA):
    def __init__(self, rom, text):
        super().__init__(rom, 'SupportAbilityAsset')
        self.data = self.table['SupportAbilityDataMap']['data']
        self.text = text
        self.skills = {}
        for Id, skill in self.data.items():
            name = self.text.getName(Id)
            if not name:
                continue
            description = self.text.getDescription(Id)
            self.skills[Id] = SUPPORTSKILL(
                Id,
                skill['AbilityCost'].value,
                name,
                description,
            )

    def update(self):
        for Id, skill in self.skills.items():
            self.data[Id]['AbilityCost'].value = skill.Cost
        super().update()
        

class JOBDATA:
    def __init__(self, rom, actions, support):
        self.assets = DATA(rom, 'JobDataAsset')
        self.assetsTable = self.assets.table['JobDataMap']['data']
        self.actionsDict = {}
        self.supportDict = {}

        self.jobs = []
        for name, data in self.assetsTable.items():

            a = [None]*15
            for i, skill in enumerate(data['ActionAbilityArray'].array):
                if skill > 0:
                    a[i] = actions.skills[skill]
                    self.actionsDict[a[i].Id] = a[i]
            
            s = [None]*15
            for i, skill in enumerate(data['SupportAbilityArray'].array):
                if skill > 0:
                    s[i] = support.skills[skill]
                    self.supportDict[s[i].Id] = s[i]

            trait1 = support.skills[data['JobTraitId1'].value]
            trait2 = support.skills[data['JobTraitId2'].value]
            self.supportDict[trait1.Id] = trait1
            self.supportDict[trait2.Id] = trait2

            job = JOB(Name=name)
            job.setActions(a)
            job.setSupport(s)
            job.setTrait1(trait1)
            job.setTrait2(trait2)
            self.jobs.append(job)

        # Store for easy skill id lookup
        self.nameToId = {}
        for skill in self.actionsDict.values():
            self.nameToId[skill.Name] = skill.Id
        for skill in self.supportDict.values():
            self.nameToId[skill.Name] = skill.Id

    def update(self):
        for job in self.jobs:
            data = self.assetsTable[job.Name]
            data['ActionAbilityArray'].array = job.getActions()
            data['SupportAbilityArray'].array = job.getSupport()
            data['JobTraitId1'].value = job.getTrait1()
            data['JobTraitId2'].value = job.getTrait2()
        self.assets.update()

    def getIds(self, names):
        return [self.nameToId[n] for n in names]

    def pickIds(self, num, names):
        assert num <= len(names)
        count = random.randint(num, len(names))
        return [self.nameToId[n] for n in random.sample(names, count)]

    def pickGroup(self, groups):
        group = random.sample(groups, 1)[0]
        return self.getActionIds(*group)

    def spoilers(self, filename):
        jobs = {job.Name:job for job in self.jobs}
        with open(filename, 'w') as sys.stdout:
            print('')
            print('')
            for key, name in jobNames.items():
                job = jobs[key]
                print(name)
                print('-'*len(name))
                print('')
                for action, support in zip(job.Actions, job.Support):
                    if action:
                        a, c = action.getString()
                        print('   ', a.ljust(40, ' '), c)
                    else:
                        s, c = support.getString()
                        print('   ', s.ljust(40, ' '), c)
                print('')
                t, c = job.getTrait1Obj().getString()
                print('    Trait 1: ', t.ljust(30, ' '), c)
                t, c = job.getTrait2Obj().getString()
                print('    Trait 2: ', t.ljust(30, ' '), c)
                print('')
        
        sys.stdout = sys.__stdout__

    
        

class JOBSTATS(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'JobCorrectionAsset')
        self.data = self.table['JobLevelMap']['data']

        self.stats = {}
        self.affinities = {}
        for k, d in self.data.items():
            self.stats[k] = STATS(
                d['HP'],
                d['MP'],
                d['Weight'],
                d['PhysicalAttack'],
                d['PhysicalDefence'],
                d['MagicAttack'],
                d['MagicDefence'],
                d['Heal'],
                d['Speed'],
                d['Accuracy'],
                d['Evasion'],
                d['Critical'],
                d['Aggro'],
            )
            self.affinities[k] = AFFINITY(
                d['BareHand'],
                d['ShortSword'],
                d['Sword'],
                d['Axe'],
                d['Spear'],
                d['Bow'],
                d['Staff'],
                d['Shield'],
            )

    def _shuffle(self, dic):
        jobs = list(dic.keys())
        for i,ji in enumerate(dic.keys()):
            jk = random.choices(jobs[i:])[0]
            dic[ji], dic[jk] = dic[jk], dic[ji]

    def _random(self, dic):
        jobs = list(dic.keys())
        for i,ji in enumerate(dic.keys()):
            for attr in dic[ji].__dict__.keys():
                jk = random.choices(jobs[i:])[0]
                vi, vk = getattr(dic[ji], attr), getattr(dic[jk], attr)
                setattr(dic[ji], attr, vk)
                setattr(dic[jk], attr, vi)

    def shuffleStats(self):
        self._shuffle(self.stats)

    def randomStats(self):
        self._random(self.stats)

    def shuffleAffinities(self):
        self._shuffle(self.affinities)

    def randomAffinities(self):
        self._random(self.affinities)

    def update(self):

        for job, stats in self.stats.items():
            for attr, value in stats.__dict__.items():
                self.data[job][attr] = value

        for job, stats in self.affinities.items():
            for attr, value in stats.__dict__.items():
                self.data[job][attr] = value

        super().update()

    def spoilers_stats(self, filename):
        k = ['HP', 'MP', 'Wt', 'PAtk', 'PDef', 'MAtk', 'MDef', 'Heal', 'Spd', 'Acc', 'Eva', 'Crit', 'Aggr']
        k = list(map(lambda x: x.rjust(5, ' '), k))
        with open(filename, 'w') as sys.stdout:
            print('')
            print('')
            print(' '*20, *k)
            for key, name in jobNames.items():
                stats = self.stats[key]
                values = stats.getValues()
                values = list(map(lambda x: x.rjust(5, ' '), stats.getValues()))
                print(name.ljust(20, ' '), *values)

        sys.stdout = sys.__stdout__

    def spoilers_affinities(self, filename):
        k = ['Bare Hand', 'ShortSword', 'Sword', 'Axe', 'Spear', 'Bow', 'Staff', 'Shield']
        k = list(map(lambda x: x.rjust(10, ' '), k))
        with open(filename, 'w') as sys.stdout:
            print('')
            print('')
            print(' '*20, *k)
            for key, name in jobNames.items():
                affinities = self.affinities[key]
                values = affinities.getValues()
                values = list(map(lambda x: x.rjust(10, ' '), affinities.getValues()))
                print(name.ljust(20, ' '), *values)

        sys.stdout = sys.__stdout__


# TODO: shuffle asterisk rematch battles????
class MONSTERPARTY(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'MonsterPartyAsset')
        self.data = self.table['MonsterPartyMap']['data']
        self.levels = {}
        for party in self.data.values():
            for i in range(1, 7):
                Id = party[f"Monster{i}Id"].value
                Level = party[f"Monster{i}Level"].value
                if Id < 0:
                    continue
                if Id not in self.levels:
                    self.levels[Id] = set()
                self.levels[Id].add(Level)

        ### MUST LOAD DATA (TO BE UPDATED) FOR SHUFFLING ENEMIES IN JOB BATTLES
        self.asterisks = hjson.load(open(get_filename('json/asterisks.json'), 'r')) # Battles where you earn an asterisk
        self.tribulation = hjson.load(open(get_filename('json/tribulation.json'), 'r'))
        self.rareMonsters = hjson.load(open(get_filename('json/rare_monsters.json'), 'r'))
        self.questBosses = hjson.load(open(get_filename('json/quest_bosses.json'), 'r'))
        self.bosses = hjson.load(open(get_filename('json/bosses.json'), 'r'))
        self.nexus = hjson.load(open(get_filename('json/nexus.json'), 'r'))
        # ENSURE NEXUS IS LAST FOR HALL REPEATS
        self.bossList = [self.asterisks, self.tribulation, self.rareMonsters, self.questBosses, self.bosses, self.nexus]

        self.enemyIdToName = {}
        def fillEnemyName(d):
            for name, value in d.items():
                self.enemyIdToName[value['Id']] = name

        for bosses in self.bossList:
            fillEnemyName(bosses)

        self.enemyLevels = {}
        def fillLevelDict(d):
            for name, value in d.items():
                self.enemyLevels[name] = 0
                for party in value['Party']:
                    Id = party['PartyId']
                    slotNum = party['Slot'][7] # Monster?Id
                    level = self.data[Id][f"Monster{slotNum}Level"].value
                    self.enemyLevels[name] = max(level, self.enemyLevels[name])

        for bosses in self.bossList:
            fillLevelDict(bosses)

    # Nerf the whole party that includes the monster with Id
    # JUST FOR TESTING PURPOSES!!!
    def partyNerf(self, Id):
        name = self.enemyIdToName[Id]
        for bosses in self.bossList:
            for boss in bosses.values():
                if name == boss['Name']:
                    partyId = boss['Party'][-1]['PartyId'] # Assumes the last party is the only important one!!!!
                    party = self.data[partyId]
                    print(f"Nerfing {name}'s party to Level 1")
                    for i in range(1, 7):
                        party[f"Monster{i}Level"].value = 1
                    return

    def getGroup(self, Id):
        assert Id in self.enemyIdToName, f"Enemy ID {Id} is not in a boss dictionary!"
        group = []
        name = self.enemyIdToName[Id]
        for bosses in self.bossList:
            for boss in bosses.values():
                if name == boss['Name']:
                    partyId = boss['Party'][-1]['PartyId'] # Assumes the last party is the only important one!!!!
                    party = self.data[partyId]
                    for i in range(1, 7):
                        enemyId = party[f"Monster{i}Id"].value
                        if enemyId > 0 and enemyId != Id:
                            group.append(enemyId)
                    return group
        return group

    def update(self):

        def patchParty(d):
            for boss in d.values():
                for party in boss['Party']:
                    Id = party['PartyId']
                    slot = party['Slot']
                    self.data[Id][slot].value = boss['Id']

        patchParty(self.asterisks)
        patchParty(self.tribulation)
        patchParty(self.rareMonsters)
        patchParty(self.questBosses)
        patchParty(self.bosses)
        patchParty(self.nexus)

        ########################
        # MISCELLANEOUS TWEAKS #
        ########################

        # Hall of Tribulation party arrangements -- allow for enemy of size S, M, or L
        partyIds = set([battle['Party'][0]['PartyId'] for battle in self.tribulation.values()])
        for Id in partyIds:
            if self.data[Id]['LayoutTypeName'].name[:21] == 'MonsterPosition_3_JBS':
                self.data[Id]['LayoutTypeName'].name = 'MonsterPosition_3_L'
                self.data[Id]['IntroductionName'].name = 'MonsterPosition_3_L'
            elif self.data[Id]['LayoutTypeName'].name[:21] == 'MonsterPosition_4_JBS':
                self.data[Id]['LayoutTypeName'].name = 'MonsterPosition_4_L'
                self.data[Id]['IntroductionName'].name = 'MonsterPosition_4_L'

        # Nexus fight layouts
        if self.data[750017]['Monster1Id'].value != 400905: # No longer an arm!
            self.data[750017]['LayoutTypeName'].name = 'MonsterPosition_3_L'      # Chapter 6
            self.data[750017]['IntroductionName'].name = 'MonsterPosition_3_L'
            self.data[750009]['LayoutTypeName'].name = 'MonsterPosition_3_L'      # Chapter 7
            self.data[750009]['IntroductionName'].name = 'MonsterPosition_3_L'

        super().update()

    # NOTE: This is a crude estimate of chapter based on the enemy's level!
    def getChapter(self, Id):
        if Id not in self.levels:
            return

        levels = self.levels[Id].difference([1])
        if levels == set():
            return

        chapter = int(min(levels) / 10)
        return min(chapter, 7)

    def spoilers(self, filename):

        def printLine(old, new):
            print('   ', old.ljust(14, ' '), '<-- ', new)

        def printHall(name):
            printLine(name, self.tribulation[name]['Name'])

        def printNexus(name):
            printLine(name[:-2], self.nexus[name]['Name'])

        def printQuest(name):
            quest = f"Quest {self.questBosses[name]['Quest']}".ljust(10, ' ')
            print('   ', quest, name.ljust(14, ' '), '<-- ', self.questBosses[name]['Name'])

        with open(filename, 'w') as sys.stdout:
            print('')
            # print('Default Boss'.ljust(19, ' '), 'New Boss')
            print('---------------')
            print('Asterisk Bosses')
            print('---------------')
            print('')
            for name, value in self.asterisks.items():
                printLine(name, value['Name'])
            print('')
            print('')
            print('----')
            print('Musa')
            print('----')
            print('')
            for name, value in self.bosses.items():
                printLine(name, value['Name'])
            print('')
            print('')
            print('-------------')
            print("Night's Nexus")
            print('-------------')
            print('')
            print(' Chapter 6')
            printNexus('Grasping Hand 1')
            printNexus('Cradling Hand 1')
            print('')
            print(' Chapter 7')
            printNexus('Grasping Hand 2')
            printNexus('Cradling Hand 2')
            print('')
            print('')
            print('--------------------')
            print('Halls of Tribulation')
            print('--------------------')
            print('')
            print(' Portal 1 -- Near Halcyonia')
            printHall('Lady Emma')
            printHall('Lonsdale')
            printHall('Sir Sloan')
            print('')
            print(' Portal 2 -- Near Halcyonia (Vally of Sighs)')
            printHall('Orpheus')
            printHall('Bernard')
            printHall('Anihal')
            printHall('Shirley')
            print('')
            print(' Portal 3 -- Near Savalon')
            printHall('Gladys')
            printHall('Galahad')
            printHall('Glenn')
            print('')
            print(' Portal 4 -- Near Wiswald')
            printHall('Martha')
            printHall('Domenic')
            printHall('Helio')
            print('')
            print(' Portal 5 -- Near Ederno')
            printHall('Vigintio')
            printHall('Prince Castor')
            printHall('Folie')
            print('')
            print(' Portal 6 -- Near Rimedhal')
            printHall('Horten')
            printHall('Adam')
            printHall('Marla')
            print('')
            print(' Portal 7 -- Near Holograd')
            printHall('Roddy')
            printHall('Dag')
            printHall('Selene')
            printHall('Lily')
            print('')
            print('')
            print('------------')
            print('Quest Bosses')
            print('------------')
            print('')
            for name in self.questBosses:
                printQuest(name)
            print('')
            print('')
            print('------------')
            print('Rare Enemies')
            print('------------')
            print('')
            for name, value in self.rareMonsters.items():
                printLine(name, value['Name'])
            print('')
            print('')

        sys.stdout = sys.__stdout__


class MONSTERS(DATA):
    def __init__(self, rom, monsterText, itemText, monsterParty):
        super().__init__(rom, 'MonsterDataAsset')
        self.data = self.table['MonsterDataMap']['data']
        self.monsterText = monsterText
        self.itemText = itemText
        self.monsterParty = monsterParty

        self.steals = {}
        self.drops = {}
        dontdrop = set([
            102182, # Oberon Gem
            101940, # Spellblossom
            101420, # Bomb Arm
            102380, # Soul Food
        ])
        for d in self.data.values():
            Id = d['Id'].value

            # Skip monster with no distinguishable chapter (i.e. level)
            chapter = self.monsterParty.getChapter(Id)
            if chapter is None:
                continue

            # Skip monster without a name
            name = self.monsterText.getName(Id)
            if not name:
                continue

            # Stolen items
            itemId = d['StealItem'].value
            itemName = self.itemText.getName(itemId)
            rareItemId = d['StealRareItem'].value
            rareItemName = self.itemText.getName(rareItemId)
            self.steals[Id] = STEAL(
                chapter, Id,
                ITEMENEMY(itemId, Name=itemName),
                ITEMENEMY(rareItemId, Name=rareItemName),
                name,
            )

            # Dropped items
            itemId = d['DropItemId'].value
            itemName = self.itemText.getName(itemId)
            rareItemId = d['DropRareItemId'].value
            rareItemName = self.itemText.getName(rareItemId)
            self.drops[Id] = DROP(
                chapter, Id,
                ITEMENEMY(itemId, Name=itemName),
                ITEMENEMY(rareItemId, Name=rareItemName),
                name,
                itemId in dontdrop,
                rareItemId in dontdrop,
            )

        # ENSURE STEAM AND SWITCH GIVE THE SAME RESULTS!!!!
        # Their levels are messed up in the Switch version!
        self.steals[103202].Chapter = 1 # Staggermoth
        self.drops[103202].Chapter = 1
        self.steals[105503].Chapter = 4 # Xanthos
        self.drops[105503].Chapter = 4
                
        # Group subsets of the resistance data together for shuffling
        self.isBoss = {}
        self.magic = {}
        self.weapons = {}
        self.effects = {}
        for d in self.data.values():
            Id = d['Id'].value
            self.isBoss[Id] = d['MonsterRank'].value == 'EMonsterRankEnum::MRE_Boss'
            self.magic[Id] = MAGIC(
                d['FireResistance'],
                d['WaterResistance'],
                d['LightningResistance'],
                d['EarthResistance'],
                d['WindResistance'],
                d['LightResistance'],
                d['DarknessResistance'],
            )
            self.weapons[Id] = WEAPONS(
                d['ShortSwordResistance'],
                d['SwordResistance'],
                d['AxeResistance'],
                d['SpearResistance'],
                d['BowResistance'],
                d['StaffResistance'],
            )
            self.effects[Id] = EFFECTS(
                d['ResistancePoison'],          d['ResistanceLevelPoison'],
                d['ResistanceDark'],            d['ResistanceLevelDark'],
                d['ResistanceSilence'],         d['ResistanceLevelSilence'],
                d['ResistanceSleep'],           d['ResistanceLevelSleep'],
                d['ResistanceParalysis'],       d['ResistanceLevelParalysis'],
                d['ResistanceFear'],            d['ResistanceLevelFear'],
                d['ResistanceBerzerk'],         d['ResistanceLevelBerzerk'],
                d['ResistanceConfusion'],       d['ResistanceLevelConfusion'],
                d['ResistanceSeduction'],       d['ResistanceLevelSeduction'],
                d['ResistanceInstantDeath'],    d['ResistanceLevelInstantDeath'],
                d['ResistanceDeathTimer'],      d['ResistanceLevelDeathTimer'],
                d['ResistanceStop'],            d['ResistanceLevelStop'],
                d['ResistanceFreeze'],          d['ResistanceLevelFreeze'],
                d['ResistanceBattleExclusion'], d['ResistanceLevelBattleExclusion'],
                d['ResistanceTransparent'],     d['ResistanceLevelTransparent'],
                d['ResistancePaint'],           d['ResistanceLevelPaint'],
                d['ResistanceEpidemic'],        d['ResistanceLevelEpidemic'],
                d['ResistanceSlow'],            d['ResistanceLevelSlow'],
                d['ResistanceWeakPoint'],       d['ResistanceLevelWeakPoint'],
            )

        # AI for boss shuffle
        self.ai = {}
        ids = [
            300101,300201,300401,300501,300601,300701,300801,
            300901,301001,301101,301201,301301,301401,301501,
            301601,301701,301801,301901,302001,302101,302202,
            302301,
        ]
        for id in ids:
            d = self.data[id]
            self.ai[id] = BOSSAI(
                d['BattleAnimationBlueprintName'],
                d['BattleActionPathName'],
                d['ArtificialIntelligenceID'],
            )

        # Various stats to be swapped along with asterisk bosses
        # Don't bother with tribulation bosses
        self.stats = {}
        for name, asterisk in self.monsterParty.asterisks.items():
            Id = asterisk['Id']
            self.stats[name] = {
                'HPModifier': self.data[Id]['HPModifier'].value,
                'PhysicalAttackModifier': self.data[Id]['PhysicalAttackModifier'].value,
                'MagicAttackModifier': self.data[Id]['MagicAttackModifier'].value,
                'pq': self.data[Id]['pq'].value,
                'Exp': self.data[Id]['Exp'].value,
                'Jp': self.data[Id]['Jp'].value,
            }

        # Store vanilla sword resistance for early bosses
        self.selene = self.weapons[300201].SwordResistance
        self.dag = self.weapons[300401].SwordResistance
        self.horten = self.weapons[300101].SwordResistance

    def update(self):

        # Ensure vanilla weakness to Sir Sloan's attack, just a safety precaution
        self.weapons[300201].SwordResistance = self.selene
        self.weapons[300401].SwordResistance = self.dag
        self.weapons[300101].SwordResistance = self.horten

        # Update resistances
        for Id, magic in self.magic.items():
            for attr, value in magic.__dict__.items():
                self.data[Id][attr] = value

        for Id, weapons in self.weapons.items():
            for attr, value in weapons.__dict__.items():
                self.data[Id][attr] = value

        for Id, effects in self.effects.items():
            for attr, value in effects.__dict__.items():
                self.data[Id][attr] = value

        # Update items
        for Id, drop in self.drops.items():
            self.data[Id]['DropItemId'].value = drop.Item.Id
            self.data[Id]['DropRareItemId'].value = drop.RareItem.Id

        for Id, steal in self.steals.items():
            self.data[Id]['StealItem'].value = steal.Item.Id
            self.data[Id]['StealRareItem'].value = steal.RareItem.Id

        # Update Boss IDs
        for Id, ai in self.ai.items():
            # self.data[Id]['BattleAnimationBlueprintName'] = ai.Animation
            self.data[Id]['BattleActionPathName'] = ai.ActionPath
            self.data[Id]['ArtificialIntelligenceID'] = ai.AIID

        # Miscellaneous stats to be swapped with bosses
        for slot in self.monsterParty.asterisks:
            boss = self.monsterParty.asterisks[slot]['Name']
            newId = self.monsterParty.asterisks[slot]['Id']
            self.data[newId]['MPModifier'].value = 10000
            for key, value in self.stats[boss].items():
                self.data[newId][key].value = value
            if slot in ['Selene*', 'Dag*', 'Horten*']: # Ensure any boss in the early slots are weak to Swords
                self.weapons[newId].SwordResistance = self.selene

        #########################
        # Specific boss updates #
        #########################

        ### Vigintio ###
        newId = self.monsterParty.asterisks['Vigintio*']['Id']
        if newId != 301901:
            # Increase Vigintio's HP Modifier
            self.data[301901]['HPModifier'].value = 3000
            # Split Vigintio's replacement's HP Modifier
            self.data[newId]['HPModifier'].value = int(self.data[newId]['HPModifier'].value / 2)

        super().update()

    def shuffleBossAI(self):
        ids = list(self.ai.keys())
        for i, Id_i in enumerate(ids):
            Id_j = random.sample(ids[i:], 1)[0]
            print(Id_i, '<--', self.ai[Id_j].AIID.name)
            self.ai[Id_i], self.ai[Id_j] = self.ai[Id_j], self.ai[Id_i]
        
    # "PQ" in the code, "PG" in the game
    def scalePG(self, scale):
        assert scale >= 0
        for d in self.data.values():
            pg = int(scale * d['pq'].value)
            d['pq'].value = min(pg, 99999)

    def scaleEXP(self, scale):
        assert scale >= 0
        for d in self.data.values():
            exp = int(scale * d['Exp'].value)
            d['Exp'].value = min(exp, 99999)

    def scaleJP(self, scale):
        assert scale >= 0
        for d in self.data.values():
            jp = int(scale * d['Jp'].value)
            d['Jp'].value = min(jp, 9999)

    def spoilers(self, filename):
        steals = sorted(self.steals.values(), key=lambda x: x.Name)

        with open(filename, 'w') as sys.stdout:
            print('')
            print('')
            print('Name'.ljust(24, ' '), 'Steal Item'.ljust(35, ' '), 'Steal Rare Item'.ljust(35, ' '), 'Drop Item'.ljust(35, ' '), 'Drop Rare Item'.ljust(35, ' '))
            print('-'*24, '-'*35, '-'*35, '-'*35, '-'*35)
            print('')
            for es in steals:
                ed = self.drops[es.EnemyId]
                assert es.Name == ed.Name
                print(es.Name.ljust(24, ' '), es.getString(), ed.getString())
        
        sys.stdout = sys.__stdout__


class MONSTERABILITIES(DATA):
    def __init__(self, rom, monsterAbilityText):
        super().__init__(rom, 'MonsterActionAbilityAsset')
        self.abilities = self.table['ActionAbilityDataMap']['data']
        self.abilityText = monsterAbilityText # ID -> GetName -> Name

    def overwriteValue(self, abilityID, value, index):
        effects = self.abilities[abilityID]['AbilityEffect'].array
        effects[index]['Value1'].value = float(value)

    def scaleByMaxHP(self, abilityID, percent, index=0):
        effects = self.abilities[abilityID]['AbilityEffect'].array
        effects[index]['Value1'].value = float(percent)
        effects[index]['ValueType'].value = 'EAbilityEffectTypeEnum::AETE_Maximum_HP'

    def scaleByMaxTargetHP(self, abilityID, percent, index=0):
        effects = self.abilities[abilityID]['AbilityEffect'].array
        effects[index]['Value1'].value = float(percent)
        effects[index]['ValueType'].value = 'EAbilityEffectTypeEnum::AETE_Target_Maximum_HP'

    def removeEffects(self, abilityID, indices):
        if isinstance(indices, list):
            indices = sorted(indices)
        elif isinstance(indices, int):
            indices = [indices]
        else:
            sys.exit(f"Monster Abilities removeEffects does not take type {type(indices)} for indices")

        effects = self.abilities[abilityID]['AbilityEffect'].array
        while indices:
            index = indices.pop()
            effects.pop(index)


class QUESTS(DATA):
    def __init__(self, rom, text):
        super().__init__(rom, 'QuestAsset')
        self.text = text
        self.questArray = self.table['QuestArray']['data'].array
        with open(get_filename('json/quests.json'),'r') as file:
            self.json = {int(key):value for key, value in hjson.load(file).items()}

        ## Organize data for shuffling
        self.questRewards = {i:[] for i in range(8)}
        for i, quest in enumerate(self.questArray[148:]):
            if quest['RewardType'].value != 'EQuestRewardType::None':
                rewardId = quest['RewardID'].value
                rewardCount = quest['RewardCount'].value
                itemName = self.text.getName(rewardId)
                subQuestIndex = quest['SubQuestIndex'].value
                subQuestName = self.json[subQuestIndex]['Name']
                chapter = self.json[subQuestIndex]['Chapter']
                location = self.json[subQuestIndex]['Location']
                self.questRewards[chapter].append(
                    QUESTREWARD(
                        148+i,
                        chapter,
                        ITEM(rewardId, rewardCount, itemName),
                        location,
                        subQuestIndex,
                        subQuestName,
                    )
                )

        # Sort chapters (mainly for printouts)
        for i in range(8):
            self.questRewards[i] = sorted(self.questRewards[i], key=lambda x: x.SubQuestIndex)

    def update(self):
        for chapterQuests in self.questRewards.values():
            for quest in chapterQuests:
                i = quest.Index
                self.questArray[i]['RewardID'].value = quest.Item.Id
                self.questArray[i]['RewardCount'].value = quest.Item.Count
                if quest.Item.isMoney():
                    self.questArray[i]['RewardType'].value = "EQuestRewardType::Money"
                else:
                    self.questArray[i]['RewardType'].value = "EQuestRewardType::Item"

        super().update()

    def spoilers(self, filename):
        with open(filename, 'w') as sys.stdout:
            for i in range(7):
                print('')
                print('')
                if i == 0:
                    print('--------')
                    print('Prologue')
                    print('--------')
                else:
                    print('---------')
                    print(f'Chapter {i}')
                    print('---------')
                print('')
                for quest in self.questRewards[i]:
                    print('   ', quest.getString())

        sys.stdout = sys.__stdout__


class TREASURES(DATA):
    def __init__(self, rom, text):
        super().__init__(rom, 'TreasureBoxDataAsset')
        self.text = text
        self.data = list(self.table.values())[0]['data']
        with open(get_filename('json/treasures.json'),'r') as file:
            self.json = hjson.load(file)

        self.chests = {i:[] for i in range(8)}
        self.enemyParties = {}
        for key, value in self.data.items():
            if key in self.json:
                chapter = self.json[key]['Chapter']
                itemId = value['ItemId'].value
                itemCount = value['ItemCount'].value
                itemName = self.text.getName(itemId)
                enemyPartyId = value['EnemyPartyId'].value
                eventType = value['EventType'].value
                location = self.json[key]['Location']
                self.chests[chapter].append(
                    CHEST(
                        key,
                        chapter,
                        ITEM(itemId, itemCount, itemName),
                        eventType,
                        enemyPartyId,
                        location,
                    )
                )
                # NEED TO ORGANIZE ENEMY PARTY BY LOCATION
                if location not in self.enemyParties:
                    self.enemyParties[location] = []
                if enemyPartyId > 100:
                    self.enemyParties[location].append(enemyPartyId)

        # Sort by location
        for chests in self.chests.values():
            chests.sort(key=lambda x: x.Location)

    def update(self):
        for chapterChests in self.chests.values():
            for chest in chapterChests:
                data = self.data[chest.Key]
                data['ItemId'].value = chest.Item.Id
                data['ItemCount'].value = chest.Item.Count
                data['EventType'].value = chest.EventType
                data['EnemyPartyId'].value = chest.EnemyPartyId
                if chest.Item.isMoney():
                    data['TreasureType'].value = 'ETreasureType::Money'
                else:
                    data['TreasureType'].value = 'ETreasureType::Item'

        super().update()

    def spoilers(self, filename):
        with open(filename, 'w') as sys.stdout:
            for i in range(8):
                if i == 0:
                    print('** denotes chests with battle')
                    print('')
                    print('')
                    print('--------')
                    print('Prologue')
                    print('--------')
                else:
                    print('')
                    print('')
                    print('----------')
                    print(f'Chapter {i}')
                    print('----------')
                print('')
                for chest in self.chests[i]:
                    if chest.EventType == 3:
                        print(' **', chest.getString())
                    else:
                        print('   ', chest.getString())

        sys.stdout = sys.__stdout__


class TEXT(DATA):
    def __init__(self, rom, baseName):
        super().__init__(rom, baseName)
        self.data = list(self.table.values())[0]['data']
        keys = list(self.data[next(iter(self.data))].keys())
        self.nameKey = list(filter(lambda key: 'Name' in key, keys))[0]
        descKey = self.nameKey.replace('Name', 'Description')
        if descKey in keys:
            self.descKey = descKey
        else:
            self.descKey = None

    def getName(self, key):
        if key in self.data:
            return self.data[key][self.nameKey].string

    def getDescription(self, key):
        if self.descKey:
            return self.data[key][self.descKey].string



# class FLAGS(DATA):
#     def __init__(self, rom):
#         super().__init__(rom, 'FlagDataAsset')
#         self.bools = self.table['BoolFlagDataArray']['data'].array
#         self.ints = self.table['IntegerFlagDataArray']['data'].array

#         self.boolsDict = {}
#         for entry in self.bools:
#             f = entry['FlagID']
#             v = entry['InitialValue']
#             self.boolsDict[f] = v

#         self.intsDict = {}
#         for entry in self.ints:
#             f = entry['FlagID']
#             v = entry['InitialValue']
#             self.intsDict[f] = v

#     def update(self):
#         ### DON'T SEEM TO DO ANYTHING
#         # self.boolsDict['LIMITATION_TELEPO'] = True
#         # self.boolsDict['RELEASE_FASTTRAVEL'] = True
#         # self.boolsDict['NPC_JBS01_J00_ON'] = True
#         # self.boolsDict['BF_EV00_TUTORIAL_01_END'] = True
#         # self.boolsDict['BF_EV00_TUTORIAL_02_END'] = True
#         # self.boolsDict['BF_EV00_TUTORIAL_03_END'] = True
#         # self.boolsDict['BF_EX_TUTORIAL_END'] = True
#         # self.boolsDict['EX01_VICTORY'] = True
#         # self.boolsDict['EX02_VICTORY'] = True
#         # self.boolsDict['EX03_VICTORY'] = True
#         # self.boolsDict['EX04_VICTORY'] = True
#         # self.boolsDict['EX05_VICTORY'] = True
#         # self.boolsDict['EX06_VICTORY'] = True
#         # self.boolsDict['EX07_VICTORY'] = True
#         # self.intsDict['ASTERISK_NUMBER'] = 2
#         # self.intsDict['INT_CHAPTER_NUMBER'] = 5
#         # self.intsDict['RELEASE_MENU_JOBABI'] = 1

#         for i, value in enumerate(self.boolsDict.values()):
#             self.bools[i]['InitialValue'] = value

#         for i, value in enumerate(self.intsDict.values()):
#             self.ints[i]['InitialValue'] = value

#         super().update()


# class AI(DATA):
#     def __init__(self, rom, monsterText, monsters, monsterParty, abilityText, supportText):
#         super().__init__(rom, 'MonsterAIAsset')
#         self.monsterText = monsterText # Link ID to name
#         self.monsters = monsters # find out which AI to use
#         self.monsterParty = monsterParty # e.g. find which enemies Glenn should revive
#         self.abilityText = abilityText
#         self.supportText = supportText

#         self.data = self.table['MonsterAIDataMap']['data']

#         with open(get_filename('json/asterisks.json'),'r') as file:
#             asterisks = hjson.load(file)
#         self.asteriskIDToName = {a['Id']:name for name, a in asterisks.items()}

#         #### MAP AI TO ENEMY NAME
#         self.aiToName = {}
#         self.dataActions = {}
#         for mID, monster in self.monsters.data.items():
#             if mID in self.asteriskIDToName: # Distinguish asterisk bosses from hall of tribulation bosses
#                 name = self.asteriskIDToName[mID]
#             else:
#                 name = self.monsterText.getName(mID)
#             ai = monster['ArtificialIntelligenceID'].name
#             datum = self.data[ai]
#             # List of actions
#             array = []
#             for state in datum['States'].array:
#                 array += state['HealAction'].structData['Actions'].array
#                 array += state['Brave0'].structData['Actions'].array
#                 array += state['Brave1'].structData['Actions'].array
#                 array += state['Brave2'].structData['Actions'].array
#                 array += state['Brave3'].structData['Actions'].array
#                 for routine in state['Routines'].array:
#                     for actionList in routine['NormalActions'].array:
#                         array += actionList['Actions'].array

#             # Store all structs with ID in a dict so they can all be overwritten as needed
#             self.dataActions[name] = {ai['ID'].value:[] for ai in array}
#             for ai in array:
#                 ID = ai['ID'].value
#                 self.dataActions[name][ID].append(ai['ID'])

#         # #### MIGHT BE USEFUL FOR ORGANIZING TARGETS FOR GLENN, ETC.
#         # self.hall_Glenn = self.structDicts('JBS18_AI002')
#         # group = self.monsterParty.getGroup(301802)


#     # CHANGE ACTIONS
#     def changeActions(self, enemyName, oldID, newID):
#         actions = self.dataActions[enemyName]
#         for action in actions[oldID]:
#             action.value = newID

#     #### MIGHT BE USEFUL FOR ORGANIZING TARGETS FOR GLENN, ETC.
#     def structDicts(self, Id):
#         structs = {}

#         def addToStructs(struct):
#             value = int(struct['Value'].value)
#             if value in self.monsterParty.enemyIdToName:
#                 name = self.monsterParty.enemyIdToName[value]
#                 if name not in structs:
#                     structs[name] = []
#                 structs[name].append(struct)

#         def commonStruct(struct):
#             addToStructs(struct['Condition'].structData)
#             for action in struct['Actions'].array:
#                 addToStructs(action['Condition'].structData)
#                 for target in action['Targets'].array:
#                     addToStructs(target)

#         states = self.data[Id]['States']
#         for state in states.array:
#             commonStruct(state['HealAction'].structData)
#             for routine in state['Routines'].array:
#                 for action in routine['NormalActions'].array:
#                     commonStruct(action)
#             commonStruct(state['Brave0'].structData)
#             commonStruct(state['Brave1'].structData)
#             commonStruct(state['Brave2'].structData)
#             commonStruct(state['Brave3'].structData)

#         return structs

#     #### MIGHT BE USEFUL FOR ORGANIZING TARGETS FOR GLENN, ETC.
#     def updateDicts(self, name, structs, group):
#         for key, structArray in structs.items():
#             if key == name:
#                 continue
#             Id = group.pop(0)
#             # Id = group.pop()
#             for struct in structArray:
#                 struct['Value'].value = float(Id)

#     def update(self):
#         # #### MIGHT BE USEFUL FOR ORGANIZING TARGETS FOR GLENN, ETC.
#         # group = self.monsterParty.getGroup(301802) # Glenn from Hall of Tribulation
#         # self.updateDicts('Glenn', self.hall_Glenn, group)
#         super().update()

