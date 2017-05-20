#!/usr/bin/env python

import pygame
import shelve
import random
import copy
pygame.init()

#color RGB 0-255
white = (255, 255, 255)
stupid = (60, 95, 140)
black = (0, 0, 0)
blue = (0, 0, 255)
green = (0, 255, 0)
red = (255, 0, 0)
yelow = (200, 200, 0)
blank = (0, 0, 0, 0)


def play(instance=False):
#____________________shelvs________________________________#
    progress = shelve.open("progress.dat")
    sizeX = copy.copy(progress["sizeX"])
    sizeY = copy.copy(progress["sizeY"])
    FPS = copy.copy(progress["FPS"])
    level = instance or copy.copy(progress["level"])
    P1_Keyboard = copy.copy(progress["P1_keyboard"])
    P2_keyboard = copy.copy(progress["P2_keyboard"])
    P1_keys = copy.copy(progress["P1_keys"])
    P2_keys = copy.copy(progress["P2_keys"])
    multiplayer = copy.copy(progress["multiplayer"])
    music_on = copy.copy(progress["music"])
    quest = shelve.open("levels/level" + str(level) + ".dat")
    block = copy.copy(quest["block"])
    foes = copy.copy(quest["foes"])
    back = copy.copy(quest["back"])
    quest.close()

#_____________general variables___________________________#
    pause = False
    gravity = 1
    fx_volume = 1
    music_volume = 0.3
    block_side = 64
    block_size = (block_side, block_side)
    edge = 0

#____________________display__________________________________#
    size = (sizeX, sizeY)
    display = pygame.display.set_mode(size, pygame.RESIZABLE)
    caption = pygame.display.set_caption("Mega Game from Outter Space")
    clock = pygame.time.Clock()

#___________________images______________________________________#

    load_pause = pygame.image.load("img/64/Pause.png")
    load_blocks = pygame.image.load("img/64/Blocks.png")
    load_loading = pygame.image.load("img/64/Loading.png")
    load_hp1 = pygame.image.load("img/64/Hp.png")
    load_hp2 = pygame.image.load("img/64/Hp.png")
    load_P1 = pygame.image.load("img/64/andromalius-57x88.png")
    load_P2 = pygame.image.load("img/64/andromalius-57x88.png")
    load_mage = pygame.image.load("img/64/mage-3-87x110.png")
    pause_img = pygame.Surface.convert_alpha(load_pause)
    blocks_img = pygame.Surface.convert_alpha(load_blocks)
    loading_img = pygame.Surface.convert_alpha(load_loading)
    hp1_img = pygame.Surface.convert_alpha(load_hp1)
    hp2_img = pygame.Surface.convert_alpha(load_hp2)
    P1_img = pygame.Surface.convert_alpha(load_P1)
    P2_img = pygame.Surface.convert_alpha(load_P2)
    mage_img = pygame.Surface.convert_alpha(load_mage)

    #__________________sound___________________________________#

    music_file = "sound/music/Life Burns.mp3"
    scrash_file = "sound/effects/shoot_crash.wav"
    shoot_file = "sound/effects/shoot.wav"
    Pdeath_file = "sound/effects/player_death.wav"
    heal_file = "sound/effects/hp_bonus.wav"
    fhit_file = "sound/effects/foe_hit.wav"
    scrash_fx = pygame.mixer.Sound(scrash_file)
    shoot_fx = pygame.mixer.Sound(shoot_file)
    pdeath_fx = pygame.mixer.Sound(Pdeath_file)
    heal_fx = pygame.mixer.Sound(heal_file)
    fhit_fx = pygame.mixer.Sound(fhit_file)
    pygame.mixer.music.load(music_file)
    scrash_fx.set_volume(fx_volume)
    shoot_fx.set_volume(fx_volume)
    pdeath_fx.set_volume(fx_volume)
    heal_fx.set_volume(fx_volume)
    fhit_fx.set_volume(fx_volume)
    pygame.mixer.music.set_volume(music_volume)

#____________________Loading_______________________________#
    display.fill(black)
    display.blit(loading_img, (0, 0))
    caption
    pygame.display.update()

#_____________groups_______________________________________#
    blocks = pygame.sprite.Group()
    platforms = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    players = pygame.sprite.Group()
    death = pygame.sprite.GroupSingle()
    attacks = pygame.sprite.Group()
    items = pygame.sprite.Group()
    bg_anim = pygame.sprite.Group()
    solids = pygame.sprite.Group()

#______________class______________________________________#

    class Movie(object):
        '''makes a clip from a sprite sheet'''
        step = 0
        cicle = -1

        def camera(object, steps, width, periude, y):
            object.cicle += 1
            if object.cicle >= periude:
                object.cicle = 0
                object.step += 1
                if object.step >= steps:
                    object.step = 0
            return (-object.step * width, y)

#______________building sprites___________________________#

    class Back (pygame.sprite.Sprite):
        """background"""
        def __init__(self, img, rect, steps=0, periude=5, y=0):
            pygame.sprite.Sprite.__init__(self, bg_anim)
            self.image = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
            self.rect = pygame.Rect(rect)
            self.x = rect[0]
            self.steps = steps
            self.img = img
            if steps:
                self.movie = Movie()
                self.T = periude
                self.Y = -y

        def update(self):
            self.image.fill(blank)
            if self.steps:
                a = self.steps
                b = self.rect[2]
                c = self.T
                d = self.Y
                state = self.movie.camera(a, b, c, d)
            else:
                state = (0, 0)
            self.image.blit(self.img, state)
            self.rect.centerx = self.x + hero.x

    class Block (pygame.sprite.Sprite):
        """Ground, platforms and walls"""
        def __init__(self, info):
            pygame.sprite.Sprite.__init__(self, solids)
            if info[0] == "heal":
                items.add(self)
                self.type = "heal"
                img_p = (0, -block_side)
            if info[0] == "goal":
                items.add(self)
                self.type = "goal"
                img_p = (-block_side, -block_side)
            if info[0] == "door":
                items.add(self)
                self.type = "door"
                img_p = (-2 * block_side, -block_side)
                self.command = level + 10  # carried information
            if info[0] == "ground":
                blocks.add(self)
                img_p = (-block_side, 0)
            if info[0] == "platform":
                platforms.add(self)
                img_p = (0, 0)
            if info[0] == "wall":
                blocks.add(self)
                img_p = (-2 * block_side, 0)
            self.image = pygame.Surface(block_size, pygame.SRCALPHA)
            self.rect = self.image.get_rect()
            self.image.blit(blocks_img, img_p)
            self.x = info[1]
            self.rect.centery = info[2]


        def update(self):
            self.rect.centerx = self.x + hero.x
            if self not in platforms:
                if pygame.sprite.spritecollide(self, attacks, True):
                    scrash_fx.play()

    class Attack (pygame.sprite.Sprite):

        def __init__(self, who):
            pygame.sprite.Sprite.__init__(self, attacks)
            self.image = pygame.Surface([block_side / 6, block_side / 6])
            self.image.fill(blue)
            self.rect = self.image.get_rect()
            dist = block_side / 1.5
            self.x = who.x + dist * who.direc[0]
            self.rect.centerx = copy.copy(who.rect.centerx + dist * who.stare)
            self.rect.centery = copy.copy(who.rect.centery + dist * who.direc[1])
            self.rect.centery = who.rect.centery
            if who.direc[1]:
                x = who.direc[0]
            else:
                x = who.stare
            self.velocity = copy.copy([x, who.direc[1]])
            self.who = who
            self.speed = 20
            self.live = 30
            shoot_fx.play()

        def motion(self):
            a = self.speed * self.velocity[0]
            b = not hero.action5
            c = hero.direc[0] * hero.speed
            self.rect.centerx += a + b * c
            self.rect.centery -= self.speed * self.velocity[1]
            self.live -= 1
            if self.live < 0:
                self.kill()

        def update(self):
            self.motion()

    class Player (pygame.sprite.Sprite):
        """players"""
        def __init__(self, x0=sizeX / 2, y0=0):
            pygame.sprite.Sprite.__init__(self, players)
            self.image = pygame.Surface(block_size, pygame.SRCALPHA)
            self.rect = self.image.get_rect()
            self.sheet = P1_img
            self.x = x0
            self.rect.centerx = x0
            self.rect.centery = y0
            self.accel = 0
            self.speed = -10
            self.jump = -16
            self.hp = 50
            self.magic = 25
            self.in_land = False
            self.fall = False
            self.toutch = [0, 0, 0, 0, 0, 0, 0, 0]
            self.movie = Movie()
#___________commands
##            self.key = pygame.key.get_pressed()
            self.direc = [False, False]
            self.stare = True
            self.action3 = False
            self.action4 = False
            self.action5 = False
            self.action6 = False
            self.action7 = False
            self.action9 = False

        def control(self):
            if self.keyboard:
                key = pygame.key.get_pressed()
                pressed = []
                for event in events:
                    if event.type == pygame.KEYDOWN:
                        pressed.append(event.key)
                self.action1 = key[self.path[0]]
                self.action2 = key[self.path[1]]
                self.action3 = self.path[2] in pressed   # shoot
                self.action4 = self.path[3] in pressed   # action
                self.action5 = key[self.path[4]]         # stand
                self.action6 = self.path[5] in pressed   # ressurect
                self.action7 = self.path[6] in pressed   # teleport
                self.action8 = key[self.path[7]]
                self.action9 = key[self.path[8]]         # pause
                self.action10 = key[self.path[9]]
                self.action11 = key[self.path[10]]
                right = key[self.path[11]]
                left = key[self.path[12]]
                up = key[self.path[13]]
                down = key[self.path[14]]
                self.direc[0] = right - left
                self.direc[1] = up - down

            else:
                try:
                    self.action1 = self.joystick.get_button(1)
                    self.action2 = self.joystick.get_button(2)
                    self.action3 = self.joystick.get_button(3)  # shoot
                    self.action4 = self.joystick.get_button(4)  # action
                    self.action5 = self.joystick.get_button(5)  # stand
                    self.action6 = self.joystick.get_button(6)  # ressurect
                    self.action7 = self.joystick.get_button(7)  # teleport
                    self.action8 = self.joystick.get_button(8)
                    self.action9 = self.joystick.get_button(9)  # pause
                    self.action10 = self.joystick.get_button(10)
                    self.action11 = self.joystick.get_button(11)
                    self.direc[0] = int((self.joystick.get_hat(0)[0] * 1.5))
                    if self.direc[0] == 0:
                        self.direc[0] = int((self.joystick.get_axis(0) * 1.5))
                    self.direc[1] = int((self.joystick.get_hat(0)[1] * 1.5))
                    if self.direc[1] == 0:
                        self.direc[1] = - int((self.joystick.get_axis(1) * 1.5))
                except:
                    AttributeError
            if self.direc[0]:
                self.stare = copy.copy(self.direc[0])

        def physics(self):
            self.in_land = False
            self.fall -= self.fall > 0
            drop = self.fall > 0
            jump = self.accel < 0
#___________to hit the wall
            if self.toutch[3] in blocks:
                if self == hero and self.rect.centerx == sizeX / 2:
                    self.x -= self.toutch[3].rect.left - self.rect.right
                else:
                    self.rect.right = self.toutch[3].rect.left
                    if self is not hero:
                        self.x = self.rect.centerx - hero.x
            if self.toutch[7] in blocks:
                if self == hero and self.rect.centerx == sizeX / 2:
                    self.x -= self.toutch[7].rect.right - self.rect.left
                else:
                    self.rect.left = self.toutch[7].rect.right
                    if self is not hero:
                        self.x = self.rect.centerx - hero.x
            if self.toutch[1] in blocks and jump:
                self.rect.top = self.toutch[1].rect.bottom
                self.accel = 0
            platf = self.toutch[5] in platforms and not (drop or jump)
            if self.toutch[5] in blocks or platf:
                self.rect.bottom = self.toutch[5].rect.top
                self.accel = 0
                self.in_land = True

        def contact(self):
            bump = pygame.sprite.spritecollide(self, solids, False)
            self.toutch = [0, 0, 0, 0, 0, 0, 0, 0]
            if bump:
                for thing in bump:
                    if thing.rect.collidepoint(self.rect.topleft):
                        self.toutch[0] = thing
                    if thing.rect.collidepoint(self.rect.midtop):
                        self.toutch[1] = thing
                    if thing.rect.collidepoint(self.rect.topright):
                        self.toutch[2] = thing
                    if thing.rect.collidepoint(self.rect.midright):
                        self.toutch[3] = thing
                    if thing.rect.collidepoint(self.rect.bottomright):
                        self.toutch[4] = thing
                    if thing.rect.collidepoint(self.rect.midbottom):
                        self.toutch[5] = thing
                    if thing.rect.collidepoint(self.rect.bottomleft):
                        self.toutch[6] = thing
                    if thing.rect.collidepoint(self.rect.midleft):
                        self.toutch[7] = thing

        def motion(self):
            if not self.action5:
                if self.in_land:
                    if self.direc[1] > 0:
                        self.accel = self.jump
                    elif self.direc[1] < 0:
                        self.fall = 17
#____________________move horizontal
                change = self.speed * self.direc[0]
                if self == hero:
                    if self.x > -edge or self.rect.centerx < sizeX/2:
                        self.x = -edge
                        self.rect.centerx -= change
                        if self.rect.left < 0:
                            self.rect.left = 0
                    else:
                        self.x += change
                else:
                    self.x -= change
                    if self.x - block_side/2 < edge:
                        self.x = edge + block_side/2
                    self.rect.centerx = self.x + hero.x
            self.accel += gravity * (self.accel < 23)
            self.rect.centery += self.accel
            solids.update()

        def get_hit(self):
            if pygame.sprite.spritecollide(self, enemies, False):
                self.hp -= 1 + self.action5
            if self.hp <= 0 or self.rect.centery >= sizeY:
                self.hp = 0
                self.magic = 0
                print self.x, "foi onde morri"
                self.kill()
                death.add(self)
                pdeath_fx.play()

        def spell(self):
            a = self.magic
            if a < 50:
                self.magic += 0.1
#___________teleport
            if self.action7 and self != hero and self.magic >= 50:
                self.magic -= 50
                self.x = copy.copy(hero.rect.centerx - hero.x)
                self.rect.center = copy.copy(hero.rect.center)
#___________shoot
            if self.action3 and a > 5:
                Attack(self)
                self.magic -= 5
#___________raise death
            if self.action6 and any(death) and self.magic >= 26:
                self.magic -= 26
                self.hp /= 2
                sidekick = death.sprites()[0]
                death.sprites()[0].x = copy.copy(-hero.x + hero.rect.centerx)
                death.sprites()[0].rect.center = copy.copy(self.rect.center)
                death.sprites()[0].hp = copy.copy(self.hp)
                players.add(death.sprites()[0])
                death.empty()

        def bonus(self):
            got_hit = pygame.sprite.spritecollide(self, items, False)
            for something in got_hit:
                if something.type == "goal":
                    if progress["level"] == 1:
                        progress["level"] = 2
                    else:
                        progress["level"] = 1
##                    progress["level"] += 1
                    progress.close()
                    play()
                if something.type == "heal":
                    something.kill()
                    heal_fx.play()
                    self.hp = 50
                if something.type == "door" and self.action4:
                    if self == hero:
                        self.x -= something.command * block_side - sizeX / 2 + self.rect.centerx
                        self.rect.centerx = sizeX / 2

                    else:
                        self.x += something.command * block_side + sizeX / 2


        def animation(self):
            self.image.fill(blank)
            if self.in_land:
                steps = 8
                T = 5
                line = 0
            else:
                steps = 8
                T = 5
                line = -1
            b = self.rect.width
            d = line * self.rect.height
            state = self.movie.camera(steps, b, T, d)
            img = self.sheet
            if self.stare < 0:
                img = pygame.transform.flip(self.sheet, True, False)
            self.image.blit(img, state)

        def update(self):
            if self not in death:
                self.get_hit()
                self.control()
                self.bonus()
                self.motion()
                self.spell()
                self.contact()
                self.physics()
                self.animation()

    class Enemy (pygame.sprite.Sprite):
        """enemies type 1"""
        def __init__(self, x0=100, y0=0):
            pygame.sprite.Sprite.__init__(self, enemies)
            self.speed = random.randint(-3, 3)
            self.hp = random.randint(1, 3)
            self.img = pygame.image.load("img/64/Slime.png")
            self.image = pygame.Surface(block_size, pygame.SRCALPHA)
            self.rect = self.image.get_rect()
            self.rect.height -= 10
            self.x = x0
            self.rect.centerx = x0
            self.rect.centery = y0
            self.accel = 0
            self.movie = Movie()

        def animation(self):
            self.image.fill(blank)
            T = abs(self.speed * 2)
            if self in bg_anim:
                state = self.movie.camera(4, self.rect.width, 5, -block_side)
                if state == (-3 * block_side, -block_side):
                    self.kill()
                    print ("A monster has died")
            elif self.hp > 0:
                state = self.movie.camera(2, self.rect.width, T, 0)
            img = self.img
            if self.speed > 0:
                img = pygame.transform.flip(self.img, True, False)
            self.image.blit(img, state)

        def contact(self):
            bump1 = pygame.sprite.spritecollide(self, blocks, False)
            bump2 = pygame.sprite.spritecollide(self, platforms, False)
            bump = bump1 + bump2
            self.toutch = [0, 0, 0, 0, 0, 0, 0, 0]
            if bump:
                for thing in bump:
##                    if thing.rect.collidepoint(self.rect.topleft):
##                        self.toutch[0] = thing
##                    if thing.rect.collidepoint(self.rect.midtop):
##                        self.toutch[1] = thing
##                    if thing.rect.collidepoint(self.rect.topright):
##                        self.toutch[2] = thing
                    if thing.rect.collidepoint(self.rect.midright):
                        self.toutch[3] = thing
##                    if thing.rect.collidepoint(self.rect.bottomright):
##                        self.toutch[4] = thing
                    if thing.rect.collidepoint(self.rect.midbottom):
                        self.toutch[5] = thing
                    if thing.rect.collidepoint(self.rect.midleft):
                        self.toutch[7] = thing

        def move(self):
            self.x += self.speed
            self.rect.centerx = self.x + hero.x
            self.accel += gravity * (self.accel < 20)
            self.rect.centery += self.accel

        def physics(self):
            if self.toutch[7]:
                self.speed = random.randint(1, 3)
                self.rect.left = self.toutch[7].rect.right
            if self.toutch[3] in blocks:
                self.speed = -random.randint(1, 3)
                self.rect.right = self.toutch[3].rect.left
            if self.toutch[5] in blocks or self.toutch[5] in platforms:
                self.rect.bottom = self.toutch[5].rect.top
                self.accel = 0

        def hit(self):
            got_hit = pygame.sprite.spritecollide(self, attacks, True)
            if got_hit:
                self.hp -= 1
                fhit_fx.play()
            if self.hp <= 0 or self.rect.y > sizeY:
                players.remove(self)
                bg_anim.add(self)
                self.speed = 0

        def update(self):
            self.contact()
            self.physics()
            self.hit()
            self.move()
            self.animation()

#_______________Calling sprites_____________________#
    P1 = Player(300, sizeY / 2)
    P1.x = 0
    hero = P1
    P1.keyboard = False
    if P1_Keyboard:
        P1.path = P1_keys
        P1.keyboard = True
    else:
        try:
            P1.joystick = pygame.joystick.Joystick(0)
            P1.joystick.init()
        except:
            pygame.error
    if multiplayer:
        P2 = Player(300, sizeY / 2)
        P2.sheet = P2_img
        sidekick = P2
        P2.keyboard = False
        if P2_keyboard:
            P2.path = P2_keys
            P2.keyboard = True
        else:
            try:
                P2.joystick = pygame.joystick.Joystick(P1_keyboard)
                P2.joystick.init()
            except:
                pygame.error
    if music_on:
        pygame.mixer.music.play()
    print ("This amazing adventure beguins!")

###############____main loop____############################################
    while True:
        events = copy.copy(pygame.event.get())
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                progress.close()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    pygame.display.toggle_fullscreen()
                if event.key == pygame.K_F2:
                    pygame.mixer.music.unpause()
                    pause = 1 - pause
            if event.type == pygame.VIDEORESIZE:
                size = copy.copy(event.size)
        if not any(players):
            pygame.mixer.stop()
            play()
#____________make stuff_____________________________________#
        for thing in block:
            if thing[1] < 1.5 * sizeX - hero.x:
                block.remove(thing)
                Block(thing)
        for champ in foes:
            if champ[1] < sizeX - hero.x:
                foes.remove(champ)
                Enemy(champ[1], champ[2])
        for thing in back:
            if thing[1] < sizeX - hero.x:
                back.remove(thing)
                if thing[0] == "mage":
                    back_img = mage_img
                    back_size = (87, 110)
                    back_step = 4
                    back_periud = 10
                    back_line = 0
                back_rect = [thing[1], thing[2], back_size[0], back_size[1]]
                Back(back_img, back_rect, back_step, back_periud, back_line)
#_____________destroy stuff________________________________#
        for thing in solids:
            if thing.x < edge - sizeX / 2:
                thing.kill()
        for thing in bg_anim:
            if thing.x < edge - sizeX / 2:
                thing.kill()
#____________focus screen on new main player________________#
        if hero in death:
            hero = players.sprites()[0]
            hero.x = sizeX / 2 - hero.x
            cornered = (edge + hero.x > 0) * (edge + hero.x)
            hero.rect.centerx = sizeX / 2 - cornered
#_____________update edge____________________________________#
        if len(players) == 1 and edge < -hero.x:
            edge = copy.copy(-hero.x)
        if len(players) == 2:
            edgeP1 = copy.copy(-hero.x)
            edgeP2 = copy.copy(sidekick.x - sizeX / 2)
            if edge < edgeP1 < edgeP2:
                edge = edgeP1
            if edge < edgeP2 < edgeP2:
                edge = edgeP2
        if not pause:
            display.fill(stupid)
            display.blit(hp1_img, (block_side * 13, block_side))
            hp1color = (P1.hp * 5, 50 - P1.hp, 0)
            hp1rect = [block_side * 14, block_side * 1.17, P1.hp * 4.4, 10]
            pygame.draw.rect(display, hp1color, hp1rect, 0)
            mag1color = (0, 50 - P1.magic, P1.magic * 5)
            mag1rect = [817, 85, P1.magic * 4.4, 10]
            pygame.draw.rect(display, mag1color, mag1rect, 0)
            if multiplayer:
                    display.blit(hp2_img, (10, 0))
                    hp2color = (P2.hp * 5, 0, 50 - P2.hp)
                    hp2rect = [119, 48, P2.hp * 4.4, 10]
                    pygame.draw.rect(display, hp2color, hp2rect, 0)
                    mag2color = (0, 50 - P2.magic, P2.magic * 5)
                    mag2rect = [119, 81, P2.magic * 4.4, 10]
                    pygame.draw.rect(display, mag2color, mag2rect, 0)

            bg_anim.update()
            players.update()
            enemies.update()
            attacks.update()
            solids.update()
            bg_anim.draw(display)
            attacks.draw(display)
            solids.draw(display)
            enemies.draw(display)
            players.draw(display)
#________________________Pause______________________________________#
        else:
            pygame.mixer.music.pause()
            display.blit(pause_img, (0, 0))
            for dude in players:
                dude.control()
                if dude.action9:  # dude.direc[0] > 0:
                    print ("continue")
                    pygame.mixer.music.unpause()
                    pause = False
                if dude.direc[0] < 0:
                    print ("restart")
                    return play()
                if dude.direc[1] > 0:
                    print ("options")
                if dude.direc[1] < 0:
                    print ("quit")
                    progress.close()
                    pygame.quit()

        clock.tick(FPS)
        sub_display = pygame.transform.scale(display, size)
        display.blit(sub_display, (0, 0))
        pygame.display.update((0, 0, size[0], size[1]))

play()
