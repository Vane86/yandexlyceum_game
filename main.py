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

LIGHT_SOURCE_RADIUS = 7  # world tiles


class FPSCounter:

    def __init__(self):
        self._frames = 0
        self._time_passed = 0

    def update(self, dt):
        self._time_passed += dt
        self._frames += 1
        if self._time_passed >= 1000:
            self._time_passed = 0
            print(f'FPS: {self._frames}')
            self._frames = 0


class Camera:

    def __init__(self, canvas_size, screen_size, position):
        self._canvas_size = canvas_size
        self._screen_size = screen_size
        self._canvas_offset = None
        self.set_position(position)

    def set_position(self, position):
        off_x = min(max(position[0] - self._screen_size[0] // 2, 0), self._canvas_size[0] - self._screen_size[0])
        off_y = min(max(position[1] - self._screen_size[1] // 2, 0), self._canvas_size[1] - self._screen_size[1])
        self._canvas_offset = (off_x, off_y)

    def get_position(self):
        return self._canvas_offset[0] + self._screen_size[0] // 2, self._canvas_offset[1] + self._screen_size[1] // 2

    def get_canvas_offset(self):
        return self._canvas_offset


class LightSource:

    def __init__(self, position):
        self._old_position = position
        self._new_position = position

    def set_position(self, position):
        self._new_position = position

    def move(self, delta):
        self._new_position = self._new_position[0] + delta[0], self._new_position[1] + delta[1]

    def update(self):
        self._old_position = self._new_position

    def get_new_position(self):
        return self._new_position

    def get_old_position(self):
        return self._old_position


class Entity:

    def __init__(self, position, sprite_group):
        self._sprite = pygame.sprite.Sprite()
        self._sprite.image = pygame.image.load(os.path.join('resources', 'textures', 'player.png'))
        self._sprite.image = pygame.transform.scale(self._sprite.image, (PLAYER_SPRITE_SIZE, PLAYER_SPRITE_SIZE))
        self._sprite.rect = self._sprite.image.get_rect(center=(position[0], position[1]))
        self._position = position
        sprite_group.add(self._sprite)

    def set_position(self, position):
        self._sprite.rect.center = position
        self._position = position

    def move(self, delta):
        self._position = tuple(map(lambda x: x[0] + x[1], zip(self._position, delta)))
        self._sprite.rect.center = tuple(map(round, self._position))

    def get_position(self):
        return self._sprite.rect.center

    def get_sprite(self):
        return self._sprite


class Player(Entity):

    def __init__(self, position, sprite_group):
        super().__init__(position, sprite_group)
        self._light_source = LightSource(position)

    def set_position(self, position):
        super().set_position(position)
        self._light_source.set_position(position)

    def move(self, delta):
        super().move(delta)
        self._light_source.move(delta)

    def get_light_source(self):
        return self._light_source


class GameWorldTile:

    def __init__(self, world_position, type, darkness=1.0):  # types: 0 - floor, 1 - wall
        self._type = type
        self._sprite = pygame.sprite.Sprite()
        self._sprite.image = pygame.image.load(os.path.join('resources', 'textures', 'tile' + str(type) + '.png'))
        self._sprite.image = pygame.transform.scale(self._sprite.image, (WORLD_TILE_SIZE, WORLD_TILE_SIZE))
        self._sprite.rect = self._sprite.image.get_rect(center=(int((world_position[0] + 0.5) * WORLD_TILE_SIZE),
                                                                int((world_position[1] + 0.5) * WORLD_TILE_SIZE)))
        self._darkness = darkness

        self._surface_to_draw = pygame.Surface((WORLD_TILE_SIZE, WORLD_TILE_SIZE))
        self._surface_to_draw.fill((0, 0, 0))
        self._surface_to_draw.set_alpha(round(self._darkness * 25))

    def draw_light_mask(self, surface):
        self._surface_to_draw.set_alpha(round(self._darkness * 255))
        pos = self._sprite.rect.center[0] - WORLD_TILE_SIZE // 2, self._sprite.rect.center[1] - WORLD_TILE_SIZE // 2
        surface.blit(self._surface_to_draw, pos)

    def set_darkness(self, darkness):
        self._darkness = darkness

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
        self._tile_chunks = [[list() for __ in range(math.ceil(self._size[1] / scr_sz_t[1]))]
                             for _ in range(math.ceil(self._size[0] / scr_sz_t[0]))]
        self._chunk_size_tiles = scr_sz_t
        self._player_position = (0, 0)
        for x, y in product(*map(range, self._size)):
            tile_color = map_image.getpixel((x, y))
            tl_chk_xy = (x // scr_sz_t[0], y // scr_sz_t[1])
            if tile_color[0] == tile_color[1] == tile_color[2] == 255:
                self._tiles[x][y] = GameWorldTile((x, y), 1)
                self._tile_chunks[tl_chk_xy[0]][tl_chk_xy[1]].append(self._tiles[x][y])
            elif tile_color[0] == tile_color[1] == tile_color[2] == 0:
                self._tiles[x][y] = GameWorldTile((x, y), 0)
                self._tile_chunks[tl_chk_xy[0]][tl_chk_xy[1]].append(self._tiles[x][y])
            elif tile_color[0] == tile_color[2] == 0 and tile_color[1] == 255:
                self._tiles[x][y] = GameWorldTile((x, y), 0)
                self._tile_chunks[tl_chk_xy[0]][tl_chk_xy[1]].append(self._tiles[x][y])
                self._player_position = (x * WORLD_TILE_SIZE, y * WORLD_TILE_SIZE)
        self._light_sources = list()
        print(list(map(lambda x: (x.get_sprite().rect.center[0] // WORLD_TILE_SIZE, x.get_sprite().rect.center[1] // WORLD_TILE_SIZE), self._get_tiles_between((10, 10), (20, 20)))))

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

    def check_collisions_and_fix_move_vector(self, entity, entity_move):
        result_move = [0, 0]
        start_pos = entity.get_sprite().rect.center
        start_pos_tiles = start_pos[0] // WORLD_TILE_SIZE, start_pos[1] // WORLD_TILE_SIZE
        entity.move((entity_move[0], 0))
        for x, y in product(range(start_pos_tiles[0] - 1, start_pos_tiles[0] + 2),
                            range(start_pos_tiles[1] - 1, start_pos_tiles[1] + 2)):
            if self._is_correct_tile_coords(x, y) and self._tiles[x][y].get_type() == 1:
                if pygame.sprite.collide_rect(entity.get_sprite(), self._tiles[x][y].get_sprite()):
                    break
        else:
            result_move[0] = entity_move[0]
        entity.move((0, entity_move[1]))
        for x, y in product(range(start_pos_tiles[0] - 1, start_pos_tiles[0] + 2),
                            range(start_pos_tiles[1] - 1, start_pos_tiles[1] + 2)):
            if self._is_correct_tile_coords(x, y) and self._tiles[x][y].get_type() == 1:
                if pygame.sprite.collide_rect(entity.get_sprite(), self._tiles[x][y].get_sprite()):
                    break
        else:
            result_move[1] = entity_move[1]
        entity.set_position(start_pos)
        return tuple(result_move)

    def add_light_source(self, source):
        self._light_sources.append(source)

    def _get_tiles_between(self, pos1, pos2):
        dx, dy = pos1[0] - pos2[0], pos1[1] - pos2[1]
        L = max(abs(dx), abs(dy))
        if not L:
            return list()
        dx, dy = dx / L, dy / L
        result = list()
        x, y = pos2
        for i in range(L):
            if self._is_correct_tile_coords(x, y):
                result.append(self._tiles[round(x)][round(y)])
            x, y = x + dx, y + dy
        return result

    def _calculate_light_from_source(self, source):
        op = source.get_old_position()
        owp = int(op[0] // WORLD_TILE_SIZE), int(op[1] // WORLD_TILE_SIZE)
        for x, y in product(range(owp[0] - LIGHT_SOURCE_RADIUS, owp[0] + LIGHT_SOURCE_RADIUS + 1),
                            range(owp[1] - LIGHT_SOURCE_RADIUS, owp[1] + LIGHT_SOURCE_RADIUS + 1)):
            if not self._is_correct_tile_coords(x, y):
                continue
            self._tiles[x][y].set_darkness(1.0)
        np = source.get_new_position()
        nwp = int(np[0] // WORLD_TILE_SIZE), int(np[1] // WORLD_TILE_SIZE)
        for x, y in product(range(nwp[0] - LIGHT_SOURCE_RADIUS, nwp[0] + LIGHT_SOURCE_RADIUS + 1),
                            range(nwp[1] - LIGHT_SOURCE_RADIUS, nwp[1] + LIGHT_SOURCE_RADIUS + 1)):
            if not self._is_correct_tile_coords(x, y):
                continue
            if any(map(lambda z: z.get_type(), self._get_tiles_between((x, y), nwp))):
                continue
            dist = ((x - nwp[0]) ** 2 + (y - nwp[1]) ** 2) ** 0.5
            lightness = max(0.0, min(2 / (dist + 0.001) - 2 / LIGHT_SOURCE_RADIUS, 1.0))
            self._tiles[x][y].set_darkness(1 - lightness)
        source.update()

    def draw(self, camera, surface):
        camera_pos = camera.get_position()
        chunks_around_camera = self._get_chunks_around_pos((camera_pos[0] // WORLD_TILE_SIZE,
                                                            camera_pos[1] // WORLD_TILE_SIZE))
        draw_group = pygame.sprite.Group()
        light_draw_list = list()
        for chunk in chunks_around_camera:
            for tile in chunk:
                if tile.get_sprite().rect.colliderect(pygame.Rect((*camera.get_canvas_offset(), *DISPLAY_SIZE))):
                    draw_group.add(tile.get_sprite())
                    light_draw_list.append(tile)
        draw_group.draw(surface)

        for source in self._light_sources:
            self._calculate_light_from_source(source)

        for tile in light_draw_list:
            tile.draw_light_mask(surface)

    def get_player_position(self):
        return self._player_position

    def get_size(self):
        return self._size

    def get_tile(self, x, y):
        return self._tile[x][y]


screen = None
fps_counter = None

dynamic_sprite_group = None

world = None
player = None

canvas = None

camera = None


def setup():
    global screen, fps_counter, world, canvas, camera, player, dynamic_sprite_group

    pygame.init()
    screen = pygame.display.set_mode(DISPLAY_SIZE)
    fps_counter = FPSCounter()

    dynamic_sprite_group = pygame.sprite.Group()

    world = GameWorld(os.path.join('resources', WORLD_MAP_NAME), DISPLAY_SIZE)
    player = Player(world.get_player_position(), dynamic_sprite_group)
    world.add_light_source(player.get_light_source())
    camera = Camera((world.get_size()[0] * WORLD_TILE_SIZE, world.get_size()[1] * WORLD_TILE_SIZE),
                    DISPLAY_SIZE,
                    player.get_position())

    canvas = pygame.Surface((world.get_size()[0] * WORLD_TILE_SIZE, world.get_size()[1] * WORLD_TILE_SIZE))


def loop(dt, events):
    for event in events:
        if event.type == pygame.QUIT:
            return False

    keys_pressed = pygame.key.get_pressed()
    if keys_pressed[pygame.K_w]:
        move_vector = world.check_collisions_and_fix_move_vector(player, (0, -PLAYER_SPEED * dt / 1000))
        player.move(move_vector)
    elif keys_pressed[pygame.K_s]:
        move_vector = world.check_collisions_and_fix_move_vector(player, (0, PLAYER_SPEED * dt / 1000))
        player.move(move_vector)
    if keys_pressed[pygame.K_d]:
        move_vector = world.check_collisions_and_fix_move_vector(player, (PLAYER_SPEED * dt / 1000, 0))
        player.move(move_vector)
    elif keys_pressed[pygame.K_a]:
        move_vector = world.check_collisions_and_fix_move_vector(player, (-PLAYER_SPEED * dt / 1000, 0))
        player.move(move_vector)

    camera.set_position(player.get_position())
    world.draw(camera, canvas)
    dynamic_sprite_group.draw(canvas)
    screen.blit(canvas, (0, 0), pygame.Rect((*camera.get_canvas_offset(), *DISPLAY_SIZE)))
    return True


def clear():
    pygame.quit()


setup()

clock = pygame.time.Clock()

while True:

    dt = clock.tick()
    fps_counter.update(dt)
    events = pygame.event.get()

    if not loop(dt, events):
        break

    pygame.display.flip()

clear()
