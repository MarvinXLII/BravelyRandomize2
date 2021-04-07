import random

def shuffleItems(treasures, quests, monsters):

    # Group by chapter
    chapters = {i:[] for i in range(8)}
    for c, data in treasures.boxes.items():
        c = min(c, 5)
        for box in data:
            chapters[c].append((box['ItemId'], box['ItemCount']))
    for c, data in quests.questRewards.items():
        c = min(c, 5)
        for reward in data:
            chapters[c].append((reward['RewardId'], reward['RewardCount']))
    for steal in monsters.steals.values():
        if steal['shuffle']:
            item = steal['item']
            if item == -1:
                print('here')
            c = min(steal['chapter'], 5)
            count = random.choices([1,2,3], [0.85,0.10,0.05])[0]
            chapters[c].append((item, count))
    for stealRare in monsters.stealsRare.values():
        if stealRare['shuffle']:
            item = stealRare['item']
            if item == -1:
                print('here')
            c = min(stealRare['chapter'], 5)
            chapters[c].append((item, 1))
    for drops in monsters.drops.values():
        if drops['shuffle']:
            item = drops['item']
            if item == -1:
                print('here')
            c = min(drops['chapter'], 5)
            count = random.choices([1,2,3], [0.85,0.10,0.05])[0]
            chapters[c].append((item, count))
    for dropsRare in monsters.dropsRare.values():
        if dropsRare['shuffle']:
            item = dropsRare['item']
            if item == -1:
                print('here')
            c = min(dropsRare['chapter'], 5)
            chapters[c].append((item, 1))

    ############################
    # SHUFFLE STEALS AND DROPS #
    ############################

    for slots in chapters.values():
        random.shuffle(slots)

    for steal in monsters.steals.values():
        if steal['shuffle']:
            c = min(steal['chapter'], 5)
            idx = 0
            while chapters[c][idx][0] == -1:
                idx += 1
            steal['item'], _ = chapters[c].pop(idx)

    for stealRare in monsters.stealsRare.values():
        if stealRare['shuffle']:
            c = min(stealRare['chapter'], 5)
            idx = 0
            while chapters[c][idx][0] == -1:
                idx += 1
            stealRare['item'], _ = chapters[c].pop(idx)

    for drops in monsters.drops.values():
        if drops['shuffle']:
            c = min(drops['chapter'], 5)
            idx = 0
            while chapters[c][idx][0] == -1:
                idx += 1
            drops['item'], _ = chapters[c].pop(idx)

    for dropsRare in monsters.dropsRare.values():
        if dropsRare['shuffle']:
            c = min(dropsRare['chapter'], 5)
            idx = 0
            while chapters[c][idx][0] == -1:
                idx += 1
            dropsRare['item'], _ = chapters[c].pop(idx)

    #####################
    # CHESTS AND QUESTS #
    #####################

    # Ensure first slots aren't biased towards money!
    for slots in chapters.values():
        random.shuffle(slots)

    # Chests
    for c, data in treasures.boxes.items():
        c = min(c, 5)
        for box in data:
            box['ItemId'], box['ItemCount'] = chapters[c].pop()
            box['Swap'] = treasures.getContents(box['ItemId'], box['ItemCount'])

    # Quests
    for c, data in quests.questRewards.items():
        c = min(c, 5)
        for quest in data:
            quest['RewardId'], quest['RewardCount'] = chapters[c].pop()
            quest['Swap'] = quests.getReward(quest['RewardId'], quest['RewardCount'])
