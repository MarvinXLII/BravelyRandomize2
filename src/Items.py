import random

def randomChestBattles(treasures):

    locations = {}
    for chests in treasures.chests.values():
        for chest in chests:
            if chest.Location not in locations:
                locations[chest.Location] = []
            if treasures.enemyParties[chest.Location]:
                locations[chest.Location].append(chest)
                chest.EnemyPartyId = -1
                chest.EventType = 1

    for chests in locations.values():
        random.shuffle(chests)

    for loc, slots in locations.items():
        if loc in treasures.enemyParties:
            while treasures.enemyParties[loc]:
                chest = slots.pop()
                chest.EnemyPartyId = treasures.enemyParties[loc].pop()
                chest.EventType = 3


def shuffleItems(treasures, quests, monsters):

    # Group all items by chapter
    chapters = {i:[] for i in range(6)}
    for enemy in monsters.steals.values():
        c = min(5, enemy.Chapter)
        chapters[c].append( enemy.Item.getItem() )
        chapters[c].append( enemy.RareItem.getItem() )
    for enemy in monsters.drops.values():
        c = min(5, enemy.Chapter)
        if not enemy.hasQuestItem():
            chapters[c].append( enemy.Item.getItem() )
        if not enemy.hasQuestRareItem():
            chapters[c].append( enemy.RareItem.getItem() )

    for candidates in chapters.values():
        random.shuffle(candidates)
        
    for chapter, rewards in quests.questRewards.items():
        c = min(5, chapter)
        for reward in rewards:
            chapters[c].append( reward.Item.getItem() )
    for chapter, chests in treasures.chests.items():
        c = min(5, chapter)
        for chest in chests:
            chapters[c].append( chest.Item.getItem() )

    # Weights for item-only shuffling
    weights = {i:[] for i in range(6)}
    for c, candidates in chapters.items():
        for item in candidates:
            weights[c].append( item.canShuffle() and not item.isMoney() )

    # Fisher-Yates shuffling
    for c in range(6):
        # Get sizes
        total = len(chapters[c])
        n = total - len(quests.questRewards[c]) - len(treasures.chests[c])

        # Shuffle drops and steals -- items only!
        for i in range(n):
            if weights[c][i]: # Skip if item obj cannot be shuffled
                j = random.choices(range(i, total), weights[c][i:])[0]
                chapters[c][i], chapters[c][j] = chapters[c][j], chapters[c][i]

        # Shuffle quest and treasure items
        for i in range(n, total):
            j = random.choices(range(i, total))[0]
            chapters[c][i], chapters[c][j] = chapters[c][j], chapters[c][i]

    # Copy items back
    for enemy in monsters.steals.values():
        c = min(5, enemy.Chapter)
        enemy.Item.setItem( chapters[c].pop(0) )
        enemy.RareItem.setItem( chapters[c].pop(0) )
    for enemy in monsters.drops.values():
        c = min(5, enemy.Chapter)
        if not enemy.hasQuestItem():
            enemy.Item.setItem( chapters[c].pop(0) )
        if not enemy.hasQuestRareItem():
            enemy.RareItem.setItem( chapters[c].pop(0) )
    for chapter, rewards in quests.questRewards.items():
        c = min(5, chapter)
        for i in range(len(rewards)):
            assert chapters[c][0].canShuffle() # Ensures all quests will have a reward
            rewards[i].Item.setItem( chapters[c].pop(0) )
    for chapter, chests in treasures.chests.items():
        c = min(5, chapter)
        for i in range(len(chests)):
            assert chapters[c][0].canShuffle() # Ensures no chest is empty
            chests[i].Item.setItem( chapters[c].pop(0) )
