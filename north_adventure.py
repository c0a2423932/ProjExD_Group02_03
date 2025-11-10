import os
import math
import sys
import pygame as pg
import threading
import random

WIDTH, HEIGHT = 900, 600
FPS = 60
os.chdir(os.path.dirname(os.path.abspath(__file__)))

BG = (135, 206, 235)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
GOLD = (255, 215, 0)
GROUND = (220, 235, 237)
FLOATING_ICE = (53, 94, 144)
PLAYER_COLOR = (220, 20, 60)
ground_y = HEIGHT - 40  # 地面
Player_base_height = 50  # 基準となるキャラクターの高さ
Enemy_base_height = 60  # 基準となるキャラクターの高さ
FallingEnemy_base_height = 50  # 基準となるキャラクターの高さ

# ... (Player クラスの定義はそのまま。画像ロードもそのまま利用) ...
class Player:
    def __init__(self, x, y):
        self.rect = pg.Rect(x, y, 50, Player_base_height) # 当たり判定の初期サイズ
        self.vx = 0
        self.vy = 0
        # 追加機能1(近藤): パワーアップ機能の状態を保持
        self.speed = 5
        self.jump_power = 14
        # 追加機能3(近藤): 向き（弾発射時に使用）
        self.on_ground = False
        self.direction = "right"  # "right" or "left"
        self.power = None  # 現在の能力
        self.facing = 1  # 追加機能3(近藤): 向き（弾発射時に使用）
        # パワーアップ状態
        self.base_speed = self.speed
        self.base_jump_power = self.jump_power
        self.jump_enabled = True
        #パワーアップ状態
        self.power_time = 0.0
        self.can_kill_on_touch = False
        # 衝突後の短い無敵フレーム（秒）
        self.invul_time = 0.0

        def load_and_resize_image(path, Player_base_height):
            """画像を読み込み、アスペクト比を維持してリサイズする"""
            img = pg.image.load(path).convert_alpha()
            orig_w, orig_h = img.get_size()
            aspect_ratio = orig_w / orig_h
            new_width = int(Player_base_height * aspect_ratio)
            return pg.transform.scale(img, (new_width, Player_base_height))


        # 画像の読み込みとリサイズを効率化
        # (画像パス, 高さ) のタプルで指定
        image_paths = {
            'normal': ("img/penguin_right.png", 70),
            'fire':   ("img/power/penguin_honoo.png", 90),
            'ice':    ("img/power/penguin_koori.png", 90),
            'jump':   ("img/power/penguin_usagi.png", 90),
            'speed':  ("img/power/penguin_speed.png", 50),
            'muteki': ("img/power/penguin_muteki.png", 70),
        }
       
        # 能力名と画像のペアを辞書にまとめる
        self.power_images = {
            key: {'right': load_and_resize_image(path, height),
                  'left': pg.transform.flip(load_and_resize_image(path, height), True, False)}
            for key, (path, height) in image_paths.items()
        }
        self.power_images[None] = self.power_images.pop('normal') # 通常状態のキーをNoneに
        self.image = self.power_images[None]['right'] # 初期画像を設定
       
    def handle_input(self, keys):
        self.vx = 0
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            self.vx = -self.speed
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            self.vx = self.speed
        if self.vx > 0:
            self.direction = "right"
            self.facing = 1
        if self.vx < 0:
            self.direction = "left"
            self.facing = -1
        if (keys[pg.K_SPACE]) and self.on_ground:
            self.vy = -self.jump_power
            self.on_ground = False
       
    def apply_gravity(self):
        self.vy += 0.8  # 重力
        if self.vy > 20:
            self.vy = 20
    
    def apply_power(self, power: str, duration: float = 8.0):
        """
        プレイヤーに数秒間パワーアップを適用します。
        power: 'fire','ice','jump','suberu','muteki'
        """
        # 以前のクラスをリセットする
        self.speed = self.base_speed
        self.jump_power = self.base_jump_power
        self.jump_enabled = True
        self.can_kill_on_touch = False
        self.power = power
        self.power_time = float(duration)
        if power == 'fire' or power == 'ice':
            self.can_kill_on_touch = True
        elif power == 'jump':
            self.jump_power = self.base_jump_power * 2
        elif power == 'speed':
            self.speed = int(self.base_speed * 1.6)
            self.jump_enabled = False
        elif power == 'muteki':
            # muteki: 敵の衝突を無視（無敵状態）
            pass

    def update_power(self, dt: float):
        if self.power is not None:
            self.power_time -= dt
            if self.power_time <= 0:
                self.clear_power()

    def update(self, platforms, hatena_platforms, items):
        self.rect.x += int(self.vx)
        self._collide(self.vx, 0, platforms, hatena_platforms, items)
        self.apply_gravity()
        self.rect.y += int(self.vy)
        self.on_ground = False
        # 画面の左端から出ないようにする
        if self.rect.left < 0:
            self.rect.left = 0
        self._collide(0, self.vy, platforms, hatena_platforms, items)
    
    def _collide(self, vx, vy, platforms, hatena_blocks=None, items=None):
        for p_obj in platforms: # platforms は hatena_platforms を含まないようにする
            # p_objがRectか、rect属性を持つオブジェクトかを判定
            p_rect = p_obj if isinstance(p_obj, pg.Rect) else p_obj.rect
            if self.rect.colliderect(p_rect):
                # ゴールオブジェクトとの衝突時は物理的な反発をしない
                if isinstance(p_obj, Goal):
                    continue
                if vx > 0:  # 右
                    self.rect.right = p_rect.left
                if vx < 0:  # 左
                    self.rect.left = p_rect.right
                if vy > 0:  # 落下
                    self.rect.bottom = p_rect.top
                    self.vy = 0
                    self.on_ground = True
                if vy < 0:  # ジャンプ
                    self.rect.top = p_rect.bottom
                    self.vy = 0
        
        if hatena_blocks and items is not None:
            for b in hatena_blocks:
                if self.rect.colliderect(b.rect): # b is a HatenaBlock, so b.rect is correct
                    if vy < 0 and not b.used and self.rect.top < b.rect.bottom: # Jumping up into block
                        self.rect.top = b.rect.bottom
                        self.vy = 0 # Stop upward movement
                        b.activate(items)


    def clear_power(self):
        """能力が切れたら、基本ステータスに戻す"""
        self.power = None
        self.power_time = 0.0
        self.speed = self.base_speed
        self.jump_power = self.base_jump_power
        self.jump_enabled = True
        self.can_kill_on_touch = False

    def draw(self, surf):
        # 辞書を使って、現在の能力と向きに応じた画像を効率的に選択
        image_set = self.power_images.get(self.power, self.power_images[None])
        self.image = image_set[self.direction]
        # 画像の足元中央を、当たり判定(rect)の足元中央に合わせる
        draw_rect = self.image.get_rect()
        draw_rect.midbottom = self.rect.midbottom
        surf.blit(self.image, draw_rect)


class Enemy:
    def __init__(self, x, y, w=40, h=40, left_bound=None, right_bound=None):
        # 元画像を2つロードランダムでどちらか選ぶ
        img_sirokuma = pg.image.load("img/sirokuma.png").convert_alpha()
        img_kame = pg.image.load("img/kame.png").convert_alpha()
        import random
        img_right_orig = random.choice([img_sirokuma, img_kame])

        # 元画像の比率を計算し、ペンギンの高さを基準に新しいサイズを算出
        orig_w, orig_h = img_right_orig.get_size()
        size = (int(Enemy_base_height * orig_w / orig_h), Enemy_base_height)
        if img_right_orig == img_sirokuma:
            self.vx = -3
        else:   
            self.vx = -1
        self.left_bound = left_bound
        self.right_bound = right_bound
        self.image_right = pg.transform.scale(img_right_orig, size) # 計算後のサイズでリサイズ
        self.image_left = pg.transform.flip(self.image_right, True, False)
        self.image = self.image_left # 初期画像は左向き
        self.rect = self.image.get_rect(bottomleft=(x, y)) # y座標（足元）を基準に配置
       
    def update(self, platforms):
        # 水平移動
        self.rect.x += self.vx

        # 進行方向の足元に地面があるかチェック
        # 崖っぷちで反転するための処理
        ground_check_pos = self.rect.midbottom
        is_wall_collision = False # is_wall_collisionを初期化
        if self.vx > 0: # 右向き
            ground_check_pos = (self.rect.right, self.rect.bottom + 1)
        elif self.vx < 0: # 左向き
            ground_check_pos = (self.rect.left, self.rect.bottom + 1)
 
        on_ground = any(p.collidepoint(ground_check_pos) for p in platforms)

        # 壁との衝突チェック
        collided_wall = False
        for p in platforms:
            if self.rect.colliderect(p)and self.rect.bottom > p.top: # 上に乗っているだけの場合は無視
                if self.vx > 0 and self.rect.right > p.left and self.rect.left < p.left: # 右の壁
                    self.rect.right = p.left
                    collided_wall = True
                elif self.vx < 0 and self.rect.left < p.right and self.rect.right > p.right: # 左の壁
                    self.rect.left = p.right
                    collided_wall = True
        # 崖っぷちまたは壁に衝突したまたは画面外の場合 
        if not on_ground or collided_wall or self.rect.left < 0 or self.rect.right > WIDTH:
               
                self.vx *= -1 # 進行方向を反転
                self.image = self.image_right if self.vx > 0 else self.image_left
    
    def draw(self, surf):
        draw_rect = self.image.get_rect()
        draw_rect.midbottom = self.rect.midbottom
        surf.blit(self.image, draw_rect)


# 落ちてくる敵
class FallingEnemy:
    def __init__(self, x, y, w=40, h=40, speed=2):
        self.rect = pg.Rect(x, y, w, h)
        self.vy = speed  # 落下速度
        img_koura = pg.image.load("img/koura.png").convert_alpha()
        orig_w, orig_h = img_koura.get_size()
        size = (int(FallingEnemy_base_height * orig_w / orig_h), FallingEnemy_base_height)
        self.image_right = pg.transform.scale(img_koura, size) # 計算後のサイズでリサイズ
        self.image_left = pg.transform.flip(self.image_right, True, False)
        self.image = self.image_left

    def update(self):
        self.rect.y += self.vy  # 下に落ちる
        # 画面外に出たら,球にあたって衝突したら上にリセット
        if self.rect.top > HEIGHT:
            self.rect.bottom = 0

    def draw(self, surf):
        surf.blit(self.image, self.rect)


# アイテムクラス
class Item:
    def __init__(self, x, y, kind, duration=10, w=40, h=40):
        self.rect = pg.Rect(x, y, w, h) #
        self.kind = kind  # 'fire','ice','jump','suberu','muteki'
        self.duration = duration

        # アイテムの種類に応じた画像を辞書に格納
        self.image_map = {
            'fire': pg.transform.scale(pg.image.load("img/item/honoo-item.png").convert_alpha(), (w, h)),
            'ice': pg.transform.scale(pg.image.load("img/item/koori-item.png").convert_alpha(), (w, h)),
            'jump': pg.transform.scale(pg.image.load("img/item/jamp-item.png").convert_alpha(), (w, h)),
            'speed': pg.transform.scale(pg.image.load("img/item/speedup-item.png").convert_alpha(), (w, h)),
            'muteki': pg.transform.scale(pg.image.load("img/item/muteki-item.png").convert_alpha(), (w, h))
        }
        # 現在のアイテム画像を設定
        self.image = self.image_map.get(self.kind)

    def draw(self, surf):
        surf.blit(self.image, self.rect)


# ハテナブロック
class HatenaBlock:
    """
    アイテムを内包するはてなブロックのクラス
    """
    def __init__(self, x, y):
        self.rect = pg.Rect(x, y, 40, 40)
        self.used = False
         # 画像のロード
        self.image_hatena = pg.transform.scale(pg.image.load("img/hatena.png").convert_alpha(), (40, 40)) # This is defined but not used.
        # 画像（self.image_hatena）を白黒にしたものをからのハテナブロックとする
        self.image_empty = pg.transform.scale(pg.image.load("img/hatena_empty.png").convert_alpha(), (40, 40))
        self.image = self.image_hatena

    def activate(self, items):
        if not self.used:
            self.used = True
            kind = random.choice(["fire", "ice", "jump", "speed", "muteki"])
            item = Item(self.rect.centerx - 20, self.rect.top - 40, kind)
            items.append(item)
            self.image = self.image_empty

    def draw(self, surf):
        surf.blit(self.image, self.rect)


class PowerUpDisplay: 
    """
    現在のパワーアップ状態を画面右上に表示するクラス
    """
    def __init__(self, pos: tuple[int, int], size: tuple[int, int]=(60, 60)):
        self.pos = pos
        self.size = size
        # アイテムの種類に応じた画像を辞書に格納
        self.image_map = {
            'fire': pg.transform.scale(pg.image.load("img/item/honoo-item.png").convert_alpha(), self.size),
            'ice': pg.transform.scale(pg.image.load("img/item/koori-item.png").convert_alpha(), self.size),
            'jump': pg.transform.scale(pg.image.load("img/item/jamp-item.png").convert_alpha(), self.size),
            'speed': pg.transform.scale(pg.image.load("img/item/speedup-item.png").convert_alpha(), self.size),
            'muteki': pg.transform.scale(pg.image.load("img/item/muteki-item.png").convert_alpha(), self.size)
        }

    def draw(self, surf, current_power):
        image = self.image_map.get(current_power)
        if image:
            surf.blit(image, self.pos)


class Projectile:
    """プレイヤーが火/氷の力を持っているときに発射する弾"""
    def __init__(self, x, y, kind: str, direction: int, speed: float = 10.0):
        self.rect = pg.Rect(int(x), int(y), 10, 10)
        self.kind = kind
        self.vx = speed * (1 if direction >= 0 else -1)
        # 画像のロード
        if self.kind == 'fire':
            self.image = pg.image.load("img/fireball.png").convert_alpha()
        elif self.kind == 'ice':
            self.image = pg.image.load("img/iceball.png").convert_alpha()
        # 画像の元の比率でリサイズ
        orig_w, orig_h = self.image.get_size()
        self.image = pg.transform.scale(self.image, (50, int(50 * orig_h / orig_w)))
        # 右向きに発射される場合のみ画像を反転させる（元画像が左向きのため）
        if self.vx > 0:
            self.image = pg.transform.flip(self.image, True, False)
    
    def update(self):
        self.rect.x += int(self.vx)

    def draw(self, surf):
        surf.blit(self.image, self.rect)


class Goal(pg.sprite.Sprite):
    def __init__(self, x, y, w, h):
        self.rect = pg.Rect(x, y, w, h)
        # ゴール画像
        self.goal_img = pg.image.load("img/goal_pole.png").convert_alpha()
        self.image = pg.transform.scale(self.goal_img, (w, h))

    def draw(self, surf):
        surf.blit(self.image, self.rect)
# ground_size_y = 40
# floating_saize_y = 50

def build_stage1():
    """
    1つ目のステージを生成する関数
    戻り値：地面・浮島・はてなブロック・敵のリスト(以下build関数は同文)
    """
    ground_platforms = [
        pg.Rect(0, ground_y, 200, 40),
        pg.Rect(250, ground_y, 50, 40),
        pg.Rect(350, ground_y, 50, 40),
        pg.Rect(500, ground_y, 50, 40),
        pg.Rect(600, ground_y, 50, 40),
        pg.Rect(700, ground_y, WIDTH, 40)
    ]
    floating_platforms = [
        pg.Rect(100, 500, 50, 50),
        pg.Rect(250, 400, 150, 50)
    ]
    hatena_platforms = [HatenaBlock(350, 300)]
    enemies = [Enemy(700, ground_y)]
    items = []
    goal_platforms = []
    falling_enemies = []
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage2():
    """2つ目のステージを生成する関数"""
    ground_platforms = [
        pg.Rect(0, ground_y, 550, 40),
        pg.Rect(650, ground_y, 150, 40)
    ]
    floating_platforms = [
        pg.Rect(200, 500, 50, 50),
        pg.Rect(300, 400, 50, 50),
        pg.Rect(400, 300, 50, 50),
        pg.Rect(500, 200, 50, 50),
        pg.Rect(650, 350, 50, 50),
        pg.Rect(800, 350, 100, 50)
    ]
    hatena_platforms = []
    enemies = [Enemy(800, ground_y)]
    goal_platforms = []
    items = []
    falling_enemies = [FallingEnemy(250, 0, speed=2), FallingEnemy(700, -200, speed=2)]
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage3():
    """3つ目のステージを生成する関数"""
    ground_platforms = [pg.Rect(0, ground_y, WIDTH, 40)]
    floating_platforms = [
        pg.Rect(0, 200, 250, 50),
        pg.Rect(300, 350, 200, 50),
        pg.Rect(600, 450, 250, 50)
    ]
    hatena_platforms = [
        HatenaBlock(50, 100),
        HatenaBlock(700, 350)
    ]
    enemies = [Enemy(WIDTH-100, y=ground_y)]
    goal_platforms = []
    items = []
    falling_enemies = [FallingEnemy(150, 0, speed=2), FallingEnemy(550, -200, speed=2)]
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage4():
    """4つ目のステージを生成する関数"""
    hatena_platforms = []
    ground_platforms = [pg.Rect(0, ground_y, WIDTH, 40)]
    floating_platforms = [
        pg.Rect(100, ground_y-50, 50, 50),
        pg.Rect(200, 400, 100, 50),
        pg.Rect(350, 300, 50, 50),
        pg.Rect(450, 200, 100, 50),
        pg.Rect(600, 100, 50, 50),
        pg.Rect(700, 200, 50, 50),
        pg.Rect(800, 100, 50, 50)
    ]
    enemies = [Enemy(x=800, y=ground_y), Enemy(x=750, y=ground_y)]
    goal_platforms = []
    items = []
    falling_enemies = [FallingEnemy(150, 0, speed=3), FallingEnemy(450, -200, speed=3)]
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage5():
    """5つ目のステージを生成する関数"""
    ground_platforms = [pg.Rect(0, ground_y, WIDTH, 40)]
    floating_platforms = [
        pg.Rect(150, 500, 50, 50),
        pg.Rect(200, 450, 50, 50),
        pg.Rect(250, 400, 50, 50),
        pg.Rect(750, 450, 50, 50),
        pg.Rect(800, 450, 100, 50),
        pg.Rect(400, 300, 150, 50),
        pg.Rect(650, 200, 250, 50)
    ]
    hatena_platforms = [HatenaBlock(750, 90)]
    enemies = [Enemy(x=800, y=ground_y)]
    goal_platforms = []
    items = []
    falling_enemies = [FallingEnemy(300, 0, speed=2), FallingEnemy(600, -150, speed=2)]
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage6():
    """6つ目のステージを生成する関数"""
    ground_platforms = [pg.Rect(0, ground_y, WIDTH, 40)]
    floating_platforms = [
        pg.Rect(0, 500, 50, 50),
        pg.Rect(350, 500, 200, 50),
        pg.Rect(300, 300, 250, 50),
        pg.Rect(650, 400, 50, 50),
        pg.Rect(700, 450, 200, 50)
    ]
    hatena_platforms = [HatenaBlock(400, 190)]
    enemies = [Enemy(x=700, y=ground_y)]
    goal_platforms = []
    items = []
    falling_enemies = [FallingEnemy(150, 0, speed=2), FallingEnemy(550, -150, speed=2)]
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage7():
    """7つ目のステージを生成する関数"""
    ground_platforms = [
        pg.Rect(0, ground_y, 250, 40),
        pg.Rect(350, ground_y, 350, 40),
        pg.Rect(800, ground_y, 100, 40)
    ]
    floating_platforms = []
    hatena_platforms = [HatenaBlock(150, 440)]
    enemies = []
    goal_platforms = []
    items = []
    falling_enemies = []
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage8():
    """8つ目のステージを生成する関数"""
    ground_platforms = [pg.Rect(0, ground_y, WIDTH, 40)]
    floating_platforms = [
        pg.Rect(150, 500, 50, 50),
        pg.Rect(200, 400, 250, 50),
        pg.Rect(750, 500, 50, 50),
        pg.Rect(500, 400, 250, 50)
    ]
    hatena_platforms = [HatenaBlock(WIDTH/2, 290)]
    enemies = [Enemy(700, ground_y)]
    goal_platforms = []
    items = []
    falling_enemies = [FallingEnemy(200, 0, speed=2)]
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage9():
    """9つ目のステージを生成する関数"""
    ground_platforms = [pg.Rect(0, ground_y, WIDTH, 40)]
    floating_platforms = [pg.Rect(150, 450, 150, 50),pg.Rect(300, 350, 150, 50), pg.Rect(400, 250, 150, 50),pg.Rect(500, 350, 150, 50),pg.Rect(650, 450, 150, 50)]
    hatena_platforms = []
    enemies = [Enemy(300, ground_y)]
    goal_platforms = []
    items = []
    falling_enemies = []
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_stage10():
    """10つ目のステージを生成する関数"""
    ground_platforms = [pg.Rect(0, ground_y, 550, 40),pg.Rect(650, ground_y, 250, 40)]
    floating_platforms = [pg.Rect(150, 500, 400, 50),pg.Rect(250, 450, 300, 50),pg.Rect(350, 400, 200, 50),pg.Rect(450, 350, 100, 50),pg.Rect(650, 350, 250, 50),pg.Rect(700, 300, 200, 50)]
    hatena_platforms = []
    enemies = []
    goal_platforms = []
    items = []
    falling_enemies = [FallingEnemy(750, 0, speed=2)]
    return ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies

def build_gole(): # 関数名を build_gole に修正
    """
    ゴールステージ画面を生成する関数。旗に触れるとゴールする。
    戻り値：ステージ名、地面のリスト、ゴールのリスト(中身は１つだけ)
    """
    ground_platforms = [pg.Rect(0, ground_y, WIDTH, 40)]
    goal_platforms = [Goal(WIDTH - 80, ground_y - 80, 40, 80)]
    hatena_platforms = []
    enemies = []
    items = []
    falling_enemies = []
    return ground_platforms, [], hatena_platforms, goal_platforms, enemies, items, falling_enemies
STAGE_BUILDERS = [ build_stage1, build_stage2, build_stage3, build_stage4, build_stage5,build_stage6, build_stage7, build_stage8, build_stage9, build_stage10, build_gole]

def draw_text(surf, text, size, x, y, color=BLACK, center=True):
    """画面にテキストを描画する関数"""
    font = pg.font.Font(None, size)
    txt = font.render(text, True, color)
    rect = txt.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surf.blit(txt, rect)

def main():
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("北極探検ゲーム")
    clock = pg.time.Clock()

        #背景画像を読み込む
    bg_img = pg.transform.scale(pg.image.load("img/haikei.png").convert(), (WIDTH, HEIGHT))
        #地面用の画像を読み込む
    ground_img = pg.image.load("img/ground.png").convert_alpha()
        # 浮遊ブロック用の画像 (icy_block.png)
    block_img = pg.image.load("img/huyuu.png").convert_alpha()

    def init_game(stage_index=0): # 修正: init_game の実装を修正
        player = Player(50, HEIGHT - 90 - 50)
        builder = STAGE_BUILDERS[stage_index]
        # ステージを構築
        ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, items, falling_enemies = builder()
        platforms = ground_platforms + floating_platforms + goal_platforms
        projectiles = []
        return player, platforms, ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, falling_enemies, items, projectiles

    stage_index = 0
    stage_index_count = 0
    stage_num = 5
    player, platforms, ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, falling_enemies, items, projectiles = init_game(stage_index)
    power_display = PowerUpDisplay(pos=(WIDTH - 80, 20))
    play_time = 0.0
    state = "start"
    running = True
    while running:
        # ... (イベント処理、更新処理は省略) ...
        dt = clock.tick(FPS) / 1000.0 
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            if state == "play":
                if event.type == pg.KEYDOWN and event.key == pg.K_x: #xが押されたときに球を発射
                    # プレイヤーが火または氷の力を持っている場合にのみ発射物を生成します
                    if player.power in ('fire', 'ice'):
                        px = player.rect.centerx + player.facing * (player.rect.width//2 + 5)
                        py = player.rect.centery
                        projectiles.append(Projectile(px, py, player.power, player.facing))

        keys = pg.key.get_pressed()

        # スタート画面
        if state == "start":
            screen.blit(bg_img, (0, 0))
            #パワーアップアイテムを適当に表示
            power_display.draw(screen, player.power)

            draw_text(screen, "GAME START", 100, WIDTH // 2, HEIGHT // 3, WHITE)
            draw_text(screen, "SPACE : Start", 80, WIDTH // 2, HEIGHT // 2)
            draw_text(screen, "< >: Move    SPACE : Jump", 80, WIDTH // 2, HEIGHT // 2 + 60, BLACK)
            pg.display.flip()
            if keys[pg.K_SPACE]:
                play_time = 0.0 #タイマーリセット
                state = "play"
            continue

        # ゲームプレイ中
        elif state == "play":
            play_time += dt #プレイ時間の加算

            player.handle_input(keys)

            # ゴールとの当たり判定を先に実行
            for g in goal_platforms:
                if player.rect.colliderect(g.rect):
                    state = "goal"
                    break # ゴールに到達したらループを抜ける

            if state == "play": # ゴール状態でない場合のみ、プレイヤーや敵の更新を続ける
                player.update(platforms, hatena_platforms, items) # blocksとitemsをキーワード引数で渡す
            player.update_power(dt)
            for e in enemies:
                e.update(platforms)
            for fe in falling_enemies:
                fe.update()
            # 発射物を更新する
            for p in projectiles[:]:
                p.update()
                # 画面外の場合は削除
                if p.rect.right < 0 or p.rect.left > WIDTH:
                    projectiles.remove(p)
                    continue
                for e in enemies[:]:
                    if p.rect.colliderect(e.rect):
                        enemies.remove(e)
                        projectiles.remove(p)
                        break
                for fe in falling_enemies:
                    if p.rect.colliderect(fe.rect):
                        falling_enemies.remove(fe)
                        projectiles.remove(p)
                        break
            # 敵との衝突
            dead = False
            for e in enemies[:]:
                if player.rect.colliderect(e.rect):
                    # 無敵（muteki）は触れると敵を倒す
                    if player.power == 'muteki':
                        enemies.remove(e)
                    # 敵を倒すのは踏みつけ（プレイヤーが下向きに当たったとき）のみ
                    elif player.vy > 0 and player.rect.bottom - e.rect.top < 20:
                        enemies.remove(e)
                        player.vy = -8
                    elif player.power in ('fire', 'ice','speed','jump'):
                            player.clear_power()
                    else:
                        dead = True
            #落ちてくる敵との衝突判定
            for fe in falling_enemies:
                if player.rect.colliderect(fe.rect):
                    # 無敵（muteki）は触れると敵を倒す
                    if player.power == 'muteki':
                        falling_enemies.remove(fe)
                    # 敵を倒すのは踏みつけ（プレイヤーが下向きに当たったとき）のみ
                    elif player.vy > 0 and player.rect.bottom  - fe.rect.top < 20:
                        falling_enemies.remove(fe)
                        player.vy = -8
                    elif player.power in ('fire', 'ice'):
                        player.clear_power()
                    else:
                        dead = True
            # アイテム取得判定
            for it in items[:]:
                if player.rect.colliderect(it.rect):
                    player.apply_power(it.kind, duration=it.duration)
                    items.remove(it)
            # ゴールとの当たり判定
            for g in goal_platforms:
                if player.rect.colliderect(g.rect):
                    state = "goal"
            #　穴に落ちた時の処理
            if player.rect.top > HEIGHT:
                dead = True
            if dead:
                state = "gameover"

            # ステージ切り替え（ゴールステージでない場合のみ）
            goal_stage_index = len(STAGE_BUILDERS) -1
            if player.rect.right > WIDTH and stage_index != goal_stage_index and state != "goal":
                stage_index_count += 1
                # 5ステージクリアしたらゴールステージへ
                if stage_index_count >= stage_num:
                    stage_index = goal_stage_index
                else:
                    # 次のランダムなステージへ（ゴールステージを除く）
                    stage_index = random.randint(0, goal_stage_index - 1)
                _, platforms, ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, falling_enemies, items, projectiles = init_game(stage_index)
                player.rect.left = 0  # プレイヤーを左端に配置
                player.rect.bottom = ground_y - Player_base_height # Y座標も初期位置に戻す
        # ゲームオーバー画面
        elif state == "gameover":
            # テキストのRectを取得するために、描画前にフォントを準備
            font = pg.font.Font(None, 100)
            text_surf = font.render("GAME OVER", True, WHITE)
            text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3))
            screen.blit(text_surf, text_rect)

            # テキストの四隅に敵を表示
            draw_text(screen, "R : Retry", 80, WIDTH // 2, HEIGHT // 2 + 60, BLACK)
            draw_text(screen, "ESC : Quit", 80, WIDTH // 2, HEIGHT // 2 + 120, BLACK)
            pg.display.flip()

            if keys[pg.K_r]:
                # init_game の戻り値に合わせる
                player, platforms, ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, falling_enemies, items, projectiles = init_game(0)
                stage_index = 0
                stage_index_count = 0
                state = "start"
            elif keys[pg.K_ESCAPE]:
                running = False
            continue

        # ゴール画面
        elif state == "goal":
            font = pg.font.Font(None, 100)
            text_surf = font.render("GOAL!!", True, GOLD)
            text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3))
            screen.blit(text_surf, text_rect)
            draw_text(screen, f"Clear Time: {play_time:.2f}", 50, WIDTH // 2, HEIGHT // 2, WHITE)
            draw_text(screen, "R : Retry", 80, WIDTH // 2, HEIGHT // 2 + 60, BLACK)
            draw_text(screen, "ESC : Quit", 80, WIDTH // 2, HEIGHT // 2 + 120, BLACK)
            pg.display.flip()
            if keys[pg.K_r]:
                # init_game の戻り値に合わせる
                player, platforms, ground_platforms, floating_platforms, hatena_platforms, goal_platforms, enemies, falling_enemies, items, projectiles = init_game(0)
                stage_index = 0
                stage_index_count = 0
                play_time = 0.0
                state = "start"
            elif keys[pg.K_ESCAPE]:
                running = False
            continue

        #背景描画
        screen.blit(bg_img, (0, 0))
        # 地面を描画
        for p in ground_platforms:
            # 地面はタイル状に描画
            # 元画像の縦横比を維持し、p.heightを基準にリサイズ
            orig_w, orig_h = ground_img.get_size()
            scaled_img = pg.transform.scale(ground_img, (p.width, p.height))
            screen.blit(scaled_img, p)
        # 浮遊ブロックを描画 (ice_block.png)
        for p in floating_platforms:
            # 元画像の縦横比を維持し、p.heightを基準にリサイズ
            orig_w, orig_h = block_img.get_size()
            scaled_img = pg.transform.scale(block_img, (p.width, p.height))
            # 当たり判定pを、リサイズ後の画像に合わせて更新
            p.size = scaled_img.get_size()
            p.center = p.center # 元の中心位置を維持
            screen.blit(scaled_img, p)
        # はてなブロックを描画 (hatena_block.png)
        for p in hatena_platforms:
            p.draw(screen)
        # ゴールを描画 (goal_pole.png)
        for p in goal_platforms:
            p.draw(screen)

        # 描画
        for it in items:
            it.draw(screen)
        for fe in falling_enemies:
            fe.draw(screen)
        for e in enemies:
            e.draw(screen)
        for p in projectiles:
            p.draw(screen)
        player.draw(screen)

        # 現在の能力を右上に表示
        power_display.draw(screen, player.power)
        # タイムを左上に表示(黒い四角の上に白文字)
        draw_text(screen, f"Time: {play_time:.2f}", 50, 100, 50, WHITE)
        draw_text(screen, "< >: Move    SPACE : Jump", 30, 150, 100, BLACK)
        draw_text(screen,"X : ball launch", 30, 100, 150, BLACK)
        draw_text(screen, f"Stage Cleared: {stage_index_count}/{stage_num}", 30, WIDTH // 2, 50, BLACK)
        pg.display.flip()

    pg.quit()


if __name__ == '__main__':
    main()
