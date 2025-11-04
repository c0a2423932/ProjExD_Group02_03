import os
import math
import pygame as pg
import random


WIDTH, HEIGHT = 900, 600
FPS = 60
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 色定義
BG = (135, 206, 235)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (50, 205, 50)
BROWN = (139, 69, 19)
GOLD = (255, 215, 0)
RED = (220, 20, 60)
YELLOW = (255, 255, 0)
SILVER = (192, 192, 192)
FLAG_COLOR = (0, 0, 0)
PLAYER_DEFAULT_COLOR = (220, 20, 60)  # 赤


class Player:
    def __init__(self, x, y):
        self.rect = pg.Rect(x, y, 40, 50)
        self.vx = 0
        self.vy = 0
        self.speed = 5
        self.jump_power = 14
        # 追加機能1(近藤): パワーアップ機能の状態を保持
        self.base_speed = self.speed
        self.base_jump_power = self.jump_power
        self.jump_enabled = True
        # パワーアップ状態
        self.power = None  # 'fire','ice','jump','suberu','muteki'
        self.power_time = 0.0
        self.can_kill_on_touch = False
        # 衝突後の短い無敵フレーム（秒）
        self.invul_time = 0.0
        # 向きフラグ: 1 = 右, -1 = 左
        # 追加機能3(近藤): 向き（弾発射時に使用）
        self.facing = 1
        self.on_ground = False
        self.color = PLAYER_DEFAULT_COLOR
        self.color_timer = 0  # 色保持用タイマー（フレーム数）

    def handle_input(self, keys):
        self.vx = 0
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            self.vx = -self.speed
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            self.vx = self.speed
        # 移動時に向きを更新する
        if self.vx > 0:
            self.facing = 1
        elif self.vx < 0:
            self.facing = -1
        if (keys[pg.K_SPACE] or keys[pg.K_z] or keys[pg.K_UP]) and self.on_ground and self.jump_enabled:
            self.vy = -self.jump_power
            self.on_ground = False

    def apply_gravity(self):
        self.vy += 0.8  # 重力
        if self.vy > 20:
            self.vy = 20

    def update(self, platforms, blocks, items):
        # 水平移動
        self.rect.x += int(self.vx)
        self.collide(self.vx, 0, platforms)
        # 垂直移動
        self.apply_gravity()
        self.rect.y += int(self.vy)
        self.on_ground = False
        self.collide(0, self.vy, platforms)

        # ブロックを下から叩く
        for b in blocks:
            if self.rect.colliderect(b.rect):
                if self.vy < 0 and self.rect.top < b.rect.bottom:
                    self.rect.top = b.rect.bottom
                    self.vy = 0
                    b.activate(items)

        # アイテム取得
        for i in items[:]:
            if self.rect.colliderect(i.rect):
                self.color = i.color
                self.color_timer = FPS * 5  # 5秒間色を保持

        # 色タイマー処理
        if self.color_timer > 0:
            self.color_timer -= 1
        elif self.color_timer == 0:
            self.color = PLAYER_DEFAULT_COLOR

    def collide(self, vx, vy, platforms):
        for p in platforms:
            if self.rect.colliderect(p):
                if vx > 0:  # 右
                    self.rect.right = p.left
                if vx < 0:  # 左
                    self.rect.left = p.right
                if vy > 0:  # 落下
                    self.rect.bottom = p.top
                    self.vy = 0
                    self.on_ground = True
                if vy < 0:  # ジャンプ
                    self.rect.top = p.bottom
                    self.vy = 0

    def draw(self, surf):
        # パワーアップに応じてキャラクターの色が変わる
        if self.power == 'muteki':
            # レインボー
            t = pg.time.get_ticks() / 100.0
            r = int((1 + math.sin(t)) * 127) % 256
            g = int((1 + math.sin(t + 2)) * 127) % 256
            b = int((1 + math.sin(t + 4)) * 127) % 256
            self.color = (r, g, b)
        elif self.power == 'fire':
            self.color = (255, 140, 0)  # オレンジ（火）
        elif self.power == 'ice':
            self.color = (100, 200, 255)  # 水色（氷）
        elif self.power == 'jump':
            self.color = (255, 215, 0)  # ゴールド
        elif self.power == 'suberu':
            self.color = (160, 160, 160)  # グレー
        # else:
        #     self.color = RED
        pg.draw.rect(surf, self.color, self.rect)

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
        elif power == 'suberu':
            self.speed = int(self.base_speed * 1.6)
            self.jump_enabled = False
        elif power == 'muteki':
            # muteki: 敵の衝突を無視（無敵状態）
            pass

    def update_power(self, dt: float):
        """
        時間切れが来たら元の状態に戻る
        """
        # パワー時間の減少
        if self.power_time > 0:
            self.power_time -= dt
            if self.power_time <= 0:
                # 時間切れで元に戻す
                self.power = None
                self.power_time = 0.0
                self.speed = self.base_speed
                self.jump_power = self.base_jump_power
                self.jump_enabled = True
                self.can_kill_on_touch = False
        # 無敵時間の減少
        if self.invul_time > 0:
            self.invul_time -= dt
            if self.invul_time < 0:
                self.invul_time = 0.0

    def clear_power(self):
        """能力が切れたら、基本ステータスに戻す"""
        self.power = None
        self.power_time = 0.0
        self.speed = self.base_speed
        self.jump_power = self.base_jump_power
        self.jump_enabled = True
        self.can_kill_on_touch = False

# ハテナブロック
class hatena:
    def __init__(self, x, y):
        self.rect = pg.Rect(x, y, 40, 40)
        self.used = False

    def activate(self, items):
        if not self.used:
            self.used = True
            kind = random.choice(["fire", "ice", "jump", "suberu", "muteki"])
            item = Item(self.rect.x + 10, self.rect.y - 25, kind)
            items.append(item)

    def draw(self, surf):
        color = SILVER if self.used else YELLOW
        pg.draw.rect(surf, color, self.rect)
        if not self.used:
            pg.draw.rect(surf, BLACK, self.rect, 2)
            font = pg.font.Font(None, 30)
            q = font.render("?", True, BLACK)
            surf.blit(q, (self.rect.x + 13, self.rect.y + 13))

#アイテム
class Item:
    color_dict = {
        'fire': (255, 100, 0),
        'ice': (100, 200, 255),
        'jump': (255, 215, 0),
        'suberu': (160, 160, 160),
        'muteki': (255, 0, 255),
    }

    def __init__(self, x, y, kind: str, w=16, h=16, duration: float = 8.0):
        self.rect = pg.Rect(x, y, w, h)
        self.kind = kind  # 'fire','ice','jump','suberu','muteki'
        self.color = self.color_dict.get(kind, (255, 215, 0))
        self.vy = -4
        self.rise_frames = 20
        self.stop_y = y - 10
        self.duration = duration

    def update(self):
        if self.rise_frames > 0:
            self.rect.y += self.vy
            self.rise_frames -= 1
            if self.rise_frames == 0:
                self.rect.y = self.stop_y

    def draw(self, surf):
        pg.draw.rect(surf, self.color, self.rect)


class Enemy:
    def __init__(self, x, y, w=40, h=40, left_bound=None, right_bound=None):
        self.rect = pg.Rect(x, y, w, h)
        self.vx = 2
        self.left_bound = left_bound
        self.right_bound = right_bound

    def update(self):
        self.rect.x += self.vx
        if self.left_bound and self.rect.left < self.left_bound:
            self.rect.left = self.left_bound
            self.vx *= -1
        if self.right_bound and self.rect.right > self.right_bound:
            self.rect.right = self.right_bound
            self.vx *= -1

    def draw(self, surf):
        pg.draw.rect(surf, (80, 0, 80), self.rect)


class Projectile:
    """プレイヤーが火/氷の力を持っているときに発射する弾"""
    def __init__(self, x, y, kind: str, direction: int, speed: float = 10.0):
        self.rect = pg.Rect(int(x), int(y), 10, 10)
        self.kind = kind
        self.vx = speed * (1 if direction >= 0 else -1)

    def update(self):
        self.rect.x += int(self.vx)

    def draw(self, surf):
        color = (255, 100, 0) if self.kind == 'fire' else (100, 200, 255)
        pg.draw.rect(surf, color, self.rect)


def build_level():
    # 簡易的な静的レベル：プラットフォームをRectで定義
    platforms = []
    # 地面
    platforms.append(pg.Rect(0, HEIGHT - 40, WIDTH, 40))
    # 一部の乗り場
    platforms.append(pg.Rect(100, 460, 200, 20))
    platforms.append(pg.Rect(380, 360, 180, 20))
    platforms.append(pg.Rect(600, 280, 220, 20))
    platforms.append(pg.Rect(250, 520, 120, 20))
    platforms.append(pg.Rect(480, 520, 80, 20))
    return platforms


def main():
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Hatena")
    clock = pg.time.Clock()

    player = Player(50, HEIGHT - 90)
    platforms = build_level()
    enemies = [Enemy(420, HEIGHT - 80, left_bound=400, right_bound=760)]

    # レベルに配置するパワーアップアイテム
    items = [
    ]

    # 球発射
    projectiles = []
    blocks = [hatena(350, 400), hatena(500, 240)]
    items = []
    goal_rect = pg.Rect(WIDTH - 50, HEIGHT - 180, 10, 140)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            if event.type == pg.KEYDOWN and event.key == pg.K_x:
                # プレイヤーが火または氷の力を持っている場合にのみ発射物を生成します
                if player.power in ('fire', 'ice'):
                    # プレイヤーの前方に出現
                    px = player.rect.centerx + player.facing * (player.rect.width//2 + 5)
                    py = player.rect.centery
                    projectiles.append(Projectile(px, py, player.power, player.facing))

        keys = pg.key.get_pressed()
        player.handle_input(keys)
        player.update(platforms, blocks, items)

        # パワーアップタイマーを更新する
        player.update_power(dt)
        for e in enemies:
            e.update()

        # ゴール判定
        if player.rect.colliderect(goal_rect):
            print("🎉 ゴール！")
            running = False

        # 発射物を更新する
        for p in projectiles[:]:
            p.update()
            # 画面外の場合は削除
            if p.rect.right < 0 or p.rect.left > WIDTH:
                try:
                    projectiles.remove(p)
                except ValueError:
                    pass
            else:
                # 発射物と敵の衝突
                for e in enemies[:]:
                    if p.rect.colliderect(e.rect):
                        try:
                            enemies.remove(e)
                        except ValueError:
                            pass
                        try:
                            projectiles.remove(p)
                        except ValueError:
                            pass
                        # score += 5
                        break

        # コインの取得
        # for c in coins[:]:
        #     if player.rect.colliderect(c):
        #         coins.remove(c)
        #         score += 1

        # アイテムのピックアップ（パワーアップ）
        for it in items[:]:
            if player.rect.colliderect(it.rect):
                player.apply_power(it.kind, duration=it.duration)
                items.remove(it)

        # 敵との衝突
        dead = False
        for e in enemies[:]:
            if player.rect.colliderect(e.rect):
                # 変更: muteki（無敵）は敵に触れると敵を倒す
                if player.power == 'muteki':
                    try:
                        enemies.remove(e)
                    except ValueError:
                        pass
                    player.vy = -8
                    continue
                # プレイヤーが火/氷の力を持っている場合、触れても敵は倒さず、デフォルト状態に戻る
                # 敵を倒すのは踏みつけ（プレイヤーが下向きに当たったとき）のみ
                if (player.vy > 0 and player.rect.bottom - e.rect.top < 20):
                    try:
                        enemies.remove(e)
                    except ValueError:
                        pass
                    player.vy = -8
                else:
                    # 火/氷のパワーを持っている場合、触れても敵は倒さずパワーだけ消える。
                    # プレイヤーはその場に留まる（死なない、跳ね返らない）
                    if player.power in ('fire', 'ice'):
                        player.clear_power()
                        i = 0
                        # 何もしない（そのまま留まる）
                        pass
                    
                    else:
                        dead = True

        if player.rect.top > HEIGHT:
            dead = True

        if dead:
            # リスポーン
            player = Player(50, HEIGHT - 90)
            enemies = [Enemy(420, HEIGHT-80, left_bound=400, right_bound=760)]
            # coins = [pg.Rect(150, 420, 12, 12), pg.Rect(420, 320, 12, 12), pg.Rect(650, 240, 12, 12), pg.Rect(270, 480, 12, 12)]
            # アイテムも復活させる
            items = [
            ]
            # score = 0

        # draw
        screen.fill(BG)
        for p in platforms:
            pg.draw.rect(screen, BROWN, p)
        # for c in coins:
        #     pg.draw.rect(screen, GOLD, c)
        for e in enemies:
            e.draw(screen)
        for p in projectiles:
            p.draw(screen)
        for b in blocks:
            b.draw(screen)
        for i in items:
            i.draw(screen)
        pg.draw.rect(screen, FLAG_COLOR, goal_rect)
        player.draw(screen)
        pg.display.flip()

    pg.quit()

if __name__ == '__main__':
    main()
