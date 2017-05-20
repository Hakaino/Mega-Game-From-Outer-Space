import shelve
"""level = (level number,
            (type of object,
             kind of object,
             x0,
             y0) , ...)
"""
block_side = 64  # the lower this number is, more sprites it will create
                 # to much and the game becomes slow
                 # must be the same size as the block side in the game


def creator(lvl_n, level):
    progress = shelve.open("progress.dat")
    sizeY = int(shelve.open("progress.dat")["sizeY"])
    block = []  # type 1
    foes = []
    bonus = []
    back = []
    print ("With magic I make...")
    for i in range(len(level)):

        if level[i][0] is "slime":
            foes.append((level[i][0], level[i][1] * block_side, level[i][2] * block_side))

        if level[i][0] in ("goal", "heal", "door"):
            print ("bonus,")
            bt = [level[i][0], int(level[i][1] * block_side), int(sizeY - level[i][2] * block_side)]
            if level[i][0] is "door":
                bt.append(level[i][3])
            block.append(bt)
        if level[i][0] in ("mage", "burst"):
            print ("this thin on the back,")
            back.append([level[i][0], level[i][1] * block_side, sizeY - level[i][2] * block_side])

        if level[i][0] in ("ground", "platform"):
            lenght = int(level[i][1])
            x0 = level[i][2]
            y0 = int(sizeY - level[i][3] * block_side)
            for j in range(lenght):
                block.append((level[i][0], x0 + j * block_side, y0))

        if level[i][0] is "wall":
            lenght = level[i][1]
            x0 = level[i][2] * block_side
            y0 = sizeY - level[i][3] * block_side
            for j in range(lenght):
                block.append((level[i][0], x0, y0 - j  * block_side))
    lvl_file = shelve.open("levels/level" +
                           str(lvl_n) + ".dat")

    lvl_file["block"] = block
    lvl_file["foes"] = foes
    lvl_file["bonus"] = bonus
    lvl_file["back"] = back
    print len(block), "blocks,"
    lvl_file.close()
    progress.close()
    print (("and voila, level " + str(lvl_n) + " was created!"))
#_________________________level characteristics____________#
level_list = [
             #what is, base, x0, y0
             ["ground", 80, 0, 0],
             ["platform", 20, 10, 2],
             ["wall", 2, 20, 2],

             #what is, x0, y0, where to
             ["goal", 50, 3],
             ["heal", 33, 3],
             ["door", 10, 3, 65],

             #what is, x0, y0
             ["mage", 10, 4],
             ["mage", 22, 3],
             ["mage", 30, 3],
             ["mage", 40, 3],

             #what is, type, how many
             ["slime", 50, 10]]

creator(1, level_list)
