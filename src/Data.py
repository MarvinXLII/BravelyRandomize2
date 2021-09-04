import hjson
import sys
import random
import struct
import io
from Classes import DATA
from ClassData import ITEMASSET, ACTIONSKILL, SUPPORTSKILL, ITEM, ITEMENEMY, CHEST, QUESTREWARD, DROP, STEAL, MAGIC, WEAPONS, EFFECTS, JOB, STATS, AFFINITY
from Utilities import get_filename


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

    # NOTE: This is a crude estimate of chapter based on the enemy's level!
    def getChapter(self, Id):
        if Id not in self.levels:
            return

        levels = self.levels[Id].difference([1])
        if levels == set():
            return

        chapter = int(min(levels) / 10)
        return min(chapter, 7)


class MONSTERS(DATA):
    def __init__(self, rom, monster, items, party):
        super().__init__(rom, 'MonsterDataAsset')
        self.data = self.table['MonsterDataMap']['data']
        self.monster = monster
        self.items = items
        self.party = party

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
            chapter = self.party.getChapter(Id)
            if chapter is None:
                continue

            # Skip monster without a name
            name = self.monster.getName(Id)
            if not name:
                continue

            # Stolen items
            itemId = d['StealItem'].value
            itemName = self.items.getName(itemId)
            rareItemId = d['StealRareItem'].value
            rareItemName = self.items.getName(rareItemId)
            self.steals[Id] = STEAL(
                chapter, Id,
                ITEMENEMY(itemId, Name=itemName),
                ITEMENEMY(rareItemId, Name=rareItemName),
                name,
            )

            # Dropped items
            itemId = d['DropItemId'].value
            itemName = self.items.getName(itemId)
            rareItemId = d['DropRareItemId'].value
            rareItemName = self.items.getName(rareItemId)
            self.drops[Id] = DROP(
                chapter, Id,
                ITEMENEMY(itemId, Name=itemName),
                ITEMENEMY(rareItemId, Name=rareItemName),
                name,
                itemId in dontdrop,
                rareItemId in dontdrop,
            )
                
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

        super().update()

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

        # Sort by location
        for chests in self.chests.values():
            chests.sort(key=lambda x: x.Location)

    def update(self):
        for chapterChests in self.chests.values():
            for chest in chapterChests:
                data = self.data[chest.Key]
                data['ItemId'].value = chest.Item.Id
                data['ItemCount'].value = chest.Item.Count
                data['EventType'].vlaue = chest.EventType
                data['EnemyPartyId'].vlaue = chest.EnemyPartyId
                if chest.Item.isMoney():
                    data['TreasureType'].value = 'ETreasureType::Money'
                else:
                    data['TreasureType'].value = 'ETreasureType::Item'

        super().update()

    def spoilers(self, filename):
        with open(filename, 'w') as sys.stdout:
            for i in range(8):
                if i == 0:
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
