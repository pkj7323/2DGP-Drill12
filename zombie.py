from pico2d import *

import random
import math
import game_framework
import game_world
from behavior_tree import BehaviorTree, Action, Sequence, Condition, Selector
import play_mode


# zombie Run Speed
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# zombie Action Speed
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10.0

animation_names = ['Walk', 'Idle']


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images == None:
            Zombie.images = {}
            for name in animation_names:
                Zombie.images[name] = [load_image("./zombie/" + name + " (%d)" % i + ".png") for i in range(1, 11)]
            Zombie.font = load_font('ENCR10B.TTF', 40)
            Zombie.marker_image = load_image('hand_arrow.png')


    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, 1180)
        self.y = y if y else random.randint(100, 924)
        self.load_images()
        self.dir = 0.0      # radian 값으로 방향을 표시
        self.speed = 0.0
        self.frame = random.randint(0, 9)
        self.state = 'Idle'
        self.ball_count = 0
        self.tx = 0
        self.ty = 0
        self.patrol_location = [(43,274),(1118,274),(1050,494),(575,804),(235,991),(575,804),(1050,494),(1118,274)]
        self.loc_no=0

        self.build_behavior_tree()


    def get_bb(self):
        return self.x - 50, self.y - 50, self.x + 50, self.y + 50


    def update(self):
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * game_framework.frame_time) % FRAMES_PER_ACTION
        self.bt.run()


    def draw(self):
        if math.cos(self.dir) < 0:
            Zombie.images[self.state][int(self.frame)].composite_draw(0, 'h', self.x, self.y, 100, 100)
        else:
            Zombie.images[self.state][int(self.frame)].draw(self.x, self.y, 100, 100)
        self.font.draw(self.x - 10, self.y + 60, f'{self.ball_count}', (0, 0, 255))
        draw_rectangle(*self.get_bb())
        Zombie.marker_image.draw(self.tx + 10, self.ty - 10)

    def handle_event(self, event):
        pass

    def handle_collision(self, group, other):
        if group == 'zombie:ball':
            self.ball_count += 1


    def set_target_location(self, x=None, y=None):#(action node)
        if x is None and y is None:
            return ValueError("x,y 오류")
        self.tx = x
        self.ty = y
        return BehaviorTree.SUCCESS

    def distance_less_than(self, x1, y1, x2, y2, r):
        distance2 = (x1 - x2) ** 2 + (y1 - y2) ** 2
        return distance2 < (PIXEL_PER_METER* r) ** 2 #float의 비교는 정확히 같을 수 없음

    def move_slightly_to(self, tx, ty):
        self.dir = math.atan2(ty - self.y, tx - self.x)
        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)

    def set_target_behind(self):
        self.dir = math.atan2(play_mode.boy.y - self.y, play_mode.boy.x - self.x)
        self.dir = -self.dir
        distance = math.sqrt((play_mode.boy.x - self.x)**2 + (play_mode.boy.y - self.y)**2)
        self.tx = self.x + distance * math.cos(self.dir)
        self.ty = self.y + distance * math.sin(self.dir)

    def move_to(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(self.tx, self.ty)
        if self.distance_less_than(self.x, self.y, self.tx, self.ty, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def set_random_location(self):
        self.tx = random.randint(100, 1280-100)
        self.ty = random.randint(100, 1024-100)
        return BehaviorTree.SUCCESS

    def is_boy_ball_less(self):
        if self.ball_count > play_mode.boy.ball_count:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def is_boy_nearby(self, distance):
        if self.distance_less_than(play_mode.boy.x,play_mode.boy.y,self.x,self.y,distance):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def move_to_boy(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(play_mode.boy.x,play_mode.boy.y)
        if self.distance_less_than(play_mode.boy.x,play_mode.boy.y,self.x,self.y,r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def get_patrol_location(self):
        self.tx,self.ty = self.patrol_location[self.loc_no]
        self.loc_no = (self.loc_no + 1) % len(self.patrol_location)
        return BehaviorTree.SUCCESS

    def build_behavior_tree(self):
        move = Action("이동",self.move_to)
        move_boy = Action("보이에게 이동",self.move_to_boy)
        ball_check = Condition("좀비가 볼이 더많은가?",self.is_boy_ball_less)
        set_loc_run_away = Action("보이에게서 멀어지는 위치 설정",self.set_target_behind)

        num_ball_compare_sequence = Sequence("볼이 더 많으면 보이에게 이동",ball_check,move_boy)
        run_away_sequence = Sequence("볼이 더적으면 도망가기",set_loc_run_away,move)

        chase_or_run_away_selector = Selector("볼 비교 이동 선택자",num_ball_compare_sequence,run_away_sequence)

        boy_near_check = Condition("근처에 보이가 있는가?",self.is_boy_nearby,7)

        chase_or_run_away_sequence = Sequence("보이 근처 시퀀스",boy_near_check,chase_or_run_away_selector)

        set_loc_random = Action("타겟 랜덤위치 설정",self.set_random_location)
        wander = Sequence("방황",set_loc_random,move)

        root = selector = Selector("root",chase_or_run_away_sequence,wander)




        self.bt = BehaviorTree(root)