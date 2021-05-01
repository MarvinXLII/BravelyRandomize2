import random

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
