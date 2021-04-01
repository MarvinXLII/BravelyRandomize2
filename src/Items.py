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
            items = steal['steal']
            c = min(steal['chapter'], 5)
            count = random.choices([1,2,3], [0.85,0.10,0.05])[0]
            chapters[c].append((items['StealItem'], count))
            chapters[c].append((items['StealRareItem'], 1))

    ##################
    # SHUFFLE STEALS #
    ##################

    for slots in chapters.values():
        random.shuffle(slots)

    for steal in monsters.steals.values():
        if steal['shuffle']:
            c = min(steal['chapter'], 5)
            idx = 0
            while chapters[c][idx][0] == -1:
                idx += 1
            steal['steal']['StealItem'], _ = chapters[c].pop(idx)
            while chapters[c][idx][0] == -1:
                idx += 1
            steal['steal']['StealRareItem'], _ = chapters[c].pop(idx)

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
