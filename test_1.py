from pygame.locals import *
import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SCREEN_FLAG = False



def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_w: (0, -1),
        pg.K_s: (0, +1),
        pg.K_a: (-1, 0),
        pg.K_d: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # 横以外の向きこうかとん
        img_2 = pg.transform.rotozoom(pg.image.load(f"fig/2.png"), 0, 0.8)
        img0_2 = pg.transform.flip(img_2, True, False)  # 横向きのこうかとん
        self.imgs = {
            (+1, 0): img_2,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0_2,  # 左
            (-1, +1): img0,  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): img,  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)



class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Life:
    """
    残りライフに関するクラス
    """
    def __init__(self, color: tuple[int, int, int]):
        self.valu = 10
        self.fonto = pg.font.SysFont("hgp創英角ﾎﾟｯﾌﾟ体", 30)
        self.img = self.fonto.render(f"ライフ {self.valu}", 0, (0, 255, 100))
        self.rct = self.img.get_rect()
        self.rct.center = [100, HEIGHT-50]


    def update(self, screen:pg.Surface):
       self.img = self.fonto.render(f"ライフ {self.valu}", 0, (100, 255, 255))
       screen.blit(self.img, self.rct)


def game_start(screen: pg.Surface):
    """
    ゲームスタート時に、操作方法表示、ゲーム開始操作設定
    """
    
    fonto = pg.font.SysFont("hg正楷書体pro", 50)
    txt1 = fonto.render("Game Start : escキー", True, (255, 255, 255))
    txt2 = fonto.render("操作方法1：WASDで操作", True, (255, 255, 255))
    txt3 = fonto.render("操作方法2：スペースでジャンプ", True, (255, 255, 255))
    txt4 = fonto.render("操作方法3：エンターと左クリックで攻撃", True, (255, 255, 255))
    game_start = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_start, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_start.set_alpha(128)
    screen.blit(game_start, (0, 0))  # 半透明画面描画
    screen.blit(txt1, [WIDTH/2-450, HEIGHT/2-100])  # Game Start描画
    screen.blit(txt2, [WIDTH/2-450, HEIGHT/2-50])
    screen.blit(txt3, [WIDTH/2-450, HEIGHT/2])
    screen.blit(txt4, [WIDTH/2-450, HEIGHT/2+50])
    pg.display.update()

def game_clear(screen: pg.Surface):
    """
    ゲームクリア時に、「Game Clear」と表示
    """
    bg_img_n8 = pg.image.load("fig/8.png")  # こうかとん画像ロード
    fonto = pg.font.Font(None, 100)
    txt = fonto.render("Game Clear", True, (255, 255, 255))
    game_clear = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_clear, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_clear.set_alpha(128)
    screen.blit(game_clear, (0, 0))  # 半透明画面描画
    screen.blit(txt, [WIDTH/2-200, HEIGHT/2])  # Game Over描画
    screen.blit(bg_img_n8, [WIDTH/2-270, HEIGHT/2])  # 泣いてるこうかとん描画
    screen.blit(bg_img_n8, [WIDTH/2+200, HEIGHT/2])
    print("kansujikkou")
    pg.display.update()
    time.sleep(5)

def game_over(screen: pg.Surface) -> None:
    """
    ゲームオーバー時に、半透明の黒い画面上で「Game Over」と表示し、
    泣いているこうかとん画像を張り付ける
    """
    bg_img_n8 = pg.image.load("fig/8.png")  # こうかとん画像ロード
    fonto = pg.font.Font(None, 100)
    txt = fonto.render("Game Over", True, (255, 255, 255))
    game_over = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_over, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_over.set_alpha(128)
    screen.blit(game_over, (0, 0))  # 半透明画面描画
    screen.blit(txt, [WIDTH/2-200, HEIGHT/2])  # Game Over描画
    screen.blit(bg_img_n8, [WIDTH/2-270, HEIGHT/2])  # 泣いてるこうかとん描画
    screen.blit(bg_img_n8, [WIDTH/2+200, HEIGHT/2])
    print("kansujikkou")
    pg.display.update()
    time.sleep(5)


def main():
    pg.display.set_caption("こうかとんの村")
    SCREEN_FLAG = False
    pg.display.set_caption("title")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/Game-battle-background-1024x576.png")
    screen.blit(bg_img, [0, 0])
    game_start(screen)  # タイトル画面の関数を呼び出し
    pg.display.update()
        
    while SCREEN_FLAG == False:  # Falseのときタイトル画面
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:  # エスケープキーが押されたら
                SCREEN_FLAG = True  # 画面状態をTrueにする
                pg.quit

    if SCREEN_FLAG == True:  # 画面状態がTrueならゲーム画面を表示
        pg.display.set_caption("真！こうかとん無双")
        screen = pg.display.set_mode((WIDTH, HEIGHT))
        bg_img = pg.image.load(f"fig/Game-battle-background-1024x576.png")

        bird = Bird(3, (900, 400))
        beams = pg.sprite.Group()
        exps = pg.sprite.Group()

        l_scr = Life((0, 255, 255))  # 残りライフ

        tmr = 0
        clock = pg.time.Clock()
        while True:
            key_lst = pg.key.get_pressed()
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return 0
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    beams.add(Beam(bird))
                if event.type == pg.KEYDOWN and event.key == pg.K_1:  # 1が押されたらライフを減らす
                    l_scr.valu-=1
                    if l_scr.valu == 0:  # ライフが0なら
                        game_over(screen)  # ゲームオーバー
                        return
                if event.type == pg.KEYDOWN and event.key == pg.K_2:  # 2が押されたらゲームクリア
                    game_clear(screen)
                    return
                if event.type == pg.KEYDOWN and event.key == pg.K_3:  # 3が押されたらゲームオーバー
                    game_over(screen)
                    return
            screen.blit(bg_img, [0, 0])

            #if 敵に当たる、攻撃が当たったら:
            #l_scr.valu-=1  残りライフを1減らす
            


            bird.update(key_lst, screen)
            l_scr.update(screen)  # 残りライフ
            beams.update()
            beams.draw(screen)
            exps.update()
            exps.draw(screen)
            pg.display.update()
            tmr += 1
            clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
