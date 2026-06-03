#!/usr/bin/env python3

import argparse
import os
import random
import sys
from dataclasses import dataclass


def smoke_test_requested(argv):
    return any(arg == "--smoke-test" or arg.startswith("--smoke-test=") for arg in argv)


if smoke_test_requested(sys.argv[1:]):
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from game_config import (
    BASE_DIR,
    BLOCK_SIDE,
    build_level,
    load_progress,
    next_level,
    save_progress,
)


PYGAME_READY = False

BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
SKY = (60, 95, 140)
TRANSPARENT = (0, 0, 0, 0)

MAX_HP = 50
MAX_MAGIC = 50
GRAVITY = 1
BLOCK_SIZE = (BLOCK_SIDE, BLOCK_SIDE)

KEY_SHOOT = 2
KEY_USE = 3
KEY_STAND = 4
KEY_RESURRECT = 5
KEY_TELEPORT = 6
KEY_PAUSE = 8
KEY_RIGHT = 11
KEY_LEFT = 12
KEY_UP = 13
KEY_DOWN = 14


class RestartGame(Exception):
    pass


class QuitGame(Exception):
    pass


class SilentSound:
    def play(self):
        pass

    def set_volume(self, volume):
        pass


def initialize_pygame():
    global PYGAME_READY
    if PYGAME_READY:
        return
    pygame.init()
    pygame.joystick.init()
    PYGAME_READY = True


@dataclass
class Assets:
    pause: pygame.Surface
    blocks: pygame.Surface
    loading: pygame.Surface
    hp1: pygame.Surface
    hp2: pygame.Surface
    player1: pygame.Surface
    player2: pygame.Surface
    mage: pygame.Surface
    enemy: pygame.Surface


@dataclass
class Sounds:
    shoot_crash: object
    shoot: object
    player_death: object
    heal: object
    foe_hit: object


def resource_path(*parts):
    return str(BASE_DIR.joinpath(*parts))


def load_image(*parts):
    return pygame.image.load(resource_path(*parts)).convert_alpha()


def load_sound(*parts):
    if not pygame.mixer.get_init():
        return SilentSound()
    try:
        return pygame.mixer.Sound(resource_path(*parts))
    except pygame.error as exc:
        print(f"Could not load sound {'/'.join(parts)}: {exc}")
        return SilentSound()


def load_music(*parts):
    if not pygame.mixer.get_init():
        return False
    try:
        pygame.mixer.music.load(resource_path(*parts))
        return True
    except pygame.error as exc:
        print(f"Could not load music {'/'.join(parts)}: {exc}")
        return False


def resolve_key(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        name = value if value.startswith("K_") else f"K_{value}"
        try:
            return getattr(pygame, name)
        except AttributeError as exc:
            raise ValueError(f"Unknown pygame key name: {value}") from exc
    raise TypeError(f"Unsupported key value: {value!r}")


def resolve_keys(values):
    return [resolve_key(value) for value in values]


def clamp(value, low, high):
    return max(low, min(high, value))


class Animation:
    def __init__(self):
        self.step = 0
        self.tick = -1

    def frame(self, steps, width, period, y):
        self.tick += 1
        if self.tick >= max(1, period):
            self.tick = 0
            self.step = (self.step + 1) % steps
        return (-self.step * width, y)


class BackgroundSprite(pygame.sprite.Sprite):
    def __init__(self, game, image, rect, steps=0, period=5, line=0):
        super().__init__(game.background)
        self.game = game
        self.image = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        self.rect = pygame.Rect(rect)
        self.x = rect[0]
        self.steps = steps
        self.sheet = image
        self.period = period
        self.line = -line
        self.animation = Animation() if steps else None

    def update(self):
        self.image.fill(TRANSPARENT)
        if self.animation:
            state = self.animation.frame(self.steps, self.rect.width, self.period, self.line)
        else:
            state = (0, 0)
        self.image.blit(self.sheet, state)
        self.rect.centerx = self.x + self.game.hero.x


class Block(pygame.sprite.Sprite):
    SPRITE_OFFSET = {
        "heal": (0, -BLOCK_SIDE),
        "goal": (-BLOCK_SIDE, -BLOCK_SIDE),
        "door": (-2 * BLOCK_SIDE, -BLOCK_SIDE),
        "ground": (-BLOCK_SIDE, 0),
        "platform": (0, 0),
        "wall": (-2 * BLOCK_SIDE, 0),
    }

    def __init__(self, game, info):
        super().__init__(game.solids)
        self.game = game
        self.kind = info[0]
        self.type = self.kind

        if self.kind in ("heal", "goal", "door"):
            game.items.add(self)
        if self.kind in ("ground", "wall"):
            game.blocks.add(self)
        if self.kind == "platform":
            game.platforms.add(self)
        if self.kind == "door":
            self.command = game.level + 10

        if self.kind not in self.SPRITE_OFFSET:
            raise ValueError(f"Unknown block type: {self.kind}")

        self.image = pygame.Surface(BLOCK_SIZE, pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.image.blit(game.assets.blocks, self.SPRITE_OFFSET[self.kind])
        self.x = info[1]
        self.rect.centery = info[2]

    def update(self):
        self.rect.centerx = self.x + self.game.hero.x
        if self.kind != "platform" and pygame.sprite.spritecollide(self, self.game.attacks, True):
            self.game.sounds.shoot_crash.play()


class Attack(pygame.sprite.Sprite):
    def __init__(self, game, player):
        super().__init__(game.attacks)
        self.game = game
        size = BLOCK_SIDE // 6
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()

        distance = BLOCK_SIDE / 1.5
        self.x = player.x + distance * player.direction[0]
        self.rect.centerx = int(player.rect.centerx + distance * player.facing)
        self.rect.centery = player.rect.centery
        x_velocity = player.direction[0] if player.direction[1] else player.facing
        self.velocity = (x_velocity, player.direction[1])
        self.speed = 20
        self.life = 30
        game.sounds.shoot.play()

    def update(self):
        hero = self.game.hero
        camera_drift = (not hero.standing) * hero.direction[0] * hero.speed
        self.rect.centerx += self.speed * self.velocity[0] + camera_drift
        self.rect.centery -= self.speed * self.velocity[1]
        self.life -= 1
        if self.life < 0:
            self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self, game, x0, y0, sheet, keyboard, keys, joystick_index=0):
        super().__init__(game.players)
        self.game = game
        self.image = pygame.Surface(BLOCK_SIZE, pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.sheet = sheet
        self.x = x0
        self.rect.centerx = x0
        self.rect.centery = y0

        self.accel = 0
        self.speed = -10
        self.jump = -16
        self.hp = MAX_HP
        self.magic = 25
        self.in_land = False
        self.fall = 0
        self.contacts = [None] * 8
        self.animation_state = Animation()

        self.keyboard = keyboard
        self.path = keys
        self.joystick = None
        if not self.keyboard:
            self.configure_joystick(joystick_index)

        self.direction = [0, 0]
        self.facing = 1
        self.clear_actions()

    def configure_joystick(self, joystick_index):
        if joystick_index < pygame.joystick.get_count():
            self.joystick = pygame.joystick.Joystick(joystick_index)
            self.joystick.init()
        else:
            print(f"Joystick {joystick_index} unavailable; falling back to keyboard")
            self.keyboard = True

    def clear_actions(self):
        self.shoot = False
        self.use = False
        self.standing = False
        self.resurrect = False
        self.teleport = False
        self.pause_request = False

    def joystick_button(self, index):
        return self.joystick.get_numbuttons() > index and self.joystick.get_button(index)

    def joystick_hat(self):
        if self.joystick.get_numhats() == 0:
            return (0, 0)
        return self.joystick.get_hat(0)

    def joystick_axis(self, index):
        if self.joystick.get_numaxes() <= index:
            return 0
        return self.joystick.get_axis(index)

    def control(self):
        self.clear_actions()
        if self.keyboard:
            held = self.game.held_keys
            pressed = self.game.pressed_keys
            self.shoot = self.path[KEY_SHOOT] in pressed
            self.use = self.path[KEY_USE] in pressed
            self.standing = self.path[KEY_STAND] in held
            self.resurrect = self.path[KEY_RESURRECT] in pressed
            self.teleport = self.path[KEY_TELEPORT] in pressed
            self.pause_request = self.path[KEY_PAUSE] in held

            right = self.path[KEY_RIGHT] in held
            left = self.path[KEY_LEFT] in held
            up = self.path[KEY_UP] in held
            down = self.path[KEY_DOWN] in held
            self.direction[0] = int(right) - int(left)
            self.direction[1] = int(up) - int(down)
        elif self.joystick is not None:
            self.shoot = self.joystick_button(3)
            self.use = self.joystick_button(4)
            self.standing = self.joystick_button(5)
            self.resurrect = self.joystick_button(6)
            self.teleport = self.joystick_button(7)
            self.pause_request = self.joystick_button(9)
            hat = self.joystick_hat()
            self.direction[0] = int(hat[0] * 1.5)
            if self.direction[0] == 0:
                self.direction[0] = int(self.joystick_axis(0) * 1.5)
            self.direction[1] = int(hat[1] * 1.5)
            if self.direction[1] == 0:
                self.direction[1] = -int(self.joystick_axis(1) * 1.5)

        if self.direction[0]:
            self.facing = self.direction[0]

    def contact(self):
        self.contacts = [None] * 8
        for thing in pygame.sprite.spritecollide(self, self.game.solids, False):
            if thing.rect.collidepoint(self.rect.topleft):
                self.contacts[0] = thing
            if thing.rect.collidepoint(self.rect.midtop):
                self.contacts[1] = thing
            if thing.rect.collidepoint(self.rect.topright):
                self.contacts[2] = thing
            if thing.rect.collidepoint(self.rect.midright):
                self.contacts[3] = thing
            if thing.rect.collidepoint(self.rect.bottomright):
                self.contacts[4] = thing
            if thing.rect.collidepoint(self.rect.midbottom):
                self.contacts[5] = thing
            if thing.rect.collidepoint(self.rect.bottomleft):
                self.contacts[6] = thing
            if thing.rect.collidepoint(self.rect.midleft):
                self.contacts[7] = thing

    def physics(self):
        self.in_land = False
        self.fall -= self.fall > 0
        drop = self.fall > 0
        jump = self.accel < 0

        right_contact = self.contacts[3]
        left_contact = self.contacts[7]
        top_contact = self.contacts[1]
        bottom_contact = self.contacts[5]

        if right_contact in self.game.blocks:
            if self == self.game.hero and self.rect.centerx == self.game.size_x / 2:
                self.x -= right_contact.rect.left - self.rect.right
            else:
                self.rect.right = right_contact.rect.left
                if self is not self.game.hero:
                    self.x = self.rect.centerx - self.game.hero.x

        if left_contact in self.game.blocks:
            if self == self.game.hero and self.rect.centerx == self.game.size_x / 2:
                self.x -= left_contact.rect.right - self.rect.left
            else:
                self.rect.left = left_contact.rect.right
                if self is not self.game.hero:
                    self.x = self.rect.centerx - self.game.hero.x

        if top_contact in self.game.blocks and jump:
            self.rect.top = top_contact.rect.bottom
            self.accel = 0

        platform_contact = bottom_contact in self.game.platforms and not (drop or jump)
        if bottom_contact in self.game.blocks or platform_contact:
            self.rect.bottom = bottom_contact.rect.top
            self.accel = 0
            self.in_land = True

    def motion(self):
        if not self.standing:
            if self.in_land:
                if self.direction[1] > 0:
                    self.accel = self.jump
                elif self.direction[1] < 0:
                    self.fall = 17

            change = self.speed * self.direction[0]
            if self == self.game.hero:
                if self.x > -self.game.edge or self.rect.centerx < self.game.size_x / 2:
                    self.x = -self.game.edge
                    self.rect.centerx -= change
                    if self.rect.left < 0:
                        self.rect.left = 0
                else:
                    self.x += change
            else:
                self.x -= change
                if self.x - BLOCK_SIDE / 2 < self.game.edge:
                    self.x = self.game.edge + BLOCK_SIDE / 2
                self.rect.centerx = self.x + self.game.hero.x

        self.accel += GRAVITY * (self.accel < 23)
        self.rect.centery += self.accel

    def get_hit(self):
        if pygame.sprite.spritecollide(self, self.game.enemies, False):
            self.hp -= 1 + int(self.standing)
        if self.hp <= 0 or self.rect.centery >= self.game.size_y:
            self.hp = 0
            self.magic = 0
            print(f"Player died at x={self.x}")
            self.kill()
            self.game.death.add(self)
            self.game.sounds.player_death.play()

    def spell(self):
        current_magic = self.magic
        if self.magic < MAX_MAGIC:
            self.magic = min(MAX_MAGIC, self.magic + 0.1)

        if self.teleport and self != self.game.hero and self.magic >= MAX_MAGIC:
            self.magic -= MAX_MAGIC
            self.x = self.game.hero.rect.centerx - self.game.hero.x
            self.rect.center = self.game.hero.rect.center

        if self.shoot and current_magic > 5:
            Attack(self.game, self)
            self.magic -= 5

        if self.resurrect and any(self.game.death) and self.magic >= 26:
            self.magic -= 26
            self.hp //= 2
            revived_player = self.game.death.sprites()[0]
            revived_player.x = -self.game.hero.x + self.game.hero.rect.centerx
            revived_player.rect.center = self.rect.center
            revived_player.hp = self.hp
            self.game.players.add(revived_player)
            self.game.death.empty()

    def bonus(self):
        for item in pygame.sprite.spritecollide(self, self.game.items, False):
            if item.type == "goal":
                self.game.progress["level"] = next_level(self.game.level)
                save_progress(self.game.progress, self.game.progress_file)
                raise RestartGame
            if item.type == "heal":
                item.kill()
                self.game.sounds.heal.play()
                self.hp = MAX_HP
            if item.type == "door" and self.use:
                if self == self.game.hero:
                    self.x -= item.command * BLOCK_SIDE - self.game.size_x / 2 + self.rect.centerx
                    self.rect.centerx = self.game.size_x / 2
                else:
                    self.x += item.command * BLOCK_SIDE + self.game.size_x / 2

    def animate(self):
        self.image.fill(TRANSPARENT)
        line = 0 if self.in_land else -1
        state = self.animation_state.frame(8, self.rect.width, 5, line * self.rect.height)
        sheet = self.sheet
        if self.facing < 0:
            sheet = pygame.transform.flip(self.sheet, True, False)
        self.image.blit(sheet, state)

    def update(self):
        if self in self.game.death:
            return
        self.control()
        self.get_hit()
        if self in self.game.death:
            return
        self.bonus()
        self.motion()
        self.spell()
        self.contact()
        self.physics()
        self.animate()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, game, x0=100, y0=0):
        super().__init__(game.enemies)
        self.game = game
        self.speed = game.rng.choice((-3, -2, -1, 1, 2, 3))
        self.hp = game.rng.randint(1, 3)
        self.image = pygame.Surface(BLOCK_SIZE, pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.height -= 10
        self.x = x0
        self.rect.centerx = x0
        self.rect.centery = y0
        self.accel = 0
        self.contacts = [None] * 8
        self.animation_state = Animation()
        self.dying = False

    def contact(self):
        self.contacts = [None] * 8
        candidates = pygame.sprite.spritecollide(self, self.game.blocks, False)
        candidates += pygame.sprite.spritecollide(self, self.game.platforms, False)
        for thing in candidates:
            if thing.rect.collidepoint(self.rect.midright):
                self.contacts[3] = thing
            if thing.rect.collidepoint(self.rect.midbottom):
                self.contacts[5] = thing
            if thing.rect.collidepoint(self.rect.midleft):
                self.contacts[7] = thing

    def physics(self):
        if self.contacts[7]:
            self.speed = self.game.rng.randint(1, 3)
            self.rect.left = self.contacts[7].rect.right
        if self.contacts[3] in self.game.blocks:
            self.speed = -self.game.rng.randint(1, 3)
            self.rect.right = self.contacts[3].rect.left
        if self.contacts[5] in self.game.blocks or self.contacts[5] in self.game.platforms:
            self.rect.bottom = self.contacts[5].rect.top
            self.accel = 0

    def move(self):
        self.x += self.speed
        self.rect.centerx = self.x + self.game.hero.x
        self.accel += GRAVITY * (self.accel < 20)
        self.rect.centery += self.accel

    def hit(self):
        if pygame.sprite.spritecollide(self, self.game.attacks, True):
            self.hp -= 1
            self.game.sounds.foe_hit.play()
        if self.hp <= 0 or self.rect.y > self.game.size_y:
            self.die()

    def die(self):
        if self.dying:
            return
        self.dying = True
        self.speed = 0
        self.accel = 0
        self.game.enemies.remove(self)
        self.game.background.add(self)

    def animate(self):
        self.image.fill(TRANSPARENT)
        if self.dying:
            state = self.animation_state.frame(4, self.rect.width, 5, -BLOCK_SIDE)
            if state == (-3 * BLOCK_SIDE, -BLOCK_SIDE):
                print("A monster has died")
                self.kill()
                return
        else:
            state = self.animation_state.frame(2, self.rect.width, abs(self.speed * 2), 0)

        sheet = self.game.assets.enemy
        if self.speed > 0:
            sheet = pygame.transform.flip(sheet, True, False)
        self.image.blit(sheet, state)

    def update(self):
        if not self.dying:
            self.contact()
            self.physics()
            self.hit()
            self.move()
        self.animate()


class GameSession:
    def __init__(self, level=None, max_frames=None, music_enabled=True):
        initialize_pygame()
        self.progress, self.progress_file = load_progress()
        self.size_x = self.progress["sizeX"]
        self.size_y = self.progress["sizeY"]
        self.fps = self.progress["FPS"]
        self.level = level or self.progress["level"]
        self.max_frames = max_frames
        self.music_enabled = bool(self.progress["music"] and music_enabled)
        self.rng = random.Random()

        self.screen = pygame.display.set_mode((self.size_x, self.size_y), pygame.RESIZABLE)
        pygame.display.set_caption("Mega Game From Outer Space")
        self.clock = pygame.time.Clock()

        self.assets = self.load_assets()
        self.sounds = self.load_sounds()
        self.music_loaded = self.music_enabled and load_music("sound", "music", "Paint It Black.mp3")
        if self.music_loaded:
            pygame.mixer.music.set_volume(0.3)

        self.blocks = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.players = pygame.sprite.Group()
        self.death = pygame.sprite.GroupSingle()
        self.attacks = pygame.sprite.Group()
        self.items = pygame.sprite.Group()
        self.background = pygame.sprite.Group()
        self.solids = pygame.sprite.Group()

        self.pending_blocks, self.pending_foes, self.pending_background = build_level(
            self.level,
            self.size_y,
        )
        self.pending_blocks = list(self.pending_blocks)
        self.pending_foes = list(self.pending_foes)
        self.pending_background = list(self.pending_background)

        self.hero = None
        self.player1 = None
        self.player2 = None
        self.edge = 0
        self.pause = False
        self.held_keys = set()
        self.pressed_keys = set()

        self.create_players()

    def load_assets(self):
        return Assets(
            pause=load_image("img", "64", "Pause.png"),
            blocks=load_image("img", "64", "Blocks.png"),
            loading=load_image("img", "64", "Loading.png"),
            hp1=load_image("img", "64", "Hp.png"),
            hp2=load_image("img", "64", "Hp.png"),
            player1=load_image("img", "64", "andromalius-57x88.png"),
            player2=load_image("img", "64", "andromalius-57x88.png"),
            mage=load_image("img", "64", "mage-3-87x110.png"),
            enemy=load_image("img", "64", "Slime.png"),
        )

    def load_sounds(self):
        sounds = Sounds(
            shoot_crash=load_sound("sound", "effects", "shoot_crash.wav"),
            shoot=load_sound("sound", "effects", "shoot.wav"),
            player_death=load_sound("sound", "effects", "player_death.wav"),
            heal=load_sound("sound", "effects", "hp_bonus.wav"),
            foe_hit=load_sound("sound", "effects", "foe_hit.wav"),
        )
        for sound in (
            sounds.shoot_crash,
            sounds.shoot,
            sounds.player_death,
            sounds.heal,
            sounds.foe_hit,
        ):
            sound.set_volume(1)
        return sounds

    def create_players(self):
        p1_keys = resolve_keys(self.progress["P1_keys"])
        p2_keys = resolve_keys(self.progress["P2_keys"])
        self.player1 = Player(
            self,
            300,
            self.size_y / 2,
            self.assets.player1,
            self.progress["P1_keyboard"],
            p1_keys,
            joystick_index=0,
        )
        self.player1.x = 0
        self.hero = self.player1

        if self.progress["multiplayer"]:
            self.player2 = Player(
                self,
                300,
                self.size_y / 2,
                self.assets.player2,
                self.progress["P2_keyboard"],
                p2_keys,
                joystick_index=1,
            )

    def show_loading(self):
        self.screen.fill(BLACK)
        self.screen.blit(self.assets.loading, (0, 0))
        pygame.display.update()

    def handle_events(self):
        self.pressed_keys = set()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise QuitGame
            if event.type == pygame.KEYDOWN:
                self.held_keys.add(event.key)
                self.pressed_keys.add(event.key)
                if event.key == pygame.K_F1:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_F2:
                    self.toggle_pause()
            elif event.type == pygame.KEYUP:
                self.held_keys.discard(event.key)
            elif event.type == pygame.VIDEORESIZE:
                self.size_x, self.size_y = event.size
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

    def toggle_pause(self):
        self.pause = not self.pause
        if self.music_loaded:
            if self.pause:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()

    def spawn_visible(self):
        left_bound = -self.hero.x - BLOCK_SIDE
        right_bound = self.size_x - self.hero.x + BLOCK_SIDE

        self.pending_blocks = self.spawn_from_pending(
            self.pending_blocks,
            left_bound,
            right_bound,
            lambda item: Block(self, item),
        )
        self.pending_foes = self.spawn_from_pending(
            self.pending_foes,
            left_bound,
            right_bound,
            lambda item: Enemy(self, item[1], item[2]),
        )
        self.pending_background = self.spawn_from_pending(
            self.pending_background,
            left_bound,
            right_bound,
            self.spawn_background,
        )

    def spawn_from_pending(self, pending, left_bound, right_bound, factory):
        remaining = []
        for item in pending:
            if left_bound <= item[1] <= right_bound:
                factory(item)
            else:
                remaining.append(item)
        return remaining

    def spawn_background(self, item):
        if item[0] != "mage":
            return
        BackgroundSprite(
            self,
            self.assets.mage,
            [item[1], item[2], 87, 110],
            steps=4,
            period=10,
        )

    def cull_old_sprites(self):
        cutoff = self.edge - self.size_x / 2
        for group in (self.solids, self.background):
            for sprite in group:
                if getattr(sprite, "x", 0) < cutoff:
                    sprite.kill()

    def focus_live_player(self):
        if self.hero in self.death:
            self.hero = self.players.sprites()[0]
            self.hero.x = self.size_x / 2 - self.hero.x
            cornered = (self.edge + self.hero.x > 0) * (self.edge + self.hero.x)
            self.hero.rect.centerx = self.size_x / 2 - cornered

    def update_edge(self):
        if len(self.players) == 1 and self.edge < -self.hero.x:
            self.edge = -self.hero.x
        elif len(self.players) == 2 and self.player2 is not None:
            self.edge = min(self.edge, -self.hero.x, self.player2.x - self.size_x / 2)

    def draw_meter(self, x, y, value, maximum, color):
        width = 220
        height = 10
        fill_width = int(width * clamp(value, 0, maximum) / maximum)
        pygame.draw.rect(self.screen, (20, 20, 20), [x, y, width, height], 0)
        pygame.draw.rect(self.screen, color, [x, y, fill_width, height], 0)

    def draw_player_hud(self, player, image, x, y, hp_color):
        self.screen.blit(image, (x, y))
        hp = clamp(player.hp, 0, MAX_HP)
        magic = clamp(player.magic, 0, MAX_MAGIC)
        self.draw_meter(x + 88, y + 48, hp, MAX_HP, hp_color(hp))
        self.draw_meter(x + 88, y + 81, magic, MAX_MAGIC, (0, int(50 - magic), int(magic * 5)))

    def draw_hud(self):
        p1_x = max(10, self.size_x - 320)
        if self.player1 is not None:
            self.draw_player_hud(
                self.player1,
                self.assets.hp1,
                p1_x,
                10,
                lambda hp: (int(hp * 5), int(50 - hp), 0),
            )
        if self.player2 is not None:
            self.draw_player_hud(
                self.player2,
                self.assets.hp2,
                10,
                0,
                lambda hp: (int(hp * 5), 0, int(50 - hp)),
            )

    def draw_active_frame(self):
        self.screen.fill(SKY)
        self.draw_hud()
        self.background.update()
        self.players.update()
        self.enemies.update()
        self.attacks.update()
        self.solids.update()
        self.background.draw(self.screen)
        self.attacks.draw(self.screen)
        self.solids.draw(self.screen)
        self.enemies.draw(self.screen)
        self.players.draw(self.screen)

    def draw_pause_frame(self):
        self.screen.blit(self.assets.pause, (0, 0))
        for player in self.players:
            player.control()
            if player.pause_request:
                print("continue")
                self.toggle_pause()
            elif player.direction[0] < 0:
                print("restart")
                raise RestartGame
            elif player.direction[1] > 0:
                print("options")
            elif player.direction[1] < 0:
                print("quit")
                raise QuitGame

    def run(self):
        self.show_loading()
        if self.music_loaded:
            pygame.mixer.music.play(-1)
        print("This amazing adventure begins!")

        frame_count = 0
        while True:
            self.handle_events()
            if not any(self.players):
                if pygame.mixer.get_init():
                    pygame.mixer.stop()
                raise RestartGame

            self.spawn_visible()
            self.cull_old_sprites()
            self.focus_live_player()
            self.update_edge()

            if self.pause:
                self.draw_pause_frame()
            else:
                self.draw_active_frame()

            self.clock.tick(self.fps)
            pygame.display.update()
            frame_count += 1
            if self.max_frames is not None and frame_count >= self.max_frames:
                return


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Mega Game From Outer Space")
    parser.add_argument(
        "--smoke-test",
        nargs="?",
        const=120,
        type=int,
        help="run for N frames with dummy SDL drivers, then exit",
    )
    parser.add_argument("--level", type=int, help="start a specific level")
    parser.add_argument("--no-music", action="store_true", help="disable music")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    max_frames = args.smoke_test
    music_enabled = not args.no_music and max_frames is None
    level = args.level

    while True:
        try:
            GameSession(level=level, max_frames=max_frames, music_enabled=music_enabled).run()
            return 0
        except RestartGame:
            if max_frames is not None:
                return 0
            level = None
        except QuitGame:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
