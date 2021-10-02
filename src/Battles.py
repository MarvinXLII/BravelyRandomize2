import random
from Utilities import get_filename
import hjson
from copy import deepcopy


def shuffleResistance(monsters):

    keys = list(monsters.isBoss.keys())

    def shuffle(objs, weights):
        for i, ki in enumerate(keys):
            if not weights[i]:
                continue
            kj = random.choices(keys[i:], weights[i:])[0]
            objs[ki], objs[kj] = objs[kj], objs[ki]

    # Shuffle resistances among bosses
    bossWeights = [isBoss for isBoss in monsters.isBoss.values()]
    shuffle(monsters.magic, bossWeights)
    shuffle(monsters.weapons, bossWeights)
    shuffle(monsters.effects, bossWeights)

    # Shuffle resistances among enemies
    enemyWeights = [not isBoss for isBoss in bossWeights]
    shuffle(monsters.magic, enemyWeights)
    shuffle(monsters.weapons, enemyWeights)
    shuffle(monsters.effects, enemyWeights)


def shuffleBosses(settings, monsters, parties):

    asterisks = parties.asterisks
    tribulation = parties.tribulation
    rareMonsters = parties.rareMonsters
    questBosses = parties.questBosses
    bosses = parties.bosses # Only musa bosses
    nexus = parties.nexus

    # TODO: rescale attacks of early/late monsters as done with asterisks
    # Specify some subsets
    lateRareMonsters = {k:v for k,v in rareMonsters.items() if v['LateGame']}
    earlyRareMonsters = {k:v for k,v in rareMonsters.items() if not v['LateGame']}
    lateQuestBosses = {k:v for k,v in questBosses.items() if v['LateGame']}
    earlyQuestBosses = {k:v for k,v in questBosses.items() if not v['LateGame']}
    lateGameSlots = {**tribulation, **bosses, **lateRareMonsters, **lateQuestBosses}
    earlyGameSlots = {**asterisks, **earlyRareMonsters, **earlyQuestBosses}
    lateGameCandidates = {**tribulation, **bosses, **lateRareMonsters, **lateQuestBosses}

    # Setup for shuffling (probably done by a loop)
    # - Vacant slots
    # - Candidates
    vacant = {}
    used = {}
    swaps = {}
    for dictionary in [asterisks, tribulation, rareMonsters, questBosses, bosses, nexus]:
        vacant.update({k: True for k in dictionary})
        used.update({k: False for k in dictionary})
        swaps.update({k: {'Id': None, 'Name': None} for k in dictionary})

    # TODO: Add options for what set of bosses to include/omit
    # For now, always shuffle asterisks, halls, and overwrite Nexus' arms
    def omit(enemyDict):
        for key, enemy in enemyDict.items():
            vacant[key] = False
            used[key] = True
            swaps[key]['Id'] = enemy['Id']
            swaps[key]['Name'] = enemy['Name']

    # omit(nexus)
    omit(questBosses)
    omit(rareMonsters)
    omit(bosses)
    # omit(tribulation)
    # omit(asterisks)

    # Overwrite Nexus arms with tribulations
    slots = list(nexus.keys())
    candidates = random.sample(sorted(tribulation), 4)
    for s, c in zip(slots, candidates):
        swaps[s]['Id'] = tribulation[c]['Id']
        swaps[s]['Name'] = tribulation[c]['Name']
        del vacant[s], used[s] # Remove nexus from potential being a candidate or slot

    def vacantList(d):
        return [k for k in d if vacant[k]]

    def unusedList(d):
        return [k for k in d if not used[k]]

    # Fill slots in swaps dict with suitable candidates
    def shuffle(candidatesDict, slotsDict):
        slots = vacantList(slotsDict)
        candidates = unusedList(candidatesDict)
        random.shuffle(slots)
        random.shuffle(candidates)
        for c, s in zip(candidates, slots):
            vacant[s] = False
            used[c] = True
            assert swaps[s]['Id'] is None, "Cannot overwrite a filled swaps slot!"
            assert swaps[s]['Name'] is None, "Cannot overwrite a filled swaps slot!"
            swaps[s]['Id'] = candidatesDict[c]['Id']
            swaps[s]['Name'] = candidatesDict[c]['Name']

    # Shuffle tribulation bosses
    slots = vacantList(lateGameSlots)
    candidates = unusedList(tribulation)
    assert len(slots) >= len(candidates)
    shuffle(tribulation, lateGameSlots)

    # Fill asterisk boss slots
    slots = vacantList(asterisks)
    candidates = unusedList(earlyGameSlots)
    assert len(slots) <= len(candidates)
    shuffle(earlyGameSlots, asterisks)

    # Asterisks need to go somewhere in the earlyGame
    slots = vacantList(earlyGameSlots)
    candidates = unusedList(asterisks)
    assert len(slots) >= len(candidates)
    shuffle(asterisks, earlyGameSlots)

    # Shuffle remaining quest bosses anywhere
    slots = vacantList(vacant)
    candidates = unusedList(questBosses) # Need to filter just in case some have to be placed elsewhere
    assert len(slots) >= len(candidates)
    shuffle(questBosses, vacant)

    # Shuffle remaining rare enemies anywhere
    slots = vacantList(vacant)
    candidates = unusedList(rareMonsters) # Need to filter just in case some have to be placed elsewhere
    assert len(slots) >= len(candidates)
    shuffle(rareMonsters, vacant)

    # Shuffle remaining rare enemies anywhere
    slots = vacantList(vacant)
    candidates = unusedList(bosses) # Need to filter just in case some have to be placed elsewhere
    assert len(slots) >= len(candidates)
    shuffle(bosses, vacant)

    def finalize(d):
        for boss in d:
            for key, value in swaps[boss].items():
                assert value is not None, "A swaps slot is empty! Oh no!!!"
                d[boss][key] = value

    finalize(asterisks)
    finalize(tribulation)
    finalize(rareMonsters)
    finalize(questBosses)
    finalize(bosses)
    finalize(nexus)


def scaleBosses(parties, monsters, abilities):

    with open(get_filename('json/ability_scalings.json'), 'r') as file:
        abilityScalings = hjson.load(file)

    with open(get_filename('json/scalings_physical.json'), 'r') as file:
        physScalings = hjson.load(file)

    with open(get_filename('json/scalings_magic.json'), 'r') as file:
        magScalings = hjson.load(file)

    # ONLY NEEDS TO BE DONE FOR ASTERISKS
    asterisks = parties.asterisks # Contains "BattleNum" for scaling
    stats = deepcopy(monsters.stats)

    # Swap and/or scale stats
    for slot in stats:
        boss = asterisks[slot]['Name']
        physScale = physScalings[slot] / physScalings[boss]
        magScale = magScalings[slot] / magScalings[boss]
        monsters.stats[boss] = stats[slot] # Take defaults for HP, Exp, JP, pg
        monsters.stats[boss]['PhysicalAttackModifier'] = 100 + int(physScale * (stats[boss]['PhysicalAttackModifier'] - 100))
        monsters.stats[boss]['MagicAttackModifier'] = 100 + int(magScale * (stats[boss]['MagicAttackModifier'] - 100))

    def overwriteValue(oldBoss, abilityID, indices=[0]):
        newBoss = asterisks[oldBoss]['Name']
        value = abilityScalings[oldBoss][str(abilityID)][newBoss]
        for index in indices:
            abilities.overwriteValue(abilityID, value, index)

    # Rescale attacks/healing of fixed values to percentages
    abilities.scaleByMaxTargetHP(300506, 0.25) # Orpheus* and Orpheus: Stone (300 by default) NOT SURE IF IT WILL WORK SINCE IT TARGETS ALL PCs!!!!
    abilities.removeEffects(300506, 1) # Orpheus* and Orpheus: Stone (max value to 300 by default; removes max value)
    abilities.scaleByMaxTargetHP(301003, 0.12) # Roddy: Healara (2000 by default, approx 11% of his HP at level 24)
    abilities.scaleByMaxTargetHP(301706, 0.50) # Domenic: Bomb Arm (2000 by default, approx 64% of default PC HP at level 40)
    abilities.scaleByMaxTargetHP(301802, 0.45) # Glenn*: Contagion Agent (1500 by default, approx 55% of default PC HP at level 34)
    abilities.scaleByMaxHP(301801, 0.15) # Glenn* and Glenn: Gigapotion (5000 by default)
    abilities.scaleByMaxTargetHP(302305, 0.9) # Sloan* and Sloan: Victory Smite (8888 by default, almost kills at max default HP of 9999)
