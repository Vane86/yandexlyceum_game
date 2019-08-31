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
ENEMY_OBSERVATION_RADIUS = 8  # world tiles

ENEMY_ATTACK_PERIOD = 1000  # ms
PLAYER_ATTACK_PERIOD = 333  # ms

BULLET_SPEED = 7 * WORLD_TILE_SIZE  # pixels per second


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


class TimeLine:

    def __init__(self):
        self._time = 0

    def get_time(self):
        return self._time

    def update(self, dt):
        self._time += dt


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
        self._old_position = (0, 0)
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

    def __init__(self, position, sprite_texture_name):
        self._sprite = pygame.sprite.Sprite()
        self._sprite.image = pygame.image.load(os.path.join('resources', 'textures', f'{sprite_texture_name}.png')).convert()
        self._sprite.image.set_colorkey((255, 255, 255))
        # self._sprite.image = pygame.transform.scale(self._sprite.image, (PLAYER_SPRITE_SIZE, PLAYER_SPRITE_SIZE))
        self._sprite.rect = self._sprite.image.get_rect(center=(position[0], position[1]))
        self._position = position

    def set_position(self, position):
        self._sprite.rect.center = tuple(map(round, position))
        self._position = position

    def move(self, delta):
        self._position = tuple(map(lambda x: x[0] + x[1], zip(self._position, delta)))
        self._sprite.rect.center = tuple(map(round, self._position))

    def get_position(self):
        return self._position

    def get_sprite(self):
        return self._sprite


class Key(Entity):

    def __init__(self, position):
        super().__init__(position, 'key')


class Bullet(Entity):

    def __init__(self, position, velocity):
        super().__init__(position, 'bullet')
        self._velocity = velocity

    def get_velocity(self):
        return self._velocity


class Mob(Entity):

    def __init__(self, position, sprite_texture_name, health):
        super().__init__(position, sprite_texture_name)
        self._health = health

    def hit(self, damage):
        self._health -= damage

    def is_dead(self):
        return self._health <= 0

    def get_health(self):
        return self._health


class Player(Mob):

    def __init__(self, position):
        super().__init__(position, 'player', 10)
        self._light_source = LightSource(position)
        self._attack_time = 0

    def set_position(self, position):
        super().set_position(position)
        self._light_source.set_position(position)

    def move(self, delta):
        super().move(delta)
        self._light_source.move(delta)

    def get_light_source(self):
        return self._light_source

    def attack(self, point_pos):
        if time_line.get_time() - self._attack_time <= PLAYER_ATTACK_PERIOD:
            return None
        vel = (point_pos[0] - self.get_position()[0], point_pos[1] - self.get_position()[1])
        dist = (vel[0] ** 2 + vel[1] ** 2) ** 0.5
        vel = (vel[0] * BULLET_SPEED / dist, vel[1] * BULLET_SPEED / dist)
        bullet = Bullet(self.get_position(), vel)
        self._attack_time = time_line.get_time()
        return bullet


class Enemy(Mob):

    def __init__(self, position):
        super().__init__(position, 'enemy', 3)
        self._attack_time = 0

    def attack(self):
        self._attack_time = time_line.get_time()

    def can_attack(self):
        return time_line.get_time() - self._attack_time >= ENEMY_ATTACK_PERIOD


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
        self._keys = list()
        self._enemies = list()
        self._bullets = list()
        self._player_start_position = (0, 0)
        self._entity_sprite_group = pygame.sprite.Group()
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
                self._player_start_position = (x * WORLD_TILE_SIZE, y * WORLD_TILE_SIZE)
            elif tile_color[0] == tile_color[1] == 0 and tile_color[2] == 255:
                self._tiles[x][y] = GameWorldTile((x, y), 0)
                self._tile_chunks[tl_chk_xy[0]][tl_chk_xy[1]].append(self._tiles[x][y])
                self._keys.append(Key((x * WORLD_TILE_SIZE, y * WORLD_TILE_SIZE)))
                self._entity_sprite_group.add(self._keys[-1].get_sprite())
            elif tile_color[0] == 255 and tile_color[1] == tile_color[2] == 0:
                self._tiles[x][y] = GameWorldTile((x, y), 0)
                self._tile_chunks[tl_chk_xy[0]][tl_chk_xy[1]].append(self._tiles[x][y])
                self.add_enemy(Enemy((x * WORLD_TILE_SIZE, y * WORLD_TILE_SIZE)))
        self._light_sources = list()

    def _is_correct_chunk_coords(self, x, y):
        return not (y >= len(self._tile_chunks[x]) or y < 0 or x >= len(self._tile_chunks) or x < 0)

    def _is_correct_tile_coords(self, x, y):
        return not (x < 0 or x >= self._size[0] or y < 0 or y >= self._size[1])

    def _get_chunks_around_pos(self, pos_tiles):
        ccp = (int(pos_tiles[0] // self._chunk_size_tiles[0]),
               int(pos_tiles[1] // self._chunk_size_tiles[1]))
        return [self._tile_chunks[x][y] for x, y in product(range(ccp[0] - 1, ccp[0] + 2),
                                                            range(ccp[1] - 1, ccp[1] + 2))
                if self._is_correct_chunk_coords(x, y)]

    def check_collisions_and_fix_move_vector(self, entity, entity_move):
        result_move = [0, 0]
        start_pos = entity.get_position()
        start_pos_tiles = int(start_pos[0] // WORLD_TILE_SIZE), int(start_pos[1] // WORLD_TILE_SIZE)
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
        dx, dy = int(pos1[0]) - int(pos2[0]), int(pos1[1]) - int(pos2[1])
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

    def _find_path_between(self, pos1, pos2):
        pos1, pos2 = tuple(map(int, pos1)), tuple(map(int, pos2))
        tile_tags = [[-1] * self._size[1] for _ in range(self._size[0])]
        tile_tags[pos1[0]][pos1[1]] = 0
        vs = {pos1}
        while vs and tile_tags[pos2[0]][pos2[1]] == -1:
            pos = vs.pop()
            if (self._is_correct_tile_coords(pos[0], pos[1] + 1) and tile_tags[pos[0]][pos[1] + 1] == -1 and
                    self._tiles[pos[0]][pos[1] + 1].get_type() == 0):
                tile_tags[pos[0]][pos[1] + 1] = tile_tags[pos[0]][pos[1]] + 1
                vs.add((pos[0], pos[1] + 1))
            if (self._is_correct_tile_coords(pos[0], pos[1] - 1) and tile_tags[pos[0]][pos[1] - 1] == -1 and
                    self._tiles[pos[0]][pos[1] - 1].get_type() == 0):
                tile_tags[pos[0]][pos[1] - 1] = tile_tags[pos[0]][pos[1]] + 1
                vs.add((pos[0], pos[1] - 1))
            if (self._is_correct_tile_coords(pos[0] + 1, pos[1]) and tile_tags[pos[0] + 1][pos[1]] == -1 and
                    self._tiles[pos[0] + 1][pos[1]].get_type() == 0):
                tile_tags[pos[0] + 1][pos[1]] = tile_tags[pos[0]][pos[1]] + 1
                vs.add((pos[0] + 1, pos[1]))
            if (self._is_correct_tile_coords(pos[0] - 1, pos[1]) and tile_tags[pos[0] - 1][pos[1]] == -1 and
                    self._tiles[pos[0] - 1][pos[1]].get_type() == 0):
                tile_tags[pos[0] - 1][pos[1]] = tile_tags[pos[0]][pos[1]] + 1
                vs.add((pos[0] - 1, pos[1]))

        path = [pos2]
        while path[-1] != pos1:
            if (self._is_correct_tile_coords(path[-1][0], path[-1][1] + 1) and
                    tile_tags[path[-1][0]][path[-1][1] + 1] + 1 == tile_tags[path[-1][0]][path[-1][1]]):
                path.append((path[-1][0], path[-1][1] + 1))
            elif (self._is_correct_tile_coords(path[-1][0], path[-1][1] - 1) and
                  tile_tags[path[-1][0]][path[-1][1] - 1] + 1 == tile_tags[path[-1][0]][path[-1][1]]):
                path.append((path[-1][0], path[-1][1] - 1))
            elif (self._is_correct_tile_coords(path[-1][0] + 1, path[-1][1]) and
                  tile_tags[path[-1][0] + 1][path[-1][1]] + 1 == tile_tags[path[-1][0]][path[-1][1]]):
                path.append((path[-1][0] + 1, path[-1][1]))
            elif (self._is_correct_tile_coords(path[-1][1] - 1, path[-1][1]) and
                  tile_tags[path[-1][0] - 1][path[-1][1]] + 1 == tile_tags[path[-1][0]][path[-1][1]]):
                path.append((path[-1][0] - 1, path[-1][1]))
        return path[::-1]

    def _calculate_light_from_source(self, source):
        op = source.get_old_position()
        owp = int(op[0] // WORLD_TILE_SIZE), int(op[1] // WORLD_TILE_SIZE)
        np = source.get_new_position()
        nwp = int(np[0] // WORLD_TILE_SIZE), int(np[1] // WORLD_TILE_SIZE)
        # if nwp == owp:
        #     return
        for x, y in product(range(owp[0] - LIGHT_SOURCE_RADIUS, owp[0] + LIGHT_SOURCE_RADIUS + 1),
                            range(owp[1] - LIGHT_SOURCE_RADIUS, owp[1] + LIGHT_SOURCE_RADIUS + 1)):
            if not self._is_correct_tile_coords(x, y):
                continue
            self._tiles[x][y].set_darkness(1.0)
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

    def add_entity(self, entity):
        self._entity_sprite_group.add(entity.get_sprite())

    def remove_entity(self, entity):
        self._entity_sprite_group.remove(entity.get_sprite())

    def add_enemy(self, enemy):
        self._enemies.append(enemy)
        self.add_entity(enemy)

    def remove_enemy(self, enemy):
        self._enemies.remove(enemy)
        self.remove_entity(enemy)

    def update_enemies(self, dt, player):
        for enemy in self._enemies:

            if enemy.get_health() <= 0:
                self.remove_enemy(enemy)
                continue

            if pygame.sprite.collide_rect(enemy.get_sprite(), player.get_sprite()):
                if enemy.can_attack():
                    player.hit(1)
                    enemy.attack()

            enemy_world_pos = tuple(map(lambda x: x / WORLD_TILE_SIZE, enemy.get_position()))
            player_world_pos = tuple(map(lambda x: x / WORLD_TILE_SIZE, player.get_position()))
            dist = ((enemy_world_pos[0] - player_world_pos[0]) ** 2 +
                    (enemy_world_pos[1] - player_world_pos[1]) ** 2) ** 0.5
            if dist >= ENEMY_OBSERVATION_RADIUS or dist < 0.7:
                continue
            if any(map(lambda x: x.get_type(), self._get_tiles_between(enemy_world_pos, player_world_pos))):
                path = self._find_path_between(enemy_world_pos, player_world_pos)
                to_player = (path[1][0] - path[0][0], path[1][1] - path[0][1])
                dist = (to_player[0] ** 2 + to_player[1] ** 2) ** 0.5
                # print('OBS')
            else:
                to_player = (player_world_pos[0] - enemy_world_pos[0], player_world_pos[1] - enemy_world_pos[1])
                # print('NO OBS')
            to_player = (to_player[0] / dist * dt / 1000 * PLAYER_SPEED * 0.5,
                         to_player[1] / dist * dt / 1000 * PLAYER_SPEED * 0.5)
            # print(to_player)
            to_player = self.check_collisions_and_fix_move_vector(enemy, to_player)
            enemy.move(to_player)

    def update_bullets(self, dt):
        for bullet in self._bullets:
            bv = bullet.get_velocity()
            move_vector = (bv[0] * dt / 1000, bv[1] * dt / 1000)
            mv1 = self.check_collisions_and_fix_move_vector(bullet, move_vector)
            if mv1 != move_vector:
                self.remove_bullet(bullet)
                continue
            bullet.move(move_vector)
            for enemy in self._enemies:
                if pygame.sprite.collide_rect(bullet.get_sprite(), enemy.get_sprite()):
                    enemy.hit(1)
                    self.remove_bullet(bullet)

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
        self._entity_sprite_group.draw(surface)

        for source in self._light_sources:
            self._calculate_light_from_source(source)

        for tile in light_draw_list:
            tile.draw_light_mask(surface)

    def add_bullet(self, bullet):
        self._bullets.append(bullet)
        self.add_entity(bullet)

    def remove_bullet(self, bullet):
        if bullet in self._bullets:
            self._bullets.remove(bullet)
            self.remove_entity(bullet)

    def remove_key(self, key):
        self._keys.remove(key)
        self.remove_entity(key)

    def get_keys(self):
        return tuple(self._keys)

    def get_player_start_position(self):
        return self._player_start_position

    def get_size(self):
        return self._size

    def get_tile(self, x, y):
        return self._tile[x][y]


screen = None
fps_counter = None
time_line = None

world = None
player = None

canvas = None

camera = None

keys_to_find = None

player_won = False
player_lost = False


def setup():
    global screen, fps_counter, time_line, world, canvas, camera, player, keys_to_find

    pygame.init()
    screen = pygame.display.set_mode(DISPLAY_SIZE)
    fps_counter = FPSCounter()
    time_line = TimeLine()

    world = GameWorld(os.path.join('resources', WORLD_MAP_NAME), DISPLAY_SIZE)
    player = Player(world.get_player_start_position())
    world.add_entity(player)
    world.add_light_source(player.get_light_source())
    camera = Camera((world.get_size()[0] * WORLD_TILE_SIZE, world.get_size()[1] * WORLD_TILE_SIZE),
                    DISPLAY_SIZE,
                    player.get_position())

    canvas = pygame.Surface((world.get_size()[0] * WORLD_TILE_SIZE, world.get_size()[1] * WORLD_TILE_SIZE))
    keys_to_find = len(world.get_keys())


def draw_gui(surface):
    font = pygame.font.Font(None, 18)
    hp_text = font.render('Здоровье: ' + str(player.get_health()), 1, (255, 100, 100))
    key_to_find_text = font.render('Ключей найти: ' + str(keys_to_find), 1, (100, 255, 100))
    surface.blit(hp_text, (5, DISPLAY_SIZE[1] - 50))
    surface.blit(key_to_find_text, (5, DISPLAY_SIZE[1] - 25))


def loop(dt, events):
    global keys_to_find, player_won, player_lost

    for event in events:
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            canvas_offset = camera.get_canvas_offset()
            mouse_game_pos = (mouse_pos[0] + canvas_offset[0], mouse_pos[1] + canvas_offset[1])
            bullet = player.attack(mouse_game_pos)
            if bullet is not None:
                world.add_bullet(bullet)

    if not (player_lost or player_won):

        time_line.update(dt)

        world.update_enemies(dt, player)
        world.update_bullets(dt)

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

        keys = world.get_keys()
        for key in keys:
            if pygame.sprite.collide_rect(player.get_sprite(), key.get_sprite()):
                world.remove_key(key)
                keys_to_find -= 1

        if player.get_health() <= 0:
            player_lost = True

        if len(world.get_keys()) == 0:
            player_won = True

        camera.set_position(player.get_position())
        world.draw(camera, canvas)
        screen.blit(canvas, (0, 0), pygame.Rect((*camera.get_canvas_offset(), *DISPLAY_SIZE)))
        draw_gui(screen)

    else:
        screen.fill((0, 0, 0))
        font = pygame.font.Font(None, 48)
        if player_lost:
            text = font.render('Потрачено', 1, (200, 10, 10))
            place = text.get_rect(center=(DISPLAY_SIZE[0] // 2, DISPLAY_SIZE[1] // 2))
            screen.blit(text, place)
        else:
            text = font.render('Победа!', 1, (100, 255, 100))
            place = text.get_rect(center=(DISPLAY_SIZE[0] // 2, DISPLAY_SIZE[1] // 2))
            screen.blit(text, place)

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
