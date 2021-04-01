import random

def shuffleItems(treasures, quests):
    # Group by chapter
    chapters = {i:[] for i in range(8)}
    for chapter, data in treasures.boxes.items():
        for box in data:
            chapters[chapter].append((box['ItemId'], box['ItemCount']))
    for chapter, data in quests.questRewards.items():
        for reward in data:
            chapters[chapter].append((reward['RewardId'], reward['RewardCount']))
        
    # Shuffle within chapter
    for slots in chapters.values():
        random.shuffle(slots)

    # Swap a few items bewteen chapters???

    # Overwrite data
    for chapter, data in treasures.boxes.items():
        for box in data:
            box['ItemId'], box['ItemCount'] = chapters[chapter].pop()
            box['Swap'] = treasures.getContents(box['ItemId'], box['ItemCount'])

    for chapter, data in quests.questRewards.items():
        for quest in data:
            quest['RewardId'], quest['RewardCount'] = chapters[chapter].pop()
            quest['Swap'] = quests.getReward(quest['RewardId'], quest['RewardCount'])
