import pygame
from itertools import product
from PIL import Image

import os

DISPLAY_SIZE = (640, 480)

WORLD_MAP_NAME = 'map.png'
WORLD_TILE_SIZE = 32

PLAYER_SPRITE_SIZE = 32
PLAYER_SPEED = 3 * WORLD_TILE_SIZE  # pixels per second


class Camera:

    def __init__(self, canvas_size, screen_size, position):
        self._canvas_size = canvas_size
        self._screen_size = screen_size
        self._canvas_offset = None
        self.set_position(position)

    def set_position(self, position):
        off_x = min(max(position[0] - self._screen_size[0] // 2, 0), self._canvas_size[0] - self._screen_size[0])
        off_y = min(max(position[1] - self._screen_size[1] // 2, 0), self._canvas_size[1] - self._screen_size[1])
        self._canvas_offset = (-off_x, -off_y)

    def get_canvas_offset(self):
        return self._canvas_offset


class Player:

    def __init__(self, position, sprite_group):
        self._sprite = pygame.sprite.Sprite()
        self._sprite.image = pygame.image.load(os.path.join('resources', 'textures', 'player.png'))
        self._sprite.image = pygame.transform.scale(self._sprite.image, (PLAYER_SPRITE_SIZE, PLAYER_SPRITE_SIZE))
        self._sprite.rect = self._sprite.image.get_rect(center=(position[0], position[1]))
        sprite_group.add(self._sprite)

    def set_position(self, position):
        self._sprite.rect.center = position

    def move(self, delta):
        self._sprite.rect.move_ip(*delta)

    def get_position(self):
        return self._sprite.rect.center


class GameWorldTile:

    def __init__(self, world_position, type, sprite_group):  # types: 0 - floor, 1 - wall
        self._type = type
        self._sprite = pygame.sprite.Sprite()
        self._sprite.image = pygame.image.load(os.path.join('resources', 'textures', 'tile' + str(type) + '.png'))
        self._sprite.image = pygame.transform.scale(self._sprite.image, (WORLD_TILE_SIZE, WORLD_TILE_SIZE))
        self._sprite.rect = self._sprite.image.get_rect(center=(int((world_position[0] + 0.5) * WORLD_TILE_SIZE),
                                                                int((world_position[1] + 0.5) * WORLD_TILE_SIZE)))
        sprite_group.add(self._sprite)

    def get_type(self):
        return self._type


class GameWorld:

    def __init__(self, map_image_path):
        map_image = Image.open(map_image_path)
        self._size = map_image.size
        self._tiles = [[None] * self._size[1] for _ in range(self._size[0])]
        self._tile_sprite_group = pygame.sprite.Group()
        self._player_position = (0, 0)
        for x, y in product(*map(range, self._size)):
            tile_color = map_image.getpixel((x, y))
            if tile_color[0] == tile_color[1] == tile_color[2] == 255:
                self._tiles[x][y] = GameWorldTile((x, y), 1, self._tile_sprite_group)
            elif tile_color[0] == tile_color[1] == tile_color[2] == 0:
                self._tiles[x][y] = GameWorldTile((x, y), 0, self._tile_sprite_group)
            elif tile_color[0] == tile_color[2] == 0 and tile_color[1] == 255:
                self._tiles[x][y] = GameWorldTile((x, y), 0, self._tile_sprite_group)
                self._player_position = (x * WORLD_TILE_SIZE, y * WORLD_TILE_SIZE)

    def draw(self, surface):
        self._tile_sprite_group.draw(surface)

    def get_player_position(self):
        return self._player_position

    def get_size(self):
        return self._size

    def get_tile(self, x, y):
        return self._tile[x][y]


screen = None

dynamic_sprite_group = None

world = None
player = None

canvas = None

camera = None


def setup():
    global screen, world, canvas, camera, player, dynamic_sprite_group

    pygame.init()
    screen = pygame.display.set_mode(DISPLAY_SIZE)

    dynamic_sprite_group = pygame.sprite.Group()

    world = GameWorld(os.path.join('resources', WORLD_MAP_NAME))
    player = Player(world.get_player_position(), dynamic_sprite_group)
    camera = Camera((world.get_size()[0] * WORLD_TILE_SIZE, world.get_size()[1] * WORLD_TILE_SIZE),
                    DISPLAY_SIZE,
                    player.get_position())

    canvas = pygame.Surface((world.get_size()[0] * WORLD_TILE_SIZE, world.get_size()[1] * WORLD_TILE_SIZE))
    pass


def loop(dt, events):
    global i

    for event in events:
        if event.type == pygame.QUIT:
            return False

    keys_pressed = pygame.key.get_pressed()
    if keys_pressed[pygame.K_w]:
        player.move((0, -PLAYER_SPEED * dt / 1000))
    elif keys_pressed[pygame.K_s]:
        player.move((0, PLAYER_SPEED * dt / 1000))
    if keys_pressed[pygame.K_d]:
        player.move((PLAYER_SPEED * dt / 1000, 0))
    elif keys_pressed[pygame.K_a]:
        player.move((-PLAYER_SPEED * dt / 1000, 0))

    camera.set_position(player.get_position())
    world.draw(canvas)
    dynamic_sprite_group.draw(canvas)
    screen.blit(canvas, camera.get_canvas_offset())
    return True


def clear():
    pygame.quit()


setup()

clock = pygame.time.Clock()

while True:

    dt = clock.tick()
    events = pygame.event.get()

    if not loop(dt, events):
        break

    pygame.display.flip()

clear()
