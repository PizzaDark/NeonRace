import os
import sys
import math
import random
import pymunk
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QComboBox, QSpinBox, QLineEdit,
                             QColorDialog, QFileDialog, QScrollArea, QFrame, QStackedWidget,
                             QGraphicsScene, QGraphicsPathItem, QGraphicsBlurEffect)
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QImage, QPixmap, 
                         QTransform, QRadialGradient, QLinearGradient, QPainterPathStroker, QIcon)
import wave
import struct
from collections import deque
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QTimer, QPointF, QSize, QUrl, QThread, pyqtSignal

class AudioPeakThread(QThread):
    peak_detected = pyqtSignal(float)
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.active = True
    def run(self):
        try:
            with wave.open(self.file_path, 'rb') as wf:
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                chunk_frames = framerate // 60
                energy_history = deque(maxlen=30)
                cooldown = 0
                while self.active:
                    data = wf.readframes(chunk_frames)
                    if not data: 
                        wf.rewind()
                        continue
                    samples = []
                    if sampwidth == 2:
                        samples = struct.unpack(f"<{len(data)//2}h", data)
                    elif sampwidth == 1:
                        samples = [(b - 128) * 256 for b in data]
                    if samples:
                        step = channels * 2 if channels > 0 else 2
                        sampled = samples[::step]
                        if sampled:
                            energy = math.sqrt(sum(float(s)*s for s in sampled) / len(sampled))
                        else:
                            energy = 0
                        energy_history.append(energy)
                        if len(energy_history) == energy_history.maxlen:
                            sorted_history = sorted(list(energy_history))
                            bg_noise = sum(sorted_history[4:-4]) / (len(sorted_history) - 8)
                            if energy > bg_noise * 1.55 and energy > 800:
                                if cooldown == 0:
                                    self.peak_detected.emit(min(1.0, energy / 16000.0))
                                    cooldown = 12 
                        if cooldown > 0: cooldown -= 1
                    QThread.msleep(16)
        except Exception as e:
            bpm = 130
            interval_ms = int(60000 / bpm)
            while self.active:
                self.peak_detected.emit(0.8)
                for _ in range(interval_ms // 15):
                    if not self.active: break
                    QThread.msleep(15)
    def stop(self):
        self.active = False
        self.quit()
        self.wait()

DEFAULT_COLORS = ['#ff00ff', '#00ffff', '#ffff00', '#00ff55', '#ff0055', '#5500ff', '#ff8800']
TRACK_WIDTH = 540

def hex_to_rgb(hx):
    hx = hx.lstrip('#')
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))

def catmull_rom_spline(pts, steps=4):
    if len(pts) < 3: return pts
    p = [pts[0]] + pts + [pts[-1]]
    spline_pts = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i-1], p[i], p[i+1], p[i+2]
        for j in range(steps):
            t = j / steps
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * ((2*p1[0]) + (-p0[0] + p2[0])*t + (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0])*t2 + (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0])*t3)
            y = 0.5 * ((2*p1[1]) + (-p0[1] + p2[1])*t + (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1])*t2 + (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1])*t3)
            spline_pts.append((x, y))
    spline_pts.append(pts[-1])
    return spline_pts

def bake_neon_texture(path, color_rgb, blur_radius=22):
    scale = 2.0 
    r, g, b = color_rgb
    transform = QTransform().scale(scale, scale)
    scaled_path = transform.map(path)
    rect = scaled_path.boundingRect()
    
    scaled_margin = blur_radius * 3.0 * scale
    translated_path = QPainterPath()
    translated_path.addPath(scaled_path)
    translated_path.translate(-rect.left() + scaled_margin, -rect.top() + scaled_margin)
    
    scene = QGraphicsScene()
    outer_glow = QGraphicsPathItem(translated_path)
    outer_glow.setPen(QPen(Qt.PenStyle.NoPen))
    outer_glow.setBrush(QColor(r, g, b, 80))
    eff_out = QGraphicsBlurEffect()
    eff_out.setBlurRadius(blur_radius * 1.8 * scale)
    eff_out.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    outer_glow.setGraphicsEffect(eff_out)
    scene.addItem(outer_glow)
    
    inner_glow = QGraphicsPathItem(translated_path)
    inner_glow.setPen(QPen(Qt.PenStyle.NoPen))
    inner_glow.setBrush(QColor(r, g, b, 255))
    eff_in = QGraphicsBlurEffect()
    eff_in.setBlurRadius(blur_radius * 0.6 * scale)
    eff_in.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    inner_glow.setGraphicsEffect(eff_in)
    scene.addItem(inner_glow)
    
    pix_w = int(math.ceil(rect.width() + scaled_margin * 2))
    pix_h = int(math.ceil(rect.height() + scaled_margin * 2))
    scene.setSceneRect(0, 0, pix_w, pix_h)
    
    image = QImage(pix_w, pix_h, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scene.render(painter)
    painter.end()
    
    image.setDevicePixelRatio(scale)
    orig_rect = path.boundingRect()
    offset = QPointF(orig_rect.left() - blur_radius * 3.0, orig_rect.top() - blur_radius * 3.0)
    return QPixmap.fromImage(image), offset

def attach_neon_cache(shape, color_rgb, blur_radius=22, path_override=None):
    path = QPainterPath()
    if path_override is not None:
        path.addPath(path_override)
    elif isinstance(shape, pymunk.Circle):
        path.addEllipse(QPointF(shape.offset.x, shape.offset.y), shape.radius, shape.radius)
    elif getattr(shape, '_is_rect', False):
        w, h = shape._w, shape._h
        r = shape._corner_radius
        path.addRoundedRect(-w/2, -h/2, w, h, r, r)
    elif isinstance(shape, pymunk.Segment):
        seg_path = QPainterPath()
        seg_path.moveTo(shape.a.x, shape.a.y)
        seg_path.lineTo(shape.b.x, shape.b.y)
        stroker = QPainterPathStroker()
        stroker.setWidth(shape.radius * 2)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        path = stroker.createStroke(seg_path)
    elif isinstance(shape, pymunk.Poly):
        vs = shape.get_vertices()
        path.moveTo(vs[0].x, vs[0].y)
        for v in vs[1:]:
            path.lineTo(v.x, v.y)
        path.closeSubpath()
    else:
        return

    pix, off = bake_neon_texture(path, color_rgb, blur_radius)
    shape._neon_pixmap = pix
    shape._neon_offset = off
    shape._core_path = path
    shape._color = color_rgb


# ==========================================
# UI 界面类
# ==========================================
class TrackSegmentRow(QFrame):
    def __init__(self, name, key, delete_cb):
        super().__init__()
        self.key = key
        self.setStyleSheet("background: rgba(255,255,255,0.08); border-radius: 4px; margin-bottom: 2px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)
        lbl = QLabel(name)
        lbl.setStyleSheet("color: #0ff; font-weight: bold;")
        layout.addWidget(lbl)
        
        btn_del = QPushButton("❌")
        btn_del.setFixedSize(24, 24)
        btn_del.setStyleSheet("background: transparent; color: #ff5555; border: none;")
        btn_del.clicked.connect(lambda: delete_cb(self))
        layout.addWidget(btn_del)

class BallConfigRow(QFrame):
    def __init__(self, index, default_color):
        super().__init__()
        self.color = QColor(default_color)
        self.skin_path = None
        self.music_path = None
        
        self.setStyleSheet(f"""
            BallConfigRow {{ background: rgba(255,255,255,0.05); border-left: 3px solid {default_color}; border-radius: 8px; margin-bottom: 5px; }}
            QLabel {{ color: #aaa; font-size: 12px; }}
            QLineEdit {{ background: #111; color: #fff; border: 1px solid #555; border-radius: 4px; padding: 4px; }}
            QPushButton {{ background: #111; color: #0ff; border: 1px solid #0ff; padding: 5px; border-radius: 4px; }}
            QPushButton:hover {{ background: #0ff; color: #000; }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(24, 24)
        self.btn_color.setStyleSheet(f"background-color: {default_color}; border: none; border-radius: 12px;")
        self.btn_color.clicked.connect(self.choose_color)
        layout.addWidget(self.btn_color)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText(f"Ball {index + 1}")
        self.txt_name.setFixedWidth(70)
        layout.addWidget(self.txt_name)

        self.btn_skin = QPushButton("🎨 Skin")
        self.btn_skin.clicked.connect(self.choose_skin)
        layout.addWidget(self.btn_skin)

        self.btn_music = QPushButton("🎵 BGM")
        self.btn_music.clicked.connect(self.choose_music)
        layout.addWidget(self.btn_music)

    def choose_color(self):
        color = QColorDialog.getColor(self.color, self, "Choose Color")
        if color.isValid():
            self.color = color
            self.btn_color.setStyleSheet(f"background-color: {color.name()}; border: none; border-radius: 12px;")

    def choose_skin(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Skin", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.skin_path = path
            self.btn_skin.setText("🎨 \u2713") 

    def choose_music(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Music", "", "Audio (*.mp3 *.wav *.ogg)")
        if path:
            self.music_path = path
            self.btn_music.setText("🎵 \u2713")

class SetupUI(QWidget):
    def __init__(self, start_callback):
        super().__init__()
        self.start_callback = start_callback
        self.track_color_start = QColor('#00ffff') 
        self.track_color_end = QColor('#ff00ff')   
        
        self.segment_options = {
            "Sector Portals": "sector_portal", 
            "Plinko Funnel": "plinko",
            "Rotating Split Rings": "c_rings",
            "Pulsing Balls Array": "pulsing",
            "Baffle Maze": "baffle",
            "Spinners Grid": "spinners",
            "Replica Gear Chamber": "replica_gears",
            "Fast Drop": "fast_drop"
        }
        
        self.active_segments = []
        self.ball_rows = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        container = QWidget()
        container.setFixedWidth(460) 
        container.setStyleSheet("QWidget { background: rgba(10, 10, 15, 0.95); border-radius: 15px; } QLabel { color: #fff; font-family: 'Segoe UI'; }")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("NEON MARBLE RACE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #0ff; font-size: 28px; font-weight: bold; letter-spacing: 2px;")
        c_layout.addWidget(title)

        top_opt_layout = QHBoxLayout()
        top_opt_layout.addWidget(QLabel("Colors: Start"))
        self.btn_c1 = QPushButton()
        self.btn_c1.setFixedSize(20, 20)
        self.btn_c1.setStyleSheet(f"background: {self.track_color_start.name()}; border-radius: 4px;")
        self.btn_c1.clicked.connect(lambda: self.pick_track_color('start'))
        top_opt_layout.addWidget(self.btn_c1)
        
        top_opt_layout.addWidget(QLabel("End"))
        self.btn_c2 = QPushButton()
        self.btn_c2.setFixedSize(20, 20)
        self.btn_c2.setStyleSheet(f"background: {self.track_color_end.name()}; border-radius: 4px;")
        self.btn_c2.clicked.connect(lambda: self.pick_track_color('end'))
        top_opt_layout.addWidget(self.btn_c2)
        
        top_opt_layout.addStretch()
        top_opt_layout.addWidget(QLabel("Balls:"))
        self.sp_count = QSpinBox()
        self.sp_count.setRange(2, 12)
        self.sp_count.setValue(6)
        self.sp_count.setStyleSheet("background: #111; color: #0ff; border: 1px solid #0ff; padding: 2px;")
        self.sp_count.valueChanged.connect(self.update_balls)
        top_opt_layout.addWidget(self.sp_count)
        c_layout.addLayout(top_opt_layout)

        builder_header = QHBoxLayout()
        builder_header.addWidget(QLabel("Track Builder Sequence:"))
        btn_random = QPushButton("🎲 Randomize")
        btn_random.setStyleSheet("background: #5500aa; color: #fff; font-weight:bold; border-radius: 4px; padding: 4px 8px;")
        btn_random.clicked.connect(self.randomize_track)
        builder_header.addWidget(btn_random)
        c_layout.addLayout(builder_header)
        
        track_builder_area = QFrame()
        track_builder_area.setStyleSheet("background: rgba(0,0,0,0.5); border-radius: 8px;")
        tb_layout = QVBoxLayout(track_builder_area)
        
        self.track_list_container = QWidget()
        self.track_list_container.setStyleSheet("background: transparent;")
        self.track_list_layout = QVBoxLayout(self.track_list_container)
        self.track_list_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.addWidget(self.track_list_container)
        
        add_seg_layout = QHBoxLayout()
        self.cb_segments = QComboBox()
        self.cb_segments.addItems(list(self.segment_options.keys()))
        self.cb_segments.setStyleSheet("background: #111; color: #0ff; border: 1px solid #0ff; padding: 4px;")
        add_seg_layout.addWidget(self.cb_segments)
        
        btn_add_seg = QPushButton("➕ Add")
        btn_add_seg.setStyleSheet("background: #004444; color: #0ff; border: 1px solid #0ff; padding: 4px; border-radius: 4px;")
        btn_add_seg.clicked.connect(self.add_segment)
        add_seg_layout.addWidget(btn_add_seg)
        tb_layout.addLayout(add_seg_layout)
        
        c_layout.addWidget(track_builder_area)
        
        for name in ["Sector Portals", "Rotating Split Rings", "Plinko Funnel", "Pulsing Balls Array", "Fast Drop"]:
            self.add_segment_row(name, self.segment_options[name])

        c_layout.addWidget(QLabel("Racers:"))
        self.balls_area = QScrollArea()
        self.balls_area.setWidgetResizable(True)
        self.balls_area.setFixedHeight(180)
        self.balls_area.setStyleSheet("background: transparent; border: none;")
        self.balls_container = QWidget()
        self.balls_container.setStyleSheet("background: transparent;")
        self.balls_layout = QVBoxLayout(self.balls_container)
        self.balls_layout.setContentsMargins(0,0,0,0)
        self.balls_area.setWidget(self.balls_container)
        c_layout.addWidget(self.balls_area)

        self.btn_start = QPushButton("START RACE")
        self.btn_start.setFixedHeight(50)
        self.btn_start.setStyleSheet("QPushButton { background: #003333; color: #0ff; font-size: 20px; font-weight: bold; border: 2px solid #0ff; border-radius: 8px;} QPushButton:hover { background: #00ffff; color: #000; }")
        self.btn_start.clicked.connect(self.on_start)
        c_layout.addWidget(self.btn_start)

        author_info = QLabel('Author<a href="https://space.bilibili.com/6297797" style="color:#4d94ff; text-decoration:none;">@依然匹萨吧</a><br><span style="font-size:12px; color:#aaa;">本软件免费，禁止商用贩卖</span>')
        author_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_info.setOpenExternalLinks(True)
        author_info.setStyleSheet("color: #fff;")
        c_layout.addWidget(author_info)
        
        layout.addWidget(container)
        self.update_balls()

    def add_segment(self):
        name = self.cb_segments.currentText()
        key = self.segment_options[name]
        self.add_segment_row(name, key)
        
    def add_segment_row(self, name, key):
        row = TrackSegmentRow(name, key, self.remove_segment)
        self.active_segments.append(row) 
        self.track_list_layout.addWidget(row)
        
    def remove_segment(self, row_widget):
        if row_widget in self.active_segments:
            self.active_segments.remove(row_widget)
        self.track_list_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        
    def randomize_track(self):
        for row in self.active_segments:
            self.track_list_layout.removeWidget(row)
            row.deleteLater()
        self.active_segments.clear()
        
        num_segments = random.randint(4, 7)
        keys = list(self.segment_options.keys())
        for _ in range(num_segments):
            name = random.choice(keys)
            self.add_segment_row(name, self.segment_options[name])

    def pick_track_color(self, type_):
        curr = self.track_color_start if type_ == 'start' else self.track_color_end
        color = QColorDialog.getColor(curr, self, "Pick Track Color")
        if color.isValid():
            if type_ == 'start':
                self.track_color_start = color
                self.btn_c1.setStyleSheet(f"background: {color.name()}; border-radius: 4px;")
            else:
                self.track_color_end = color
                self.btn_c2.setStyleSheet(f"background: {color.name()}; border-radius: 4px;")

    def update_balls(self):
        cnt = self.sp_count.value()
        while len(self.ball_rows) < cnt:
            row = BallConfigRow(len(self.ball_rows), DEFAULT_COLORS[len(self.ball_rows) % len(DEFAULT_COLORS)])
            self.ball_rows.append(row)
            self.balls_layout.addWidget(row)
        while len(self.ball_rows) > cnt:
            row = self.ball_rows.pop()
            self.balls_layout.removeWidget(row)
            row.deleteLater()

    def on_start(self):
        track_sequence = [row.key for row in self.active_segments]
        if not track_sequence: track_sequence = ["sector_portal"] 
            
        config = {
            'segments': track_sequence,
            'balls': [],
            'obs_start_rgb': hex_to_rgb(self.track_color_start.name()),
            'obs_end_rgb': hex_to_rgb(self.track_color_end.name())
        }
        for i, row in enumerate(self.ball_rows):
            name = row.txt_name.text().strip() or f"Ball {i+1}"
            config['balls'].append({
                'id': i, 'name': name,
                'color': row.color, 'rgb': hex_to_rgb(row.color.name()),
                'skin': row.skin_path, 'music': row.music_path
            })
        self.start_callback(config)


# ==========================================
# 游戏引擎与动态赛道生成器
# ==========================================
class GameEngineWidget(QWidget):
    def __init__(self, go_home_callback):
        super().__init__()
        self.go_home_callback = go_home_callback
        
        self.btn_home = QPushButton("🏠", self)
        self.btn_restart = QPushButton("🔄", self)
        btn_style = "QPushButton { background: rgba(0, 30, 30, 180); color: #0ff; border: 2px solid #0ff; border-radius: 20px; font-size: 18px; } QPushButton:hover { background: #0ff; color: #000; }"
        for btn in [self.btn_home, self.btn_restart]:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(btn_style)
        self.btn_home.clicked.connect(self.on_home)
        self.btn_restart.clicked.connect(self.on_restart)

        self.my_balls = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_physics_and_render)
        self._buffer = None
        self.cleanup(first_init=True)

    def resizeEvent(self, event):
        self.btn_home.move(self.width() - 55, 15)
        self.btn_restart.move(self.width() - 105, 15)
        super().resizeEvent(event)

    def cleanup(self, first_init=False):
        if not first_init:
            self.timer.stop()
            for b in self.my_balls:
                if b.get('player'):
                    b['player'].stop()
                    b['player'].deleteLater()
                if b.get('audio_out'): b['audio_out'].deleteLater()
                if b.get('peak_thread'):
                    b['peak_thread'].stop()
                    b['peak_thread'].deleteLater()
            
        self.my_balls.clear()
        self.ripples = []
        self.leader = None
        self.first_finisher = None
        
        self.pulsing_obs = [] 
        self.moving_obs = [] 
        self.c_rings = [] 
        self.gear_spinners = []
        self.sector_spinners = []   
        self.teleport_zones = []    
        self.bg_dots = []
        self.flippers = [] # 追踪动态挡板

        self.pending_segments = []
        self.current_build_y = 600
        self.estimated_total_y = 20000 
        self.track_end_y = 9999999 
        self.finish_built = False
        
        self.time_offset = 0
        self.ripple_timer = 0
        
        self.game_state = "COUNTDOWN"
        self.countdown_ticks = 180 

        self.space = pymunk.Space()
        self.space.gravity = (0, 1100)
        self.space.damping = 0.99
        self.ring_body = None
        self.ring_shapes = []

    def start_game(self, config):
        self.config = config
        self.init_world()
        self.timer.start(1000 // 60)

    def on_restart(self):
        self.cleanup()
        self.start_game(self.config)

    def on_home(self):
        self.cleanup()
        self.go_home_callback()

    def get_obs_color(self, y):
        t = max(0.0, min(1.0, y / self.estimated_total_y))
        return lerp_color(self.config['obs_start_rgb'], self.config['obs_end_rgb'], t)

    def get_inverse_color(self, y):
        r, g, b = self.get_obs_color(y)
        return (255 - r, 255 - g, 255 - b)

    def _create_rounded_rect_shape(self, body, w, h, r=5):
        safe_r = min(r, w/2.0 - 0.5, h/2.0 - 0.5)
        shape = pymunk.Poly.create_box(body, (w - 2*safe_r, h - 2*safe_r), radius=safe_r)
        shape._is_rect = True
        shape._w, shape._h, shape._corner_radius = w, h, safe_r
        return shape

    # ================= 赛道积木 =================
    def add_wall(self, x, y, w, h):
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (x, y)
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.elasticity, shape.friction = 0.4, 0.0
        self.space.add(body, shape)

    def add_rect_obs(self, x, y, w, h, angle=0.0, bounce=0.6, color_rgb=None, friction=0.1):
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (x, y)
        body.angle = angle
        shape = self._create_rounded_rect_shape(body, w, h, r=8)
        shape.elasticity, shape.friction = bounce, friction
        self.space.add(body, shape)
        attach_neon_cache(shape, color_rgb or self.get_obs_color(y), blur_radius=22)

    def add_poly_obs(self, points, bounce=0.6, color_rgb=None, radius=8, friction=0.1):
        cx = sum(px for px, _ in points) / len(points)
        cy = sum(py for _, py in points) / len(points)
        local_points = [(px - cx, py - cy) for px, py in points]
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (cx, cy)
        shape = pymunk.Poly(body, local_points, radius=radius)
        shape.elasticity, shape.friction = bounce, friction
        self.space.add(body, shape)
        path = QPainterPath()
        path.moveTo(local_points[0][0], local_points[0][1])
        for px, py in local_points[1:]:
            path.lineTo(px, py)
        path.closeSubpath()
        attach_neon_cache(shape, color_rgb or self.get_obs_color(cy), blur_radius=22, path_override=path)

    def add_segment_obs(self, x1, y1, x2, y2, thickness=20, bounce=0.6, color_rgb=None, friction=0.1):
        mx = (x1 + x2) / 2.0
        my = (y1 + y2) / 2.0
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (mx, my)
        shape = pymunk.Segment(body, (x1 - mx, y1 - my), (x2 - mx, y2 - my), thickness / 2.0)
        shape.elasticity, shape.friction = bounce, friction
        self.space.add(body, shape)
        attach_neon_cache(shape, color_rgb or self.get_obs_color(my), blur_radius=22)

    def add_arc_obs(self, cx, cy, r, start_deg, end_deg, thickness=20, bounce=0.6, color_rgb=None, segments=14, friction=0.1):
        pts = []
        for i in range(segments + 1):
            t = i / segments
            ang = math.radians(start_deg + (end_deg - start_deg) * t)
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            self.add_segment_obs(x1, y1, x2, y2, thickness=thickness, bounce=bounce, color_rgb=color_rgb, friction=friction)

    def add_moving_circle_obs(self, x, y, r, amplitude=30, speed=0.04, phase=0):
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = (x, y)
        shape = pymunk.Circle(body, r)
        shape.elasticity, shape.friction = 0.6, 0.1
        self.space.add(body, shape)
        attach_neon_cache(shape, self.get_obs_color(y), blur_radius=22)
        self.moving_obs.append({
            'body': body, 'shape': shape, 'base_x': x,
            'amplitude': amplitude, 'speed': speed, 'phase': phase
        })

    def add_spinner(self, x, y, size, direction=None):
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = (x, y)
        sh1 = self._create_rounded_rect_shape(body, size, 40, r=5)
        sh2 = self._create_rounded_rect_shape(body, 40, size, r=5)
        sh1.elasticity = sh2.elasticity = 0.8
        self.space.add(body, sh1, sh2)
        attach_neon_cache(sh1, self.get_obs_color(y), blur_radius=22)
        attach_neon_cache(sh2, self.get_obs_color(y), blur_radius=22)
        if direction is None: direction = 1 if random.random() > 0.5 else -1
        body.angular_velocity = direction * 2.5

    def add_gear_spinner(self, x, y, core_r, tooth_inner_r, tooth_outer_r, tooth_width, direction,
                         speed=1.55, teeth=8, color_rgb=None, bounce=0.78, angle_offset_deg=0, friction=0.1):
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = (x, y)
        body.angle = math.radians(angle_offset_deg)
        body.angular_velocity = direction * speed
        self.space.add(body)
        shapes = []
        core_shape = pymunk.Circle(body, core_r)
        core_shape.elasticity, core_shape.friction = bounce, friction
        self.space.add(core_shape)
        shapes.append(core_shape)
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), core_r, core_r)
        stroker = QPainterPathStroker()
        stroker.setWidth(tooth_width)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        for i in range(teeth):
            ang = i * (2 * math.pi / teeth)
            ax, ay = math.cos(ang) * tooth_inner_r, math.sin(ang) * tooth_inner_r
            bx, by = math.cos(ang) * tooth_outer_r, math.sin(ang) * tooth_outer_r
            tooth_shape = pymunk.Segment(body, (ax, ay), (bx, by), tooth_width / 2.0)
            tooth_shape.elasticity, tooth_shape.friction = bounce, friction
            self.space.add(tooth_shape)
            shapes.append(tooth_shape)
            tooth_path = QPainterPath()
            tooth_path.moveTo(ax, ay)
            tooth_path.lineTo(bx, by)
            path.addPath(stroker.createStroke(tooth_path))
        color = color_rgb or self.get_obs_color(y)
        pixmap, offset = bake_neon_texture(path, color, blur_radius=22)
        self.gear_spinners.append({
            'body': body, 'shapes': shapes, 'pixmap': pixmap, 'offset': offset,
            'core_path': path, 'color': color
        })
        
    def add_pulsing_circle(self, x, y, min_r, max_r, phase):
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = (x, y)
        shape = pymunk.Circle(body, max_r)
        shape.elasticity, shape.friction = 0.5, 0.1
        shape._is_pulsing = True 
        self.space.add(body, shape)
        color_rgb = self.get_obs_color(y)
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), max_r, max_r)
        pixmap, offset = bake_neon_texture(path, color_rgb, blur_radius=22)
        self.pulsing_obs.append({
            'body': body, 'shape': shape, 'min_r': min_r, 'max_r': max_r,
            'current_r': max_r, 'phase': phase, 'color': color_rgb,
            'pixmap': pixmap, 'offset': offset, 'core_path': path
        })
        
    def add_split_ring(self, x, y, r, speed, gap_angle_deg=34, thickness=4):
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = (x, y)
        body.angular_velocity = speed
        body.angle = random.uniform(0, math.pi * 2) 
        self.space.add(body)
        path = QPainterPath()
        physics_shapes = []
        half_gap = gap_angle_deg / 2.0
        arcs = [(half_gap, 180 - half_gap), (180 + half_gap, 360 - half_gap)]
        segments_per_arc = 18
        for start_deg, end_deg in arcs:
            for i in range(segments_per_arc):
                a1 = math.radians(start_deg + i * (end_deg - start_deg) / segments_per_arc)
                a2 = math.radians(start_deg + (i + 1) * (end_deg - start_deg) / segments_per_arc)
                px, py = math.cos(a1) * r, math.sin(a1) * r
                nx, ny = math.cos(a2) * r, math.sin(a2) * r
                if i == 0: path.moveTo(px, py)
                path.lineTo(nx, ny)
                seg = pymunk.Segment(body, (px, py), (nx, ny), thickness)
                seg.elasticity, seg.friction = 0.2, 0.1
                self.space.add(seg)
                physics_shapes.append(seg)
        stroker = QPainterPathStroker()
        stroker.setWidth(thickness * 2)
        stroker.setCapStyle(Qt.PenCapStyle.FlatCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        thick_path = stroker.createStroke(path)
        color_rgb = self.get_obs_color(y)
        pixmap, offset = bake_neon_texture(thick_path, color_rgb, blur_radius=22)
        self.c_rings.append({
            'body': body, 'shapes': physics_shapes, 'pixmap': pixmap,
            'offset': offset, 'core_path': thick_path, 'color': color_rgb
        })

    def _generate_sector_points(self, radius, start_deg, end_deg, steps=6):
        pts = [(0, 0)]
        for i in range(steps + 1):
            ang = math.radians(start_deg + i * (end_deg - start_deg) / steps)
            pts.append((math.cos(ang) * radius, math.sin(ang) * radius))
        return pts

    def add_sector_spinner(self, x, y, radius, speed, span_deg=90):
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = (x, y)
        body.angular_velocity = speed 
        self.space.add(body)

        half_span = span_deg / 2.0
        pts1 = self._generate_sector_points(radius, -half_span, half_span)
        pts2 = self._generate_sector_points(radius, 180 - half_span, 180 + half_span)

        sh1 = pymunk.Poly(body, pts1)
        sh2 = pymunk.Poly(body, pts2)
        sh1.elasticity = sh2.elasticity = 0.5
        sh1.friction = sh2.friction = 0.1
        self.space.add(sh1, sh2)

        path = QPainterPath()
        path.moveTo(0, 0)
        for p in pts1[1:]: path.lineTo(p[0], p[1])
        path.closeSubpath()
        path.moveTo(0, 0)
        for p in pts2[1:]: path.lineTo(p[0], p[1])
        path.closeSubpath()

        color_rgb = self.get_obs_color(y)
        pixmap, offset = bake_neon_texture(path, color_rgb, blur_radius=22)

        self.sector_spinners.append({
            'body': body,
            'shapes': [sh1, sh2],
            'pixmap': pixmap,
            'offset': offset,
            'core_path': path,
            'color': color_rgb
        })

    def add_pinball_flipper(self, x, y, width, height, side, color_rgb):
        mass = 8.0
        moment = pymunk.moment_for_box(mass, (width, height))
        body = pymunk.Body(mass, moment)
        body.position = (x, y)
        
        # 旋转角度设定（正右为0度，顺时针为正）
        if side == 'left':
            rest_angle = math.pi / 7   # 静止时下垂
            up_angle = -math.pi / 5    # 弹起时上翘
            r = 10
            # 顶点相对于锚点(0,0)靠右
            safe_v = [(r, -height/2+r), (width-r, -height/2+r), (width-r, height/2-r), (r, height/2-r)]
        else:
            rest_angle = -math.pi / 7  # 右侧相反
            up_angle = math.pi / 5     
            r = 10
            # 顶点相对于锚点(0,0)靠左
            safe_v = [(-width+r, -height/2+r), (-r, -height/2+r), (-r, height/2-r), (-width+r, height/2-r)]

        body.angle = rest_angle
        
        shape = pymunk.Poly(body, safe_v, radius=r)
        shape.elasticity = 0.6
        shape.friction = 0.2
        shape.collision_type = 2 # 分配编号2为Flipper(挡板)
        self.space.add(body, shape)

        static_body = self.space.static_body
        
        # 1. 铰链：固定挡板的旋转轴
        pivot = pymunk.PivotJoint(static_body, body, (x, y))
        self.space.add(pivot)

        # 2. 角度限制器：不让挡板360度乱转
        if side == 'left':
            limit = pymunk.RotaryLimitJoint(static_body, body, up_angle, rest_angle)
        else:
            limit = pymunk.RotaryLimitJoint(static_body, body, rest_angle, up_angle)
        self.space.add(limit)

        # 3. 扭转弹簧：让挡板拍打后能自动回弹复位
        spring = pymunk.DampedRotarySpring(static_body, body, rest_angle, 1.5e6, 30000)
        self.space.add(spring)

        # 附加渲染特效
        path = QPainterPath()
        if side == 'left':
            path.addRoundedRect(0, -height/2, width, height, r, r)
        else:
            path.addRoundedRect(-width, -height/2, width, height, r, r)
            
        attach_neon_cache(shape, color_rgb, blur_radius=22, path_override=path)
        
        self.flippers.append({
            'body': body,
            'shape': shape,
            'joints': [pivot, limit, spring]
        })

    def flipper_hit(self, arbiter, space, data):
        """当小球触碰挡板时触发，给挡板极大的旋转角速度向上抬起"""
        flipper_body = arbiter.shapes[1].body
        # 通过X坐标判断是左挡板还是右挡板，施加不同方向的旋转角速度
        if flipper_body.position.x < TRACK_WIDTH / 2:
            flipper_body.angular_velocity = -18.0 
        else:
            flipper_body.angular_velocity = 18.0
        return True


    # ================= 赛段组合生成 =================
    
    def seg_c_rings(self, start_y):
        y = start_y + 150
        r_path, thickness = 150, 2
        R_in, R_out = r_path - thickness, r_path + thickness
        x_left, x_right = R_in, TRACK_WIDTH - R_in
        dy = math.sqrt((2 * R_out)**2 - (x_right - x_left)**2)
        for i in range(6):
            if i % 2 == 0: x, speed = x_left, 1.6
            else: x, speed = x_right, -1.6
            self.add_split_ring(x, y, r=r_path, speed=speed, gap_angle_deg=34, thickness=thickness)
            y += dy 
        return y + 150

    def seg_plinko_funnel(self, start_y):
        y = start_y
        for i in range(6):
            cols = 5
            spacing = (436 - 84) / 4 
            offset_x = 84
            phase_offset = 0 if i % 2 == 0 else math.pi 
            for j in range(cols):
                px = offset_x + j * spacing
                self.add_moving_circle_obs(px, y, 14, amplitude=30, speed=0.04, phase=phase_offset)
            y += 120
            
        # 底部更换为动态弹球挡板，左右靠边，宽度210，留出极大的间隙
        color = self.get_obs_color(y+80)
        self.add_pinball_flipper(10, y+80, 210, 36, 'left', color)
        self.add_pinball_flipper(TRACK_WIDTH - 10, y+80, 210, 36, 'right', color)
        return y + 300

    def seg_baffle_maze(self, start_y):
        y = start_y
        for i in range(4):
            if i % 2 == 0: self.add_rect_obs(140, y, 400, 40, angle=math.pi/8, bounce=0.4)
            else: self.add_rect_obs(TRACK_WIDTH - 140, y, 400, 40, angle=-math.pi/8, bounce=0.4)
            y += 240
        return y + 100

    def seg_spinners(self, start_y):
        y = start_y + 120
        size = 180
        for i in range(5): 
            if i % 2 == 0:
                self.add_spinner(0, y, size, direction=-1)
                self.add_spinner(TRACK_WIDTH, y, size, direction=1)
            else:
                self.add_spinner(150, y, size, direction=1)
                self.add_spinner(TRACK_WIDTH - 150, y, size, direction=-1)
            y += 220 
        return y + 100

    def seg_replica_gear_chamber(self, start_y):
        y = start_y + 20
        strong_bounce_rgb, strong_bounce, rail_bounce = (0, 255, 40), 1.28, 0.22
        self.add_poly_obs([(-82, y + 178), (-82, y + 506), (360, y + 408), (310, y + 266)], bounce=rail_bounce)
        self.add_segment_obs(446, y + 228, TRACK_WIDTH + 34, y + 190, thickness=54, bounce=rail_bounce)
        self.add_rect_obs(522, y + 408, 24, 294, bounce=strong_bounce, color_rgb=strong_bounce_rgb)
        self.add_segment_obs(308, y + 624, 492, y + 674, thickness=28, bounce=strong_bounce, color_rgb=strong_bounce_rgb)
        self.add_segment_obs(504, y + 560, 468, y + 650, thickness=24, bounce=strong_bounce, color_rgb=strong_bounce_rgb)
        self.add_arc_obs(86, y + 676, 156, 108, 290, thickness=30, bounce=rail_bounce)
        self.add_segment_obs(108, y + 676, 430, y + 650, thickness=38, bounce=rail_bounce)
        self.add_segment_obs(102, y + 820, 332, y + 848, thickness=40, bounce=rail_bounce)
        self.add_segment_obs(-18, y + 968, 84, y + 988, thickness=34, bounce=rail_bounce)
        self.add_gear_spinner(394, y + 390, core_r=44, tooth_inner_r=30, tooth_outer_r=86, tooth_width=28,
                              direction=1, speed=1.42, bounce=0.5, angle_offset_deg=6)
        self.add_gear_spinner(94, y + 678, core_r=42, tooth_inner_r=28, tooth_outer_r=82, tooth_width=26,
                              direction=-1, speed=1.36, bounce=0.5, angle_offset_deg=8)
        self.add_gear_spinner(406, y + 888, core_r=40, tooth_inner_r=26, tooth_outer_r=80, tooth_width=26,
                              direction=1, speed=1.48, bounce=0.5, angle_offset_deg=-8)
        return y + 1030

    def seg_fast_drop(self, start_y):
        height = 2500
        y = start_y
        for py in range(int(y), int(y + height), 60):
            for px in range(30, TRACK_WIDTH, 60):
                if random.random() > 0.3:
                    self.bg_dots.append((px, py))
        self.add_rect_obs(30, y + 500, 350, 20, angle=math.pi/3, bounce=0.2)
        self.add_rect_obs(TRACK_WIDTH-30, y + 1500, 350, 20, angle=-math.pi/3, bounce=0.2)
        end_y = y + height
        self.add_rect_obs(50, end_y, 350, 40, angle=math.pi/7)
        self.add_rect_obs(TRACK_WIDTH-50, end_y, 350, 40, angle=-math.pi/7)
        return end_y + 200
        
    def seg_pulsing_balls(self, start_y):
        y = start_y + 150
        self.add_pulsing_circle(0, y, min_r=70, max_r=125, phase=0)
        self.add_pulsing_circle(270, y, min_r=70, max_r=125, phase=0)
        self.add_pulsing_circle(540, y, min_r=70, max_r=125, phase=0)
        y += 250
        self.add_pulsing_circle(170, y, min_r=60, max_r=110, phase=math.pi)
        self.add_pulsing_circle(370, y, min_r=60, max_r=110, phase=math.pi)
        y += 250
        self.add_pulsing_circle(0, y, min_r=70, max_r=125, phase=0)
        self.add_pulsing_circle(270, y, min_r=70, max_r=125, phase=0)
        self.add_pulsing_circle(540, y, min_r=70, max_r=125, phase=0)
        y += 250
        self.add_pulsing_circle(170, y, min_r=60, max_r=110, phase=math.pi)
        self.add_pulsing_circle(370, y, min_r=60, max_r=110, phase=math.pi)
        return y + 250

    def seg_sector_portal(self, start_y):
        y = start_y + 120
        rows = 4  
        row_spacing = 220
        direction = random.choice(['left', 'right'])
        R = 100 
        
        if direction == 'right':
            c1_x = R               
            c2_x = 3 * R           
            teleport_side = 'right'
            threshold = TRACK_WIDTH - 30 
            speed = 1.8            
        else:
            c1_x = TRACK_WIDTH - 3 * R 
            c2_x = TRACK_WIDTH - R     
            teleport_side = 'left'
            threshold = 30
            speed = -1.8           
            
        for i in range(rows):
            current_y = y + i * row_spacing
            self.add_sector_spinner(c1_x, current_y, radius=R, speed=speed, span_deg=90)
            self.add_sector_spinner(c2_x, current_y, radius=R, speed=speed, span_deg=90)

        end_y = y + (rows - 1) * row_spacing + 150
        self.teleport_zones.append({
            'start_y': start_y, 
            'end_y': end_y, 
            'respawn_y': start_y - 80, 
            'side': teleport_side,
            'threshold': threshold
        })
        return end_y + 150


    # ================= 动态加载核心逻辑 =================
    
    def build_next_segment(self):
        if not self.pending_segments:
            if not self.finish_built:
                plat_y = self.current_build_y + 350
                self.track_end_y = plat_y - 150 
                
                plat_body = pymunk.Body(body_type=pymunk.Body.STATIC)
                plat_body.position = (TRACK_WIDTH/2, plat_y)
                plat_shape = self._create_rounded_rect_shape(plat_body, TRACK_WIDTH, 150, r=10)
                plat_shape.elasticity = 0.2
                self.space.add(plat_body, plat_shape)
                attach_neon_cache(plat_shape, self.config['obs_end_rgb'], blur_radius=22)
                
                self.add_wall(-20, plat_y, 40, 1000)
                self.add_wall(TRACK_WIDTH + 20, plat_y, 40, 1000)
                
                self.finish_built = True
            return

        seg_name = self.pending_segments.pop(0)
        old_y = self.current_build_y

        if seg_name == 'plinko': new_y = self.seg_plinko_funnel(old_y)
        elif seg_name == 'baffle': new_y = self.seg_baffle_maze(old_y)
        elif seg_name == 'spinners': new_y = self.seg_spinners(old_y)
        elif seg_name == 'replica_gears': new_y = self.seg_replica_gear_chamber(old_y)
        elif seg_name == 'c_rings': new_y = self.seg_c_rings(old_y)
        elif seg_name == 'pulsing': new_y = self.seg_pulsing_balls(old_y)
        elif seg_name == 'fast_drop': new_y = self.seg_fast_drop(old_y)
        elif seg_name == 'sector_portal': new_y = self.seg_sector_portal(old_y)
        else: new_y = old_y + 500
        
        new_y += 150
        
        chunk_height = new_y - old_y + 200 
        mid_y = (old_y + new_y) / 2.0
        self.add_wall(-20, mid_y, 40, chunk_height)
        self.add_wall(TRACK_WIDTH + 20, mid_y, 40, chunk_height)

        self.current_build_y = new_y

    def init_world(self):
        expected = 600
        for seg in self.config['segments']:
            if seg == 'plinko': expected += 1020
            elif seg == 'baffle': expected += 1060
            elif seg == 'spinners': expected += 1320 
            elif seg == 'replica_gears': expected += 1120
            elif seg == 'c_rings': expected += 1300
            elif seg == 'fast_drop': expected += 2700
            elif seg == 'pulsing': expected += 1100
            elif seg == 'sector_portal': expected += 1100 
            expected += 150 
        self.estimated_total_y = expected + 500

        self.pending_segments = list(self.config['segments'])
        self.current_build_y = 600
        self.finish_built = False
        
        self.add_wall(-20, 0, 40, 1500) 
        self.add_wall(TRACK_WIDTH + 20, 0, 40, 1500)

        # 注册小球（类型1）和动态挡板（类型2）的碰撞回调
        handler = self.space.add_collision_handler(1, 2)
        handler.begin = self.flipper_hit

        self.ring_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.ring_body.position = (TRACK_WIDTH/2, 250)
        self.ring_body.angular_velocity = random.uniform(5, 8)  # 加快转速，体现滚筒感
        self.space.add(self.ring_body)
        
        r_out, r_in = 160, 60
        segments_count = 24
        # 1. 建立内外圆环
        for i in range(segments_count):
            ang1 = i * (2 * math.pi / segments_count)
            ang2 = (i + 1) * (2 * math.pi / segments_count)
            p1 = (math.cos(ang1)*r_out, math.sin(ang1)*r_out)
            p2 = (math.cos(ang2)*r_out, math.sin(ang2)*r_out)
            seg_out = pymunk.Segment(self.ring_body, p1, p2, 10)
            seg_out.elasticity = 0.5
            self.ring_shapes.append(seg_out)
            self.space.add(seg_out)
            
            p3 = (math.cos(ang1)*r_in, math.sin(ang1)*r_in)
            p4 = (math.cos(ang2)*r_in, math.sin(ang2)*r_in)
            seg_in = pymunk.Segment(self.ring_body, p3, p4, 10)
            seg_in.elasticity = 0.5
            self.ring_shapes.append(seg_in)
            self.space.add(seg_in)

        # 2. 添加 12 个内部隔板(Baffles)，使其变成洗衣机/抽奖滚筒结构
        baffles_count = 12
        offset_angle = math.pi / baffles_count # 偏移半个舱室角度，防止小球直接生成在隔板内部发生物理爆炸
        for i in range(baffles_count):
            ang = i * (2 * math.pi / baffles_count) + offset_angle
            p_in = (math.cos(ang)*r_in, math.sin(ang)*r_in)
            p_out = (math.cos(ang)*r_out, math.sin(ang)*r_out)
            seg_baffle = pymunk.Segment(self.ring_body, p_in, p_out, 6)
            seg_baffle.elasticity = 0.4
            self.ring_shapes.append(seg_baffle)
            self.space.add(seg_baffle)

        num_balls = len(self.config['balls'])
        for i, data in enumerate(self.config['balls']):
            angle = i * (2 * math.pi / num_balls)
            r_mid = (r_out + r_in) / 2
            x = TRACK_WIDTH/2 + math.cos(angle) * r_mid
            y = 250 + math.sin(angle) * r_mid
            
            ball_radius = 26 
            body = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, ball_radius))
            body.position = (x, y)
            shape = pymunk.Circle(body, ball_radius)
            shape.elasticity = 0.85
            shape.friction = 0.05
            shape.collision_type = 1 # 分配编号1为小球
            self.space.add(body, shape)

            path = QPainterPath()
            path.addEllipse(QPointF(0, 0), ball_radius, ball_radius)
            pix, off = bake_neon_texture(path, data['rgb'], blur_radius=22)
            
            skin_brush = None
            if data['skin']:
                img = QImage(data['skin'])
                if not img.isNull():
                    scaled_img = img.scaled(ball_radius*2, ball_radius*2, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    pm = QPixmap.fromImage(scaled_img)
                    skin_brush = QBrush(pm)
                    skin_brush.setTransform(QTransform().translate(-ball_radius, -ball_radius))

            player, audio_out, peak_thread = None, None, None
            if data['music']:
                player = QMediaPlayer()
                audio_out = QAudioOutput()
                player.setAudioOutput(audio_out)
                player.setSource(QUrl.fromLocalFile(data['music']))
                player.setLoops(QMediaPlayer.Loops.Infinite)
                peak_thread = AudioPeakThread(data['music'])
                peak_thread.peak_detected.connect(lambda v, b_id=data['id']: self.trigger_beat_ripple(b_id, v))
                peak_thread.start()
            
            self.my_balls.append({
                'body': body, 'data': data, 'radius': ball_radius,
                'pixmap': pix, 'offset': off, 'path': path, 
                'skin_brush': skin_brush, 'player': player, 'audio_out': audio_out,
                'peak_thread': peak_thread, 'finished': False, 'finish_rank': -1,
                'history': []
            })

        self.build_next_segment()
        self.build_next_segment()

    def trigger_beat_ripple(self, ball_id, volume):
        # 拦截：如果还在倒计时阶段，不要生成随着音乐跳动的光圈
        if self.game_state != "RACING":
            return
            
        if self.leader and self.leader['data']['id'] == ball_id:
            self.ripples.append(0.0)

    def update_physics_and_render(self):
        self.time_offset += 1
        self.space.step(1.0 / 60.0)
        
        if self.my_balls and not self.finish_built:
            lowest_y = max(b['body'].position.y for b in self.my_balls)
            if lowest_y + 2000 > self.current_build_y:
                self.build_next_segment()
                
        for p in self.pulsing_obs:
            p['phase'] += 0.045 
            t = (math.sin(p['phase']) + 1) / 2
            current_r = p['min_r'] + (p['max_r'] - p['min_r']) * t
            self.space.remove(p['shape'])
            new_shape = pymunk.Circle(p['body'], current_r)
            new_shape.elasticity, new_shape.friction = 0.5, 0.1
            new_shape._is_pulsing = True 
            self.space.add(new_shape)
            p['shape'] = new_shape
            p['current_r'] = current_r
            
        for m in self.moving_obs:
            m['phase'] += m['speed']
            new_x = m['base_x'] + m['amplitude'] * math.sin(m['phase'])
            vx = (new_x - m['body'].position.x) * 60
            m['body'].velocity = (vx, 0)
            m['body'].position = (new_x, m['body'].position.y)

        if self.game_state == "RACING":
            for b in self.my_balls:
                bx, by = b['body'].position.x, b['body'].position.y
                for zone in self.teleport_zones:
                    if zone['start_y'] <= by <= zone['end_y']:
                        is_teleport = False
                        if zone['side'] == 'right' and bx >= zone['threshold']:
                            is_teleport = True
                        elif zone['side'] == 'left' and bx <= zone['threshold']:
                            is_teleport = True
                            
                        if is_teleport:
                            b['body'].position = (TRACK_WIDTH / 2.0 + random.uniform(-10, 10), zone['respawn_y'])
                            b['body'].velocity = (random.uniform(-50, 50), 200)
                            b['history'].clear() 

        if self.game_state == "COUNTDOWN":
            self.countdown_ticks -= 1
            cx, cy = TRACK_WIDTH / 2.0, 250
            
            for b in self.my_balls:
                # 倒计时期间：给小球施加人工离心力，强行让它们贴在滚筒外壁上
                bx, by = b['body'].position
                dx, dy = bx - cx, by - cy
                dist = math.hypot(dx, dy)
                if dist > 0.1:
                    force_mag = 1200 # 持续向外的离心力
                    b['body'].apply_force_at_local_point((dx/dist * force_mag, dy/dist * force_mag))
                
            if self.countdown_ticks <= 0:
                self.game_state = "RACING"
                self.space.remove(self.ring_body, *self.ring_shapes)
                self.ring_shapes.clear()
                
                for b in self.my_balls:
                    # 消除倒计时期间累积的连续受力
                    b['body'].force = (0, 0)
                    
                    # 计算小球当前的离心方向 (向外的径向)
                    bx, by = b['body'].position
                    dx, dy = bx - cx, by - cy
                    dist = math.hypot(dx, dy)
                    if dist > 0:
                        dx, dy = dx/dist, dy/dist
                    else:
                        dx, dy = 0, 1
                        
                    # 释放瞬间：物理引擎会自动保留小球当前的旋转切线速度
                    # 我们额外给一个温和的径向爆发推力，让它们呈烟花状散开，速度不要太大
                    push_out = random.uniform(150, 250)
                    b['body'].apply_impulse_at_local_point((dx * push_out, dy * push_out))
                    
                # 倒计时结束，正式开跑，如果此时已经选出了领先者，立即播放其音乐
                if self.leader and self.leader['player']:
                    self.leader['player'].setPosition(0)
                    self.leader['player'].play()

        for b in self.my_balls:
            b['history'].append((b['body'].position.x, b['body'].position.y))
            if len(b['history']) > 24:
                b['history'].pop(0)

        if self.time_offset % 60 == 0:
            highest_y = min((b['body'].position.y for b in self.my_balls), default=0)
            cutoff_y = highest_y - 3000
            
            shapes_to_rm, bodies_to_rm = [], []
            for b in self.space.bodies:
                if (b == self.ring_body or 
                    any(p['body'] == b for p in self.pulsing_obs) or 
                    any(m['body'] == b for m in self.moving_obs) or
                    any(c['body'] == b for c in self.c_rings) or
                    any(g['body'] == b for g in self.gear_spinners) or
                    any(s['body'] == b for s in self.sector_spinners) or
                    any(f['body'] == b for f in self.flippers)): # 防止动态挡板被误删
                    continue
                
                if (b.body_type in [pymunk.Body.STATIC, pymunk.Body.KINEMATIC]) and b.position.y < cutoff_y:
                    bodies_to_rm.append(b)
                    shapes_to_rm.extend(list(b.shapes))
            if shapes_to_rm:
                self.space.remove(*shapes_to_rm, *bodies_to_rm)
                
            active_pulsing = []
            for p in self.pulsing_obs:
                if p['body'].position.y < cutoff_y:
                    if p['shape'] in self.space.shapes: self.space.remove(p['shape'])
                    if p['body'] in self.space.bodies: self.space.remove(p['body'])
                else: active_pulsing.append(p)
            self.pulsing_obs = active_pulsing
            
            active_moving = []
            for m in self.moving_obs:
                if m['body'].position.y < cutoff_y:
                    if m['shape'] in self.space.shapes: self.space.remove(m['shape'])
                    if m['body'] in self.space.bodies: self.space.remove(m['body'])
                else: active_moving.append(m)
            self.moving_obs = active_moving
            
            active_c_rings = []
            for cr in self.c_rings:
                if cr['body'].position.y < cutoff_y:
                    for s in cr['shapes']:
                        if s in self.space.shapes: self.space.remove(s)
                    if cr['body'] in self.space.bodies: self.space.remove(cr['body'])
                else: active_c_rings.append(cr)
            self.c_rings = active_c_rings

            active_gears = []
            for gear in self.gear_spinners:
                if gear['body'].position.y < cutoff_y:
                    for s in gear['shapes']:
                        if s in self.space.shapes: self.space.remove(s)
                    if gear['body'] in self.space.bodies: self.space.remove(gear['body'])
                else: active_gears.append(gear)
            self.gear_spinners = active_gears

            active_sectors = []
            for sec in self.sector_spinners:
                if sec['body'].position.y < cutoff_y:
                    for s in sec['shapes']:
                        if s in self.space.shapes: self.space.remove(s)
                    if sec['body'] in self.space.bodies: self.space.remove(sec['body'])
                else: active_sectors.append(sec)
            self.sector_spinners = active_sectors
            
            # 单独回收动态挡板资源
            active_flippers = []
            for f in self.flippers:
                if f['body'].position.y < cutoff_y:
                    if f['shape'] in self.space.shapes: self.space.remove(f['shape'])
                    if f['body'] in self.space.bodies: self.space.remove(f['body'])
                    for j in f['joints']:
                        if j in self.space.constraints: self.space.remove(j)
                else: 
                    active_flippers.append(f)
            self.flippers = active_flippers

            self.teleport_zones = [z for z in self.teleport_zones if z['end_y'] >= cutoff_y]
            self.bg_dots = [dot for dot in self.bg_dots if dot[1] >= cutoff_y]


        current_finished_count = len([b for b in self.my_balls if b['finished']])
        for b in self.my_balls:
            if not b['finished'] and b['body'].position.y > self.track_end_y: 
                b['finished'] = True
                current_finished_count += 1
                b['finish_rank'] = current_finished_count
                if not self.first_finisher: self.first_finisher = b

        active = [b for b in self.my_balls if not b['finished']]
        new_leader = self.first_finisher if self.first_finisher else (max(active, key=lambda b: b['body'].position.y) if active else None)
        
        if new_leader != self.leader:
            if self.leader and self.leader['player']: self.leader['player'].stop()
            self.leader = new_leader
            
            # 拦截：只有在正式比赛阶段（即不是倒计时）发生第一名更替时，才播放音乐
            if self.game_state == "RACING" and self.leader and self.leader['player']:
                self.leader['player'].setPosition(0)
                self.leader['player'].play()

        # 拦截：只有在正式比赛阶段，如果没有提供音乐，才自动生成光圈涟漪
        if self.game_state == "RACING":
            if self.leader and not self.leader.get('peak_thread'):
                self.ripple_timer += 1
                if self.ripple_timer >= (15 if self.first_finisher else 28):
                    self.ripple_timer = 0
                    self.ripples.append(0.0) 
        
        new_ripples = []
        # 光圈扩散速度变慢，如果是到达终点的状态，扩展会显得宏大
        ripple_speed = 0.015 if self.first_finisher else 0.05
        for r in self.ripples:
            r += ripple_speed
            if r <= 1.0: new_ripples.append(r)
        self.ripples = new_ripples

        self.update()

    def paintEvent(self, event):
        cw, ch = self.width(), self.height()
        dpr = self.devicePixelRatioF()
        if self._buffer is None or self._buffer.size() != QSize(cw, ch) or self._buffer.devicePixelRatio() != dpr:
            self._buffer = QImage(int(cw * dpr), int(ch * dpr), QImage.Format.Format_ARGB32_Premultiplied)
            self._buffer.setDevicePixelRatio(dpr)

        self._buffer.fill(QColor('#080810'))
        buf_painter = QPainter(self._buffer)
        buf_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        if self.game_state == "COUNTDOWN":
            target_y = 250 - ch * 0.5 
        else:
            target_y = (self.leader['body'].position.y if self.leader else 0) - ch * 0.7
            if target_y > self.track_end_y - ch * 0.4: target_y = self.track_end_y - ch * 0.4
            
        if target_y < -200: target_y = -200

        buf_painter.save()
        buf_painter.translate(cw / 2 - TRACK_WIDTH/2, -target_y)
        
        buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
        for px, py in self.bg_dots:
            if target_y - 100 < py < target_y + ch + 100:
                alpha = int(100 + 100 * math.sin(py * 0.1 + self.time_offset * 0.05))
                buf_painter.setBrush(QColor(0, 255, 255, alpha))
                buf_painter.drawEllipse(QPointF(px, py), 4, 4)

        for zone in self.teleport_zones:
            if target_y - 100 < zone['end_y'] and target_y + ch + 100 > zone['start_y']:
                inv_color_start = self.get_inverse_color(zone['start_y'])
                inv_color_end = self.get_inverse_color(zone['end_y'])
                
                grad = QLinearGradient(0, zone['start_y'], 0, zone['end_y'])
                grad.setColorAt(0, QColor(*inv_color_start))
                grad.setColorAt(1, QColor(*inv_color_end))
                
                buf_painter.setPen(QPen(QBrush(grad), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                
                x_pos = TRACK_WIDTH - 7 if zone['side'] == 'right' else 7
                buf_painter.drawLine(int(x_pos), int(zone['start_y']), int(x_pos), int(zone['end_y']))
                
                buf_painter.setPen(QPen(QColor(inv_color_start[0], inv_color_start[1], inv_color_start[2], 80), 30))
                buf_painter.drawLine(int(x_pos), int(zone['start_y']), int(x_pos), int(zone['end_y']))

        if self.game_state == "COUNTDOWN" and self.ring_shapes:
            buf_painter.save()
            buf_painter.translate(self.ring_body.position.x, self.ring_body.position.y)
            buf_painter.rotate(math.degrees(self.ring_body.angle))
            buf_painter.setPen(QPen(QColor(*self.config['obs_start_rgb']), 6))
            buf_painter.setBrush(QColor(0, 0, 0, 0))
            
            # 画内外圈
            buf_painter.drawEllipse(QPointF(0, 0), 160, 160)
            buf_painter.drawEllipse(QPointF(0, 0), 60, 60)
            
            # 画 12 个隔板
            baffles_count = 12
            offset_angle = math.pi / baffles_count
            for i in range(baffles_count):
                ang = i * (2 * math.pi / baffles_count) + offset_angle
                p_in = QPointF(math.cos(ang)*60, math.sin(ang)*60)
                p_out = QPointF(math.cos(ang)*160, math.sin(ang)*160)
                buf_painter.drawLine(p_in, p_out)
                
            buf_painter.restore()

        top_y, bot_y = int(target_y - 200), int(target_y + ch + 200)
        buf_painter.setPen(QPen(QColor(0, 255, 255, 80), 8))
        buf_painter.drawLine(0, top_y, 0, bot_y)
        buf_painter.drawLine(TRACK_WIDTH, top_y, TRACK_WIDTH, bot_y)

        # 修复绘制 FINISH 线段因为 float 报错的 Bug
        finish_y = int(self.track_end_y)
        if target_y < finish_y < target_y + ch + 200:
            buf_painter.setPen(QPen(QColor(255, 255, 255, 200), 6, Qt.PenStyle.DashLine))
            buf_painter.drawLine(0, finish_y, TRACK_WIDTH, finish_y)
            buf_painter.setPen(QColor(255, 255, 255, 200))
            buf_painter.setFont(QFont('Arial', 24, QFont.Weight.Black))
            buf_painter.drawText(int(TRACK_WIDTH/2 - 50), finish_y - 10, "FINISH")

        for shape in self.space.shapes:
            if hasattr(shape, '_neon_pixmap') and not getattr(shape, '_is_pulsing', False) and not getattr(shape, '_is_c_ring_seg', False):
                buf_painter.save()
                buf_painter.translate(shape.body.position.x, shape.body.position.y)
                buf_painter.rotate(math.degrees(shape.body.angle))
                buf_painter.drawPixmap(shape._neon_offset, shape._neon_pixmap)
                buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
                buf_painter.setBrush(QColor(*shape._color))
                buf_painter.drawPath(shape._core_path)
                buf_painter.restore()
                
        for p in self.pulsing_obs:
            buf_painter.save()
            buf_painter.translate(p['body'].position.x, p['body'].position.y)
            scale_ratio = p['current_r'] / p['max_r']
            buf_painter.scale(scale_ratio, scale_ratio)
            buf_painter.drawPixmap(p['offset'], p['pixmap'])
            buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
            buf_painter.setBrush(QColor(*p['color']))
            buf_painter.drawPath(p['core_path'])
            buf_painter.restore()
            
        for cr in self.c_rings:
            buf_painter.save()
            buf_painter.translate(cr['body'].position.x, cr['body'].position.y)
            buf_painter.rotate(math.degrees(cr['body'].angle))
            buf_painter.drawPixmap(cr['offset'], cr['pixmap'])
            buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
            buf_painter.setBrush(QColor(*cr['color']))
            buf_painter.drawPath(cr['core_path'])
            buf_painter.restore()

        for gear in self.gear_spinners:
            buf_painter.save()
            buf_painter.translate(gear['body'].position.x, gear['body'].position.y)
            buf_painter.rotate(math.degrees(gear['body'].angle))
            buf_painter.drawPixmap(gear['offset'], gear['pixmap'])
            buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
            buf_painter.setBrush(QColor(*gear['color']))
            buf_painter.drawPath(gear['core_path'])
            buf_painter.restore()
            
        for sec in self.sector_spinners:
            buf_painter.save()
            buf_painter.translate(sec['body'].position.x, sec['body'].position.y)
            buf_painter.rotate(math.degrees(sec['body'].angle))
            buf_painter.drawPixmap(sec['offset'], sec['pixmap'])
            buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
            buf_painter.setBrush(QColor(*sec['color']))
            buf_painter.drawPath(sec['core_path'])
            buf_painter.restore()

        if self.leader:
            buf_painter.save()
            buf_painter.translate(self.leader['body'].position.x, self.leader['body'].position.y)
            rr, gg, bb = self.leader['data']['rgb']
            for phase in self.ripples:
                # 若冠军已产生，将最大光圈从 55 暴力拉升至 800
                max_radius = 800 if self.first_finisher else 55
                current_radius = self.leader['radius'] + phase * max_radius
                glow_width = 150 if self.first_finisher else 25
                
                # 动态计算透明度
                base_opacity = 0.9 if self.first_finisher else 0.7
                alpha = int(255 * (1.0 - phase) * base_opacity)
                
                if alpha <= 0: continue
                grad = QRadialGradient(QPointF(0, 0), current_radius + glow_width)
                grad.setColorAt(0, Qt.GlobalColor.transparent)
                
                inner_stop = max(0.0, current_radius/(current_radius+glow_width) - 0.001)
                grad.setColorAt(inner_stop, Qt.GlobalColor.transparent)
                grad.setColorAt(current_radius/(current_radius+glow_width), QColor(rr, gg, bb, alpha))
                grad.setColorAt(1.0, Qt.GlobalColor.transparent)
                
                buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
                buf_painter.setBrush(QBrush(grad))
                buf_painter.drawEllipse(QPointF(0, 0), current_radius + glow_width, current_radius + glow_width)
            buf_painter.restore()

        for b in self.my_balls:
            raw_pts = b['history'] + [(b['body'].position.x, b['body'].position.y)]
            spline_pts = catmull_rom_spline(raw_pts, steps=4)
            n = len(spline_pts)
            
            if n >= 2 and math.hypot(spline_pts[-1][0]-spline_pts[0][0], spline_pts[-1][1]-spline_pts[0][1]) > 1:
                rr, gg, bb = b['data']['rgb']
                buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
                for i in range(n):
                    t = i / (n - 1)
                    width = b['radius'] * (0.3 + 0.7 * t)
                    alpha = int(200 * t)
                    buf_painter.setBrush(QColor(rr, gg, bb, alpha))
                    buf_painter.drawEllipse(QPointF(*spline_pts[i]), width, width)

            pos = b['body'].position
            buf_painter.save()
            buf_painter.translate(pos.x, pos.y)
            buf_painter.rotate(math.degrees(b['body'].angle))
            
            # ====== 新增：冠军专属闪烁大辉光底座 ======
            if b == self.first_finisher:
                # 使用正弦波做周期性呼吸效果 (0.0 ~ 1.0)
                glow_phase = (math.sin(self.time_offset * 0.15) + 1.0) / 2.0 
                champion_glow_radius = b['radius'] + 20 + glow_phase * 40
                c_alpha = int(80 + 175 * glow_phase)
                rr, gg, bb = b['data']['rgb']
                
                champ_grad = QRadialGradient(QPointF(0, 0), champion_glow_radius)
                champ_grad.setColorAt(0, QColor(rr, gg, bb, c_alpha))
                champ_grad.setColorAt(0.6, QColor(rr, gg, bb, int(c_alpha * 0.5)))
                champ_grad.setColorAt(1.0, Qt.GlobalColor.transparent)
                
                buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
                buf_painter.setBrush(QBrush(champ_grad))
                
                # 抵消由于小球自身的物理角度旋转造成的画刷偏移
                buf_painter.save()
                buf_painter.rotate(-math.degrees(b['body'].angle))
                buf_painter.drawEllipse(QPointF(0, 0), champion_glow_radius, champion_glow_radius)
                buf_painter.restore()

            # 绘制小球本体
            buf_painter.drawPixmap(b['offset'], b['pixmap'])
            buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
            buf_painter.setBrush(b['skin_brush'] if b['skin_brush'] else QColor(*b['data']['rgb']))
            buf_painter.drawPath(b['path'])
            buf_painter.restore()
            
            name = b['data']['name']
            if name:
                buf_painter.setPen(QColor('#ffffff'))
                buf_painter.setFont(QFont('Arial', 10, QFont.Weight.Bold))
                tw = buf_painter.fontMetrics().horizontalAdvance(name)
                buf_painter.drawText(int(pos.x - tw/2), int(pos.y - 32), name)
                
            if b['finished']:
                rank_text = f"#{b['finish_rank']}"
                buf_painter.setPen(b['data']['color'])
                buf_painter.setFont(QFont('Arial', 16, QFont.Weight.Black))
                tw = buf_painter.fontMetrics().horizontalAdvance(rank_text)
                # 修复当小球没有提供名字时名次文字纵向坐标错位的 Bug
                y_offset = 48 if name else 32
                buf_painter.drawText(int(pos.x - tw/2), int(pos.y - y_offset), rank_text)

        if self.game_state == "COUNTDOWN":
            sec_left = math.ceil(self.countdown_ticks / 60)
            text = str(sec_left) if sec_left > 0 else "GO!"
            buf_painter.setPen(QColor('#ffffff'))
            buf_painter.setFont(QFont('Arial', 60, QFont.Weight.Black))
            tw = buf_painter.fontMetrics().horizontalAdvance(text)
            buf_painter.drawText(int(TRACK_WIDTH/2 - tw/2), 270, text)

        buf_painter.restore()

        if self.game_state != "COUNTDOWN":
            buf_painter.setBrush(QColor(0, 0, 0, 140))
            buf_painter.setPen(QPen(Qt.PenStyle.NoPen))
            buf_painter.drawRoundedRect(10, 10, 260, 60, 8, 8)
            if self.leader:
                buf_painter.setPen(self.leader['data']['color'])
                buf_painter.setFont(QFont('Arial', 12, QFont.Weight.Bold))
                state = "🏆 Winner" if self.first_finisher else "🔥 Leading"
                buf_painter.drawText(20, 32, f"{state}: {self.leader['data']['name']}")
                all_finished = all(ball['finished'] for ball in self.my_balls)
                buf_painter.setPen(QColor('#aaaaaa'))
                buf_painter.drawText(20, 52, "RACE FINISHED!" if all_finished else "RACING...")

        buf_painter.end()

        screen = QPainter(self)
        screen.drawImage(0, 0, self._buffer)
        screen.end()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neon Marble Race")
        self.resize(540, 960) 
        self.setStyleSheet("MainWindow { background-color: #080810; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.ui = SetupUI(self.start_game)
        self.engine = GameEngineWidget(self.go_home)

        self.stack.addWidget(self.ui)
        self.stack.addWidget(self.engine)

    def start_game(self, config):
        self.stack.setCurrentWidget(self.engine)
        self.engine.start_game(config)

    def go_home(self):
        self.stack.setCurrentWidget(self.ui)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    icon_path = resource_path("neon_race.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())