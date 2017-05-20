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
    sizeY = int(shelve.open("progress.dat")["sizeY"]) - block_side / 2
    block = []  # type 1
    foes = []
    back = []
    print ("With magic I make...")
    level.reverse()
    for line in range(len(level)):
        for column in range(len(level[line][0])):
            specific = level[line][0][column]
            x =  column * block_side
            y = sizeY - line * block_side
            thing = False
            if specific == "g":
                thing = "ground"
            if specific == "p":
                thing = "platform"
            if specific == "w":
                thing = "wall"
            if specific == "s":
                thing = "slime"
            if specific == "h":
                thing = "heal"
            if specific == "d":
                thing = "door"
            if specific == "e":
                thing = "goal"
            if specific == "m":
                thing = "mage"
            if thing in ["ground", "platform", "wall", "heal", "door", "goal"]:
                block.append((thing,x , y))
            if thing in ["slime"]:
                foes.append((thing, x, y))
            if thing in ["mage"]:
                back.append((thing, x, y))
                
    lvl_file = shelve.open("levels/level" +
                           str(lvl_n) + ".dat")

    lvl_file["block"] = block
    lvl_file["foes"] = foes
    lvl_file["back"] = back
    print len(block), "blocks,"
    lvl_file.close()
    progress.close()
    print (("and voila, level " + str(lvl_n) + " was created!"))
#_________________________level characteristics____________#
# simbol|meaning
# g     | ground block
# w     | wall
# p     | platform
# s     | slime
# h     | healing bonus
# d     | door
# e     | quests end
# m     | mage
level_list = [
             ["g                    wgggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"],
             ["g                    w                            w                                    g                                         g"],
             ["g                    w                            w                       s            g                    s                    g"],
             ["g                    w                            w                                    g                                         g"],
             ["g                    w                            w                     gggggggg       g                    ggggg                g"],
             ["g                    w                                                 gg              g                         g           e   g"],
             ["g                                   m                      m          gwg              g             ppppppp     gg              g"],
             ["g                                                                    gwwgggggggggppppppg                         ggg       gggg  g"],
             ["g                        s                                      d   gw  h     dg             pppppppp            gggg   ppp      g"],
             ["g                                                           gpppgggggggggggggggg                                                 g"],
             ["g             ppppppppppppppppppppppppp           ppppp  ggg                         pppppppp                           ppp      g"],
             ["g                                      h                                                                                         g"],
             ["gggggggggggggggggggggggggg   ggggg  ggggggg   gggggg                           ggggggggggggggggggggggggggggggggggggggggggggggggggg"]]

creator(2, level_list)
