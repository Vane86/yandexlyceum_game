import pygame
from itertools import product
from PIL import Image

import os
import math

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

    def get_position(self):
        return -self._canvas_offset[0] + self._screen_size[0] // 2, -self._canvas_offset[1] + self._screen_size[1] // 2

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

    def get_sprite(self):
        return self._sprite


class GameWorldTile:

    def __init__(self, world_position, type, sprite_group):  # types: 0 - floor, 1 - wall
        self._type = type
        self._sprite = pygame.sprite.Sprite()
        self._sprite.image = pygame.image.load(os.path.join('resources', 'textures', 'tile' + str(type) + '.png'))
        self._sprite.image = pygame.transform.scale(self._sprite.image, (WORLD_TILE_SIZE, WORLD_TILE_SIZE))
        self._sprite.rect = self._sprite.image.get_rect(center=(int((world_position[0] + 0.5) * WORLD_TILE_SIZE),
                                                                int((world_position[1] + 0.5) * WORLD_TILE_SIZE)))
        sprite_group.add(self._sprite)

    def get_sprite(self):
        return self._sprite

    def get_type(self):
        return self._type


class GameWorld:

    def __init__(self, map_image_path, screen_size):
        map_image = Image.open(map_image_path)
        self._size = map_image.size
        self._tiles = [[None] * self._size[1] for _ in range(self._size[0])]
        scr_sz_t = (math.ceil(screen_size[0] / WORLD_TILE_SIZE), math.ceil(screen_size[1] / WORLD_TILE_SIZE))
        self._tile_chunks = [[pygame.sprite.Group() for __ in range(math.ceil(self._size[1] / scr_sz_t[1]))]
                             for _ in range(math.ceil(self._size[0] / scr_sz_t[0]))]
        self._chunk_size_tiles = scr_sz_t
        self._player_position = (0, 0)
        for x, y in product(*map(range, self._size)):
            tile_color = map_image.getpixel((x, y))
            tl_chk_xy = (x // scr_sz_t[0], y // scr_sz_t[1])
            if tile_color[0] == tile_color[1] == tile_color[2] == 255:
                self._tiles[x][y] = GameWorldTile((x, y), 1, self._tile_chunks[tl_chk_xy[0]][tl_chk_xy[1]])
            elif tile_color[0] == tile_color[1] == tile_color[2] == 0:
                self._tiles[x][y] = GameWorldTile((x, y), 0, self._tile_chunks[tl_chk_xy[0]][tl_chk_xy[1]])
            elif tile_color[0] == tile_color[2] == 0 and tile_color[1] == 255:
                self._tiles[x][y] = GameWorldTile((x, y), 0, self._tile_chunks[tl_chk_xy[0]][tl_chk_xy[1]])
                self._player_position = (x * WORLD_TILE_SIZE, y * WORLD_TILE_SIZE)

    def _is_correct_chunk_coords(self, x, y):
        return not (y >= len(self._tile_chunks[x]) or y < 0 or x >= len(self._tile_chunks) or x < 0)

    def _is_correct_tile_coords(self, x, y):
        return not (x < 0 or x >= self._size[0] or y < 0 or y >= self._size[1])

    def _get_chunks_around_pos(self, pos_tiles):
        ccp = (pos_tiles[0] // self._chunk_size_tiles[0],
               pos_tiles[1] // self._chunk_size_tiles[1])
        return [self._tile_chunks[x][y] for x, y in product(range(ccp[0] - 1, ccp[0] + 2),
                                                            range(ccp[1] - 1, ccp[1] + 2))
                if self._is_correct_chunk_coords(x, y)]

    def check_collisions_and_fix_move_vector(self, entity_sprite, entity_move):
        result_move = [0, 0]
        start_pos = entity_sprite.rect.center
        start_pos_tiles = start_pos[0] // WORLD_TILE_SIZE, start_pos[1] // WORLD_TILE_SIZE
        entity_sprite.rect.move_ip(entity_move[0], 0)
        for x, y in product(range(start_pos_tiles[0] - 1, start_pos_tiles[0] + 2),
                            range(start_pos_tiles[1] - 1, start_pos_tiles[1] + 2)):
            if self._is_correct_tile_coords(x, y) and self._tiles[x][y].get_type() == 1:
                if pygame.sprite.collide_rect(entity_sprite, self._tiles[x][y].get_sprite()):
                    break
        else:
            result_move[0] = entity_move[0]
        entity_sprite.rect.move_ip(0, entity_move[1])
        for x, y in product(range(start_pos_tiles[0] - 1, start_pos_tiles[0] + 2),
                            range(start_pos_tiles[1] - 1, start_pos_tiles[1] + 2)):
            if self._is_correct_tile_coords(x, y) and self._tiles[x][y].get_type() == 1:
                if pygame.sprite.collide_rect(entity_sprite, self._tiles[x][y].get_sprite()):
                    break
        else:
            result_move[1] = entity_move[1]
        entity_sprite.rect.center = start_pos
        return tuple(result_move)

    def draw(self, camera, surface):
        camera_pos = camera.get_position()
        chunks_around_camera = self._get_chunks_around_pos((camera_pos[0] // WORLD_TILE_SIZE,
                                                            camera_pos[1] // WORLD_TILE_SIZE))
        for chunk in chunks_around_camera:
            chunk.draw(surface)

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

    world = GameWorld(os.path.join('resources', WORLD_MAP_NAME), DISPLAY_SIZE)
    player = Player(world.get_player_position(), dynamic_sprite_group)
    camera = Camera((world.get_size()[0] * WORLD_TILE_SIZE, world.get_size()[1] * WORLD_TILE_SIZE),
                    DISPLAY_SIZE,
                    player.get_position())

    canvas = pygame.Surface((world.get_size()[0] * WORLD_TILE_SIZE, world.get_size()[1] * WORLD_TILE_SIZE))
    pass


def loop(dt, events):
    for event in events:
        if event.type == pygame.QUIT:
            return False

    keys_pressed = pygame.key.get_pressed()
    if keys_pressed[pygame.K_w]:
        move_vector = world.check_collisions_and_fix_move_vector(player.get_sprite(), (0, -PLAYER_SPEED * dt / 1000))
        player.move(move_vector)
    elif keys_pressed[pygame.K_s]:
        move_vector = world.check_collisions_and_fix_move_vector(player.get_sprite(), (0, PLAYER_SPEED * dt / 1000))
        player.move(move_vector)
    if keys_pressed[pygame.K_d]:
        move_vector = world.check_collisions_and_fix_move_vector(player.get_sprite(), (PLAYER_SPEED * dt / 1000, 0))
        player.move(move_vector)
    elif keys_pressed[pygame.K_a]:
        move_vector = world.check_collisions_and_fix_move_vector(player.get_sprite(), (-PLAYER_SPEED * dt / 1000, 0))
        player.move(move_vector)

    camera.set_position(player.get_position())
    world.draw(camera, canvas)
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
