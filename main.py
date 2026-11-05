import pygame
import sys
import random
import os

# 初期化
pygame.init()
pygame.mixer.init()

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 640
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Evolution Puyo - Next Preview Edition")

clock = pygame.time.Clock()

GRID_SIZE = 80  # 横6列（480 ÷ 80）
COLS = SCREEN_WIDTH // GRID_SIZE
ROWS = SCREEN_HEIGHT // GRID_SIZE

font = pygame.font.SysFont(None, 48)
score_font = pygame.font.SysFont(None, 32)
small_font = pygame.font.SysFont(None, 24)

# 画像の読み込み
try:
    block_images = {
        "1000": pygame.transform.scale(pygame.image.load("1000.jpg").convert(), (GRID_SIZE, GRID_SIZE)),
        "2000": pygame.transform.scale(pygame.image.load("2000.jpg").convert(), (GRID_SIZE, GRID_SIZE)),
        "5000": pygame.transform.scale(pygame.image.load("5000.jpg").convert(), (GRID_SIZE, GRID_SIZE)),
        "10000": pygame.transform.scale(pygame.image.load("10000.jpg").convert(), (GRID_SIZE, GRID_SIZE)),
    }
except Exception as e:
    print(f"画像の読み込みに失敗しました: {e}")
    pygame.quit()
    sys.exit()

# 効果音の読み込み
evolve_sound = None
gameover_sound = None
try:
    if os.path.exists("evolve.wav"):
        evolve_sound = pygame.mixer.Sound("evolve.wav")
    if os.path.exists("gameover.wav"):
        gameover_sound = pygame.mixer.Sound("gameover.wav")
except Exception as e:
    print(f"サウンドのロードに失敗しました: {e}")

game_state = "TITLE"

board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
BLOCK_TYPES = ["1000", "2000", "5000"]

current_type = random.choice(BLOCK_TYPES)
next_type = random.choice(BLOCK_TYPES)

block_x = COLS // 2 - 1
block_y = 0

fall_time = 0
score = 0
floating_animations = []

HIGH_SCORE_FILE = "highscore.txt"

def load_high_score():
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            return 0
    return 0

def save_high_score(new_high_score):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(new_high_score))
    except Exception as e:
        print(f"ハイスコアの保存に失敗しました: {e}")

high_score = load_high_score()

initial_fall_speed = 400
fast_fall_speed = 50

def get_current_fall_speed():
    speed = initial_fall_speed - (score // 10000) * 40
    return max(140, speed)  # 最高速度の上限（緩やかな設定）

def reset_game():
    global board, current_type, next_type, block_x, block_y, score, fall_time, is_down_pressed
    board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    current_type = random.choice(BLOCK_TYPES)
    next_type = random.choice(BLOCK_TYPES)
    block_x = COLS // 2 - 1
    block_y = 0
    score = 0
    fall_time = 0
    is_down_pressed = False

def reset_block():
    global block_x, block_y, current_type, next_type, game_state, high_score
    block_x = COLS // 2 - 1
    block_y = 0
    current_type = next_type
    next_type = random.choice(BLOCK_TYPES)
    
    if board[block_y][block_x] != 0:
        game_state = "GAMEOVER"
        if gameover_sound:
            gameover_sound.play()
        if score > high_score:
            high_score = score
            save_high_score(high_score)

def get_connected_group(start_r, start_c, target_type):
    visited = set()
    queue = [(start_r, start_c)]
    visited.add((start_r, start_c))
    
    group = []
    while queue:
        r, c = queue.pop(0)
        group.append((r, c))
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                if (nr, nc) not in visited and board[nr][nc] == target_type:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
    return group

def check_and_evolve_blocks():
    global score
    checked = set()
    evolved = False

    for r in range(ROWS):
        for c in range(COLS):
            b_type = board[r][c]
            if b_type != 0 and (r, c) not in checked:
                group = get_connected_group(r, c, b_type)
                for coord in group:
                    checked.add(coord)
                
                # 1. 1000が5個以上で 5000 に進化
                if b_type == "1000" and len(group) >= 5:
                    first = group[0]
                    board[first[0]][first[1]] = "5000"
                    for r_idx, c_idx in group[1:]:
                        board[r_idx][c_idx] = 0
                    score += 5000
                    evolved = True
                    if evolve_sound:
                        evolve_sound.play()

                # 2. 2000が5個以上で 10000になって上部に消えるアニメーション
                elif b_type == "2000" and len(group) >= 5:
                    for r_idx, c_idx in group:
                        pixel_x = c_idx * GRID_SIZE
                        pixel_y = r_idx * GRID_SIZE
                        floating_animations.append({
                            "x": pixel_x,
                            "y": pixel_y,
                            "timer": 30
                        })
                        board[r_idx][c_idx] = 0
                        
                    score += 25000
                    evolved = True
                    if evolve_sound:
                        evolve_sound.play()
                    
                # 3. 5000が2個以上で 10000になって上部に消えるアニメーション
                elif b_type == "5000" and len(group) >= 2:
                    for r_idx, c_idx in group:
                        pixel_x = c_idx * GRID_SIZE
                        pixel_y = r_idx * GRID_SIZE
                        floating_animations.append({
                            "x": pixel_x,
                            "y": pixel_y,
                            "timer": 30
                        })
                        board[r_idx][c_idx] = 0
                        
                    score += 10000 * len(group)
                    evolved = True
                    if evolve_sound:
                        evolve_sound.play()
                    
    return evolved

def apply_gravity():
    moved = False
    for c in range(COLS):
        for r in range(ROWS - 1, 0, -1):
            if board[r][c] == 0 and board[r-1][c] != 0:
                board[r][c] = board[r-1][c]
                board[r-1][c] = 0
                moved = True
    return moved

is_down_pressed = False

while True:
    dt = clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if score > high_score and game_state == "GAMEOVER":
                save_high_score(score)
            pygame.quit()
            sys.exit()
        
        if event.type == pygame.KEYDOWN:
            if game_state == "TITLE":
                if event.key == pygame.K_SPACE:
                    reset_game()
                    game_state = "PLAYING"
            
            elif game_state == "PLAYING":
                if event.key == pygame.K_LEFT:
                    if block_x > 0 and board[block_y][block_x - 1] == 0:
                        block_x -= 1
                elif event.key == pygame.K_RIGHT:
                    if block_x < COLS - 1 and board[block_y][block_x + 1] == 0:
                        block_x += 1
                elif event.key == pygame.K_DOWN:
                    is_down_pressed = True
            
            elif game_state == "GAMEOVER":
                if event.key == pygame.K_SPACE:
                    game_state = "TITLE"
        
        elif event.type == pygame.KEYUP:
            if game_state == "PLAYING" and event.key == pygame.K_DOWN:
                is_down_pressed = False

    if game_state == "PLAYING":
        current_normal_speed = get_current_fall_speed()
        fall_speed = fast_fall_speed if is_down_pressed else current_normal_speed

        fall_time += dt
        if fall_time >= fall_speed:
            if block_y + 1 >= ROWS or board[block_y + 1][block_x] != 0:
                board[block_y][block_x] = current_type
                
                while True:
                    is_evolved = check_and_evolve_blocks()
                    if is_evolved:
                        while apply_gravity():
                            pass
                    else:
                        break

                reset_block()
            else:
                block_y += 1
            
            fall_time = 0

    # アニメーション更新
    for anim in floating_animations[:]:
        anim["y"] -= 4
        anim["timer"] -= 1
        if anim["timer"] <= 0:
            floating_animations.remove(anim)

    # 描画処理
    screen.fill((20, 20, 40))

    if game_state == "TITLE":
        title_text = font.render("PHOTO PUZZLE", True, (255, 220, 50))
        sub_title = small_font.render("Complete Edition with Next", True, (200, 200, 200))
        start_prompt = score_font.render("Press [SPACE] to Start", True, (100, 255, 100))
        
        screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 200))
        screen.blit(sub_title, (SCREEN_WIDTH // 2 - sub_title.get_width() // 2, 255))
        screen.blit(start_prompt, (SCREEN_WIDTH // 2 - start_prompt.get_width() // 2, 400))

    else:
        for r in range(ROWS):
            for c in range(COLS):
                cell = board[r][c]
                if cell != 0:
                    screen.blit(block_images[cell], (c * GRID_SIZE, r * GRID_SIZE))

        if game_state == "PLAYING":
            screen.blit(block_images[current_type], (block_x * GRID_SIZE, block_y * GRID_SIZE))

        for anim in floating_animations:
            screen.blit(block_images["10000"], (anim["x"], anim["y"]))

        # スコアとハイスコアの表示
        score_surface = score_font.render(f"SCORE: {score}", True, (255, 255, 255))
        high_score_surface = small_font.render(f"HIGH SCORE: {high_score}", True, (250, 220, 50))
        screen.blit(score_surface, (20, 15))
        screen.blit(high_score_surface, (20, 50))

        # --- 【ネクストブロックの予告表示】 ---
        # 80×80の大きなブロックサイズに合わせたプレビュー枠
        next_label = small_font.render("NEXT", True, (200, 200, 200))
        screen.blit(next_label, (380, 15))
        pygame.draw.rect(screen, (100, 100, 150), (370, 40, 90, 90), 2)
        # ネクストブロックを少し縮小してキレイに枠内に収める
        next_preview_img = pygame.transform.scale(block_images[next_type], (70, 70))
        screen.blit(next_preview_img, (380, 50))

        if game_state == "GAMEOVER":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))

            game_over_text = font.render("GAME OVER", True, (255, 50, 50))
            final_score_text = score_font.render(f"Score: {score}", True, (255, 255, 255))
            best_score_text = score_font.render(f"Best: {high_score}", True, (250, 220, 50))
            retry_prompt = small_font.render("Press [SPACE] for Title", True, (200, 200, 200))
            
            screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 70))
            screen.blit(final_score_text, (SCREEN_WIDTH // 2 - final_score_text.get_width() // 2, SCREEN_HEIGHT // 2 - 20))
            screen.blit(best_score_text, (SCREEN_WIDTH // 2 - best_score_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))
            screen.blit(retry_prompt, (SCREEN_WIDTH // 2 - retry_prompt.get_width() // 2, SCREEN_HEIGHT // 2 + 75))

    pygame.display.flip()