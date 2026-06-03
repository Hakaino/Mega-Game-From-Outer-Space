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
    available_levels,
    build_level,
    load_progress,
    next_level,
    save_progress,
)


PYGAME_READY = False

BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
CYAN = (60, 220, 255)
GOLD = (255, 200, 70)
GREEN = (70, 220, 120)
RED = (230, 80, 80)
SKY = (60, 95, 140)
TRANSPARENT = (0, 0, 0, 0)
WHITE = (245, 248, 255)
PANEL = (12, 18, 28, 220)

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
    def __init__(self, level=None):
        super().__init__()
        self.level = level


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
    world_background: pygame.Surface
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
        self.decorate()
        self.x = info[1]
        self.rect.centery = info[2]

    def decorate(self):
        if self.kind == "goal":
            pygame.draw.circle(self.image, GOLD, (BLOCK_SIDE // 2, BLOCK_SIDE // 2), 25, 4)
            pygame.draw.circle(self.image, (255, 245, 160, 110), (BLOCK_SIDE // 2, BLOCK_SIDE // 2), 14)
        elif self.kind == "door":
            pygame.draw.rect(self.image, CYAN, [12, 6, 40, 52], 3, border_radius=4)
            pygame.draw.circle(self.image, CYAN, (44, 34), 3)
        elif self.kind == "heal":
            pygame.draw.rect(self.image, RED, [28, 14, 8, 36])
            pygame.draw.rect(self.image, RED, [14, 28, 36, 8])
        elif self.kind == "platform":
            pygame.draw.line(self.image, (210, 230, 240), (5, 10), (58, 10), 2)

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
        center = (size // 2, size // 2)
        pygame.draw.circle(self.image, (90, 190, 255), center, size // 2)
        pygame.draw.circle(self.image, (220, 245, 255), center, max(1, size // 3))
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
                next_level_number = next_level(self.game.level)
                self.game.progress["level"] = next_level_number
                save_progress(self.game.progress, self.game.progress_file)
                print(f"Level {self.game.level} complete. Next level: {next_level_number}")
                raise RestartGame(next_level_number)
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
        self.font = pygame.font.SysFont("arial", 22)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.title_font = pygame.font.SysFont("arial", 38, bold=True)
        self.pause_options = [
            ("Resume", "resume"),
            ("Restart Level", "restart"),
            ("Quit Game", "quit"),
        ]
        self.pause_index = 0
        self.pause_snapshot = None
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
            world_background=load_image("img", "64", "Background 1.png"),
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
                if self.pause:
                    self.handle_pause_key(event.key)
                elif event.key == pygame.K_F1:
                    pygame.display.toggle_fullscreen()
                elif event.key in (pygame.K_F2, pygame.K_ESCAPE):
                    self.open_pause()
            elif event.type == pygame.KEYUP:
                self.held_keys.discard(event.key)
            elif event.type == pygame.VIDEORESIZE:
                self.size_x, self.size_y = event.size
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

    def open_pause(self):
        self.pause = True
        self.pause_index = 0
        self.pause_snapshot = self.screen.copy()
        if self.music_loaded:
            pygame.mixer.music.pause()

    def close_pause(self):
        self.pause = False
        self.pause_snapshot = None
        self.held_keys.clear()
        self.pressed_keys.clear()
        if self.music_loaded:
            pygame.mixer.music.unpause()

    def handle_pause_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_F2):
            self.close_pause()
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.pause_index = (self.pause_index + 1) % len(self.pause_options)
        elif key in (pygame.K_UP, pygame.K_w):
            self.pause_index = (self.pause_index - 1) % len(self.pause_options)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_g):
            self.activate_pause_option()

    def activate_pause_option(self):
        action = self.pause_options[self.pause_index][1]
        if action == "resume":
            self.close_pause()
        elif action == "restart":
            print("restart")
            raise RestartGame(self.level)
        elif action == "quit":
            print("quit")
            raise QuitGame

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
        pygame.draw.rect(self.screen, (15, 20, 30), [x, y, width, height], 0, border_radius=4)
        pygame.draw.rect(self.screen, color, [x, y, fill_width, height], 0, border_radius=4)
        pygame.draw.rect(self.screen, (220, 230, 240), [x, y, width, height], 1, border_radius=4)

    def draw_player_hud(self, player, image, x, y, hp_color):
        panel = pygame.Surface((308, 112), pygame.SRCALPHA)
        panel.fill((8, 14, 24, 160))
        pygame.draw.rect(panel, (160, 185, 210), panel.get_rect(), 1, border_radius=6)
        self.screen.blit(panel, (x, y))
        self.screen.blit(image, (x, y))
        hp = clamp(player.hp, 0, MAX_HP)
        magic = clamp(player.magic, 0, MAX_MAGIC)
        self.draw_text("HP", x + 88, y + 25, self.small_font)
        self.draw_text("Magic", x + 88, y + 62, self.small_font)
        self.draw_meter(x + 88, y + 48, hp, MAX_HP, hp_color(hp))
        self.draw_meter(x + 88, y + 81, magic, MAX_MAGIC, (0, int(50 - magic), int(magic * 5)))

    def draw_text(self, text, x, y, font=None, color=WHITE):
        font = font or self.font
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))

    def draw_hud(self):
        self.draw_text(f"Level {self.level}", 18, 14, self.font)
        self.draw_text("Reach the glowing exit portal", 18, 40, self.small_font, (215, 230, 245))
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

    def draw_world_background(self):
        self.screen.fill(SKY)
        bg = self.assets.world_background
        width = bg.get_width()
        y = max(0, self.size_y - bg.get_height())
        offset = int((self.hero.x * 0.18) % width)
        x = -offset
        while x < self.size_x:
            self.screen.blit(bg, (x, y))
            x += width

    def draw_active_frame(self):
        self.draw_world_background()
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
        self.draw_hud()

    def draw_pause_frame(self):
        if self.pause_snapshot:
            self.screen.blit(self.pause_snapshot, (0, 0))
        else:
            self.draw_world_background()

        shade = pygame.Surface((self.size_x, self.size_y), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 155))
        self.screen.blit(shade, (0, 0))

        panel_width = min(460, self.size_x - 40)
        panel_height = 300
        panel_rect = pygame.Rect(
            (self.size_x - panel_width) // 2,
            (self.size_y - panel_height) // 2,
            panel_width,
            panel_height,
        )
        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel.fill(PANEL)
        pygame.draw.rect(panel, (160, 190, 220), panel.get_rect(), 1, border_radius=8)
        self.screen.blit(panel, panel_rect)

        title = self.title_font.render("Paused", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(self.size_x // 2, panel_rect.top + 55)))

        for index, (label, _action) in enumerate(self.pause_options):
            option_rect = pygame.Rect(panel_rect.left + 50, panel_rect.top + 105 + index * 52, panel_width - 100, 40)
            selected = index == self.pause_index
            if selected:
                pygame.draw.rect(self.screen, GOLD, option_rect, 0, border_radius=5)
            pygame.draw.rect(self.screen, (210, 225, 240), option_rect, 1, border_radius=5)
            color = BLACK if selected else WHITE
            text = self.font.render(label, True, color)
            self.screen.blit(text, text.get_rect(center=option_rect.center))

        hint = self.small_font.render("Up/Down select    Enter choose    Esc resume", True, (210, 220, 235))
        self.screen.blit(hint, hint.get_rect(center=(self.size_x // 2, panel_rect.bottom - 30)))

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
        except RestartGame as exc:
            if max_frames is not None:
                return 0
            level = exc.level
        except QuitGame:
            pygame.quit()
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
