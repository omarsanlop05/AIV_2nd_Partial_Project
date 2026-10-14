import math
import sys
import pygame

from Dijkstra import Graph

pygame.init()
pygame.key.set_repeat(400, 35)

# ───────────────────────── Configuración ─────────────────────────
W, H = 1200, 720
PANEL_X = 780
PW = W - PANEL_X
CANVAS_RECT = pygame.Rect(0, 0, PANEL_X, H - 30)
STATUS_RECT = pygame.Rect(0, H - 30, PANEL_X, 30)

NODE_R = 24          # radio visual
COLLIDER_R = 32      # radio del collider (un poco mayor para que no queden pegados)
MAX_LABEL = 12
LABEL_DELAY_MS = 1000
STEP_MS = 700        # duración de la animación por flecha del camino

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK = (40, 40, 48)
GRAY = (170, 172, 180)
LIGHT = (232, 234, 240)
PANEL_BG = (245, 246, 250)
BLUE = (50, 110, 230)
RED = (205, 45, 45)
GREEN = (30, 140, 70)
YELLOW = (255, 196, 0)

FONT = pygame.font.SysFont("arial", 18)
FONT_B = pygame.font.SysFont("arial", 18, bold=True)
FONT_S = pygame.font.SysFont("arial", 15)


# ───────────────────────── Utilidades ─────────────────────────
class GraphEx(Graph):
    """Graph + la función que faltaba para actualizar el label de un nodo."""

    def update_vertex_data(self, index, data):
        if 0 <= index < self.size:
            self.nodes[index].label = data


def draw_text(surf, text, font, color, pos, anchor="topleft"):
    img = font.render(text, True, color)
    r = img.get_rect(**{anchor: pos})
    surf.blit(img, r)
    return r


def wrap_text(text, font, width):
    lines, cur = [], ""
    for word in text.split(" "):
        test = (cur + " " + word).strip()
        if font.size(test)[0] <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fmt_num(x):
    x = float(x)
    return str(int(x)) if x.is_integer() else f"{x:.2f}".rstrip("0").rstrip(".")


def parse_weight(text):
    """Devuelve el peso (>= 0) o None si el texto no es válido."""
    try:
        v = float(text)
    except ValueError:
        return None
    if v < 0 or math.isnan(v) or math.isinf(v):
        return None
    return int(v) if v.is_integer() else v


# ───────────────────────── Collider ─────────────────────────
class Collider:
    def __init__(self, center, radius):
        self.center = pygame.Vector2(center)
        self.radius = radius

    def contains_point(self, p):
        return self.center.distance_to(p) <= self.radius

    def overlaps(self, other):
        return self.center.distance_to(other.center) < self.radius + other.radius


# ───────────────────────── Widgets ─────────────────────────
class TextInput:
    def __init__(self, rect, text="", max_len=MAX_LABEL, allowed=None,
                 on_change=None, placeholder=""):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.max_len = max_len
        self.allowed = allowed
        self.on_change = on_change
        self.placeholder = placeholder
        self.focused = False
        self.enabled = True

    def handle_event(self, e):
        if not self.enabled:
            self.focused = False
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.focused = self.rect.collidepoint(e.pos)
            return self.focused
        if e.type == pygame.KEYDOWN and self.focused:
            old = self.text
            if e.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self.focused = False
            elif (e.unicode and e.unicode.isprintable() and len(self.text) < self.max_len
                  and (self.allowed is None or e.unicode in self.allowed)):
                self.text += e.unicode
            if self.text != old and self.on_change:
                self.on_change(self.text)
            return True
        return False

    def draw(self, surf):
        pygame.draw.rect(surf, WHITE if self.enabled else LIGHT, self.rect, border_radius=6)
        pygame.draw.rect(surf, BLUE if self.focused else GRAY, self.rect, 2, border_radius=6)
        if self.text:
            img = FONT.render(self.text, True, DARK)
        else:
            img = FONT.render(self.placeholder, True, GRAY)
        surf.blit(img, (self.rect.x + 8, self.rect.centery - img.get_height() // 2))
        if self.focused and (pygame.time.get_ticks() // 500) % 2 == 0:
            x = self.rect.x + 8 + FONT.size(self.text)[0] + 1
            pygame.draw.line(surf, DARK, (x, self.rect.y + 6), (x, self.rect.bottom - 6), 2)


class Dropdown:
    active = None  # el dropdown abierto (solo uno a la vez)
    ITEM_H = 28
    MAX_VISIBLE = 6

    def __init__(self, rect, options_fn, placeholder, on_change=None):
        self.rect = pygame.Rect(rect)
        self.options_fn = options_fn      # siempre devuelve [(valor, label)] actualizado
        self.placeholder = placeholder
        self.on_change = on_change        # puede devolver False para rechazar la selección
        self.selected = None
        self.open = False
        self.offset = 0

    def selected_label(self):
        for v, l in self.options_fn():
            if v == self.selected:
                return l
        return None

    def list_rect(self):
        n = max(1, len(self.options_fn()))
        h = min(n, self.MAX_VISIBLE) * self.ITEM_H
        y = self.rect.bottom + 2
        if y + h > H:                     # si no cabe abajo, se abre hacia arriba
            y = self.rect.top - 2 - h
        return pygame.Rect(self.rect.x, y, self.rect.w, h)

    def close(self):
        self.open = False
        if Dropdown.active is self:
            Dropdown.active = None

    def handle_event(self, e):
        if self.open:
            opts = self.options_fn()
            if e.type == pygame.MOUSEWHEEL:
                self.offset = max(0, min(self.offset - e.y, max(0, len(opts) - self.MAX_VISIBLE)))
                return True
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                lr = self.list_rect()
                if lr.collidepoint(e.pos):
                    i = (e.pos[1] - lr.y) // self.ITEM_H + self.offset
                    if 0 <= i < len(opts):
                        value = opts[i][0]
                        self.close()
                        ok = self.on_change(value) if self.on_change else None
                        if ok is not False:
                            self.selected = value
                else:
                    self.close()
                return True
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            if Dropdown.active:
                Dropdown.active.close()
            self.open, self.offset = True, 0
            Dropdown.active = self
            return True
        return False

    def draw_box(self, surf):
        pygame.draw.rect(surf, WHITE, self.rect, border_radius=6)
        pygame.draw.rect(surf, BLUE if self.open else GRAY, self.rect, 2, border_radius=6)
        label = self.selected_label()
        img = FONT.render(label if label is not None else self.placeholder, True,
                          DARK if label is not None else GRAY)
        surf.blit(img, (self.rect.x + 8, self.rect.centery - img.get_height() // 2),
                  pygame.Rect(0, 0, self.rect.w - 30, img.get_height()))
        cx, cy = self.rect.right - 16, self.rect.centery
        pygame.draw.polygon(surf, DARK, [(cx - 5, cy - 3), (cx + 5, cy - 3), (cx, cy + 4)])

    def draw_list(self, surf):
        opts = self.options_fn()
        lr = self.list_rect()
        pygame.draw.rect(surf, WHITE, lr)
        mouse = pygame.mouse.get_pos()
        if not opts:
            draw_text(surf, "Sin nodos", FONT_S, GRAY, (lr.x + 8, lr.y + 6))
        for row, (value, label) in enumerate(opts[self.offset:self.offset + self.MAX_VISIBLE]):
            r = pygame.Rect(lr.x, lr.y + row * self.ITEM_H, lr.w, self.ITEM_H)
            if value == self.selected:
                pygame.draw.rect(surf, (214, 228, 255), r)
            elif r.collidepoint(mouse):
                pygame.draw.rect(surf, LIGHT, r)
            draw_text(surf, label, FONT, DARK, (r.x + 8, r.centery), "midleft")
        pygame.draw.rect(surf, BLUE, lr, 2)


class Card:
    """Tarjeta de conexión: dropdown (nodo destino) + peso + botón eliminar."""
    H = 88

    def __init__(self, app, target, weight):
        self.app = app
        self.applied_target = target      # destino realmente guardado en el grafo
        self.dd = Dropdown((0, 0, 10, 32), app.other_nodes, "Elegir nodo destino", self.on_target)
        self.dd.selected = target
        self.weight = TextInput((0, 0, 120, 28), fmt_num(weight), 6, "0123456789.", self.on_weight)
        self.rect = pygame.Rect(0, 0, 10, self.H)
        self.del_rect = pygame.Rect(0, 0, 30, 32)

    def layout(self, x, y, w):
        self.rect = pygame.Rect(x, y, w, self.H)
        self.dd.rect = pygame.Rect(x + 10, y + 10, w - 60, 32)
        self.del_rect = pygame.Rect(x + w - 40, y + 10, 30, 32)
        self.weight.rect = pygame.Rect(x + 62, y + 50, 120, 28)

    def on_target(self, value):
        app = self.app
        node = app.graph.nodes[app.selected]
        label = app.graph.nodes[value].label
        if value in node.connections and value != self.applied_target:
            app.set_message(f"Ya existe una conexión hacia '{label}'. Elige otro nodo.", "error")
            return False
        w = parse_weight(self.weight.text)
        if w is None:
            w = 0
            self.weight.text = "0"
        if self.applied_target is not None:
            node.connections.pop(self.applied_target, None)
        node.add_connection(value, w)
        self.applied_target = value
        app.invalidate_path()
        app.set_message(f"Conexión {node.label} → {label} (peso {fmt_num(w)})", "ok")
        return True

    def on_weight(self, text):
        app = self.app
        if self.applied_target is None or text in ("", "."):
            return
        w = parse_weight(text)
        if w is None:
            app.set_message("Peso inválido: debe ser un número mayor o igual a 0.", "error")
            return
        app.graph.nodes[app.selected].add_connection(self.applied_target, w)
        app.invalidate_path()

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.del_rect.collidepoint(e.pos):
            self.app.remove_card(self)
            return True
        a = self.dd.handle_event(e)
        b = self.weight.handle_event(e)
        return a or b

    def draw(self, surf):
        # Si el peso quedó vacío/ inválido al perder el foco, se restaura el valor del grafo
        if not self.weight.focused and parse_weight(self.weight.text) is None:
            cur = 0
            if self.applied_target is not None:
                cur = self.app.graph.nodes[self.app.selected].connections.get(self.applied_target, 0)
            self.weight.text = fmt_num(cur)
        pygame.draw.rect(surf, WHITE, self.rect, border_radius=10)
        pygame.draw.rect(surf, GRAY, self.rect, 1, border_radius=10)
        self.dd.draw_box(surf)
        pygame.draw.rect(surf, (250, 228, 228), self.del_rect, border_radius=6)
        c = self.del_rect.center
        pygame.draw.line(surf, RED, (c[0] - 5, c[1] - 5), (c[0] + 5, c[1] + 5), 3)
        pygame.draw.line(surf, RED, (c[0] - 5, c[1] + 5), (c[0] + 5, c[1] - 5), 3)
        draw_text(surf, "Peso", FONT, DARK, (self.rect.x + 12, self.weight.rect.centery), "midleft")
        self.weight.draw(surf)


# ───────────────────────── Canvas ─────────────────────────
class Canvas:
    def __init__(self, rect):
        self.rect = rect
        self.colliders = []   # posición/collider de cada nodo (mismo índice que en el grafo)

    def node_at(self, pos):
        for i, c in enumerate(self.colliders):
            if c.contains_point(pos):
                return i
        return None

    def check_placement(self, pos):
        """Devuelve None si se puede colocar un nodo, o el motivo si no."""
        if not self.rect.inflate(-2 * COLLIDER_R, -2 * COLLIDER_R).collidepoint(pos):
            return "Demasiado cerca del borde del lienzo."
        new = Collider(pos, COLLIDER_R)
        if any(new.overlaps(c) for c in self.colliders):
            return "Demasiado cerca de otro nodo."
        return None

    def draw_node(self, surf, center, label, selected, yellow):
        c = (int(center.x), int(center.y))
        if yellow:
            pygame.draw.circle(surf, YELLOW, c, NODE_R)
        pygame.draw.circle(surf, BLACK, c, NODE_R, 3)
        if selected:
            pygame.draw.circle(surf, BLUE, c, NODE_R + 6, 2)
        img = FONT_B.render(label, True, BLACK)
        r = img.get_rect(center=c)
        if r.w > 2 * NODE_R - 8:  # label largo: fondo blanco para que se lea
            bg = r.inflate(10, 4)
            pygame.draw.rect(surf, WHITE, bg, border_radius=6)
            pygame.draw.rect(surf, BLACK, bg, 1, border_radius=6)
        surf.blit(img, r)

    def draw_arrow(self, surf, c1, c2, bidir, progress):
        """Dibuja la flecha c1→c2. `progress` (0-1) es cuánto se ha pintado de amarillo.
        Devuelve la posición donde va el label del peso."""
        d = c2 - c1
        d = d / d.length()
        n = pygame.Vector2(-d.y, d.x)
        off = 9 if bidir else 0                      # separa flechas A→B y B→A
        t = math.sqrt(NODE_R ** 2 - off ** 2)
        start = c1 + n * off + d * t
        tip = c2 + n * off - d * t
        base = tip - d * 14
        head = [tip, base + n * 7, base - n * 7]
        pygame.draw.line(surf, BLACK, start, base, 2)
        pygame.draw.polygon(surf, BLACK, head)
        if progress > 0:
            p = start + (base - start) * min(progress, 1)
            pygame.draw.line(surf, BLACK, start, p, 8)
            pygame.draw.line(surf, YELLOW, start, p, 4)
            if progress >= 1:
                pygame.draw.polygon(surf, BLACK, [tip + d * 2, base + n * 9, base - n * 9])
                pygame.draw.polygon(surf, YELLOW, head)
        return (start + tip) / 2 + n * (off + 14)

    def draw_weight(self, surf, pos, w):
        img = FONT_S.render(fmt_num(w), True, DARK)
        r = img.get_rect(center=(int(pos.x), int(pos.y)))
        pygame.draw.rect(surf, WHITE, r.inflate(6, 2), border_radius=4)
        surf.blit(img, r)


# ───────────────────────── Aplicación ─────────────────────────
class App:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Dijkstra – camino más corto")
        self.clock = pygame.time.Clock()

        self.graph = GraphEx()
        self.canvas = Canvas(CANVAS_RECT)
        self.selected = None

        # Panel de nodo / conexiones
        self.label_input = TextInput((PANEL_X + 16, 44, PW - 32, 34), "", MAX_LABEL, None,
                                     self.on_label_typed, "Label del nodo")
        self.label_input.enabled = False
        self.label_pending = False
        self.label_t = 0
        self.plus_rect = pygame.Rect(W - 16 - 32, 92, 32, 32)
        self.cards_area = pygame.Rect(PANEL_X + 8, 132, PW - 16, 372)
        self.cards = []
        self.scroll = 0

        # Panel de ejecución
        self.dd_start = Dropdown((PANEL_X + 16, 584, 186, 32), self.all_nodes, "Nodo inicial")
        self.dd_end = Dropdown((PANEL_X + 16 + 186 + 16, 584, 186, 32), self.all_nodes, "Nodo final")
        self.run_rect = pygame.Rect(PANEL_X + 16, 628, PW - 32, 36)
        self.result_text, self.result_kind = "", "info"

        # Animación del camino
        self.path_edges, self.edge_index, self.path_nodes, self.anim_t0 = [], {}, None, 0

        self.msg, self.msg_kind, self.msg_until = "", "info", 0

    # ----- datos / helpers -----
    def all_nodes(self):
        return [(i, n.label) for i, n in enumerate(self.graph.nodes)]

    def other_nodes(self):
        return [(i, n.label) for i, n in enumerate(self.graph.nodes) if i != self.selected]

    def set_message(self, text, kind="info", ms=4500):
        self.msg, self.msg_kind, self.msg_until = text, kind, pygame.time.get_ticks() + ms

    def invalidate_path(self):
        """Cualquier cambio en el grafo invalida el camino mostrado."""
        self.path_edges, self.edge_index, self.path_nodes = [], {}, None
        self.result_text = ""

    def generic_label(self, exclude=None):
        used = {n.label.lower() for i, n in enumerate(self.graph.nodes) if i != exclude}
        i = 0
        while True:
            name = chr(65 + i % 26) + (str(i // 26) if i >= 26 else "")
            if name.lower() not in used:
                return name
            i += 1

    def validate_label(self, text, idx):
        if not text:
            return "El label no puede estar vacío."
        bad = [c for c in text if not (c.isalnum() or c in "_ ")]
        if bad:
            return f"Carácter no permitido: '{bad[0]}' (solo letras, números, _ y espacio)."
        if any(n.label.lower() == text.lower() for i, n in enumerate(self.graph.nodes) if i != idx):
            return f"El label '{text}' ya existe."
        return None

    # ----- selección y nodos -----
    def select_node(self, idx):
        self.commit_label()
        self.selected = idx
        self.label_input.enabled = idx is not None
        self.label_input.focused = False
        self.label_input.text = self.graph.nodes[idx].label if idx is not None else ""
        self.rebuild_cards()

    def create_node(self, pos):
        pos = pygame.Vector2(pos)
        hit = self.canvas.node_at(pos)
        if hit is not None:                       # click sobre un nodo existente: seleccionarlo
            self.select_node(hit)
            return
        reason = self.canvas.check_placement(pos)
        if reason:
            self.set_message(reason, "error")
            return
        label = self.generic_label()
        self.graph.add_vertex_data(label)
        self.canvas.colliders.append(Collider(pos, COLLIDER_R))
        self.invalidate_path()
        self.select_node(len(self.canvas.colliders) - 1)
        self.set_message(f"Nodo '{label}' creado.", "ok")

    # ----- label -----
    def on_label_typed(self, _text):
        self.label_pending, self.label_t = True, pygame.time.get_ticks()

    def commit_label(self):
        if not self.label_pending or self.selected is None:
            self.label_pending = False
            return
        self.label_pending = False
        idx = self.selected
        text = self.label_input.text.strip()
        if text == self.graph.nodes[idx].label:
            return
        err = self.validate_label(text, idx)
        if err:
            new = self.generic_label(exclude=idx)
            self.graph.update_vertex_data(idx, new)
            self.label_input.text = new
            self.set_message(f"{err} Se asignó '{new}'.", "error", 6000)
        else:
            self.graph.update_vertex_data(idx, text)
            self.label_input.text = text
            self.set_message(f"Label actualizado a '{text}'.", "ok")
        self.invalidate_path()

    # ----- conexiones -----
    def rebuild_cards(self):
        self.cards, self.scroll = [], 0
        if self.selected is not None:
            for t, w in self.graph.nodes[self.selected].connections.items():
                self.cards.append(Card(self, t, w))

    def max_scroll(self):
        content = len(self.cards) * (Card.H + 8) + 8
        return max(0, content - self.cards_area.h)

    def add_card(self):
        if self.selected is None:
            self.set_message("Selecciona un nodo primero.", "error")
        elif not self.other_nodes():
            self.set_message("No hay otros nodos a los que conectar.", "error")
        elif len(self.cards) >= len(self.other_nodes()):
            self.set_message("Ya hay una conexión hacia todos los demás nodos.", "error")
        else:
            self.cards.append(Card(self, None, 1))
            self.scroll = self.max_scroll()

    def remove_card(self, card):
        if card.applied_target is not None:
            self.graph.nodes[self.selected].connections.pop(card.applied_target, None)
            self.invalidate_path()
        self.cards.remove(card)
        self.scroll = min(self.scroll, self.max_scroll())

    # ----- ejecución -----
    def run_dijkstra(self):
        self.commit_label()
        s, e = self.dd_start.selected, self.dd_end.selected
        if s is None or e is None:
            self.result_text, self.result_kind = "Selecciona el nodo inicial y el final.", "error"
            self.set_message(self.result_text, "error")
            return
        labels = self.graph.vertex_data
        _dist, path = self.graph.dijkstra(labels[s], labels[e])
        self.invalidate_path()
        if path is None:
            self.result_text = f"No hay camino de '{labels[s]}' a '{labels[e]}'."
            self.result_kind = "error"
            self.set_message(self.result_text, "error", 6000)
            return
        names = path if isinstance(path, list) else path.split("->")
        idxs = [labels.index(n) for n in names]
        self.path_edges = list(zip(idxs, idxs[1:]))
        self.edge_index = {edge: k for k, edge in enumerate(self.path_edges)}
        self.path_nodes = (idxs[0], idxs[-1])
        self.anim_t0 = pygame.time.get_ticks()
        self.result_text = f"Camino: {' → '.join(names)}  |  Distancia: {fmt_num(_dist)}"
        self.result_kind = "ok"

    # ───────── eventos ─────────
    def on_click(self, e):
        pos = e.pos
        self.label_input.handle_event(e)
        in_area = self.cards_area.collidepoint(pos)
        for c in list(self.cards):
            if in_area:
                c.handle_event(e)
            else:
                c.weight.focused = False
        if self.dd_start.handle_event(e) or self.dd_end.handle_event(e):
            return
        if CANVAS_RECT.collidepoint(pos):
            self.create_node(pos)
        elif self.plus_rect.collidepoint(pos):
            self.add_card()
        elif self.run_rect.collidepoint(pos):
            self.run_dijkstra()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if Dropdown.active and e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
                Dropdown.active.handle_event(e)
                continue
            if e.type == pygame.MOUSEWHEEL:
                if self.cards_area.collidepoint(pygame.mouse.get_pos()):
                    self.scroll = max(0, min(self.scroll - e.y * 30, self.max_scroll()))
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.on_click(e)
            elif e.type == pygame.KEYDOWN:
                self.label_input.handle_event(e)
                for c in self.cards:
                    c.weight.handle_event(e)

    def update(self):
        if self.label_pending and pygame.time.get_ticks() - self.label_t >= LABEL_DELAY_MS:
            self.commit_label()

    # ───────── dibujo ─────────
    def draw_canvas(self, now):
        scr = self.screen
        scr.fill(WHITE, CANVAS_RECT)
        scr.set_clip(CANVAS_RECT)
        cols = self.canvas.colliders
        weights = []
        for u, node in enumerate(self.graph.nodes):
            for v, w in node.connections.items():
                bidir = u in self.graph.nodes[v].connections
                progress = 0
                if (u, v) in self.edge_index:
                    progress = (now - self.anim_t0 - self.edge_index[(u, v)] * STEP_MS) / STEP_MS
                    progress = max(0, min(1, progress))
                pos = self.canvas.draw_arrow(scr, cols[u].center, cols[v].center, bidir, progress)
                weights.append((pos, w))
        for pos, w in weights:
            self.canvas.draw_weight(scr, pos, w)

        done = self.path_nodes and now - self.anim_t0 >= len(self.path_edges) * STEP_MS
        for i, node in enumerate(self.graph.nodes):
            yellow = bool(self.path_nodes) and (i == self.path_nodes[0] or (i == self.path_nodes[1] and done))
            self.canvas.draw_node(scr, cols[i].center, node.label, i == self.selected, yellow)
        scr.set_clip(None)

        pygame.draw.rect(scr, PANEL_BG, STATUS_RECT)
        if now < self.msg_until:
            color = {"error": RED, "ok": GREEN}.get(self.msg_kind, DARK)
            text = self.msg
        else:
            color, text = GRAY, "Click en el lienzo: crear nodo  |  click sobre un nodo: seleccionarlo"
        draw_text(scr, text, FONT_S, color, (12, STATUS_RECT.centery), "midleft")

    def draw_plus(self, enabled):
        pygame.draw.rect(self.screen, BLUE if enabled else GRAY, self.plus_rect, border_radius=8)
        cx, cy = self.plus_rect.center
        pygame.draw.line(self.screen, WHITE, (cx - 8, cy), (cx + 8, cy), 3)
        pygame.draw.line(self.screen, WHITE, (cx, cy - 8), (cx, cy + 8), 3)

    def draw_panel(self):
        scr = self.screen
        pygame.draw.rect(scr, PANEL_BG, (PANEL_X, 0, PW, H))
        pygame.draw.line(scr, GRAY, (PANEL_X, 0), (PANEL_X, H), 2)

        # Nodo seleccionado
        if self.selected is None:
            draw_text(scr, "Ningún nodo seleccionado", FONT_B, DARK, (PANEL_X + 16, 14))
        else:
            draw_text(scr, f"Nodo seleccionado: {self.graph.nodes[self.selected].label}",
                      FONT_B, DARK, (PANEL_X + 16, 14))
        self.label_input.draw(scr)

        # Conexiones
        draw_text(scr, "Conexiones salientes", FONT_B, DARK, (PANEL_X + 16, 108), "midleft")
        self.draw_plus(self.selected is not None)
        pygame.draw.rect(scr, LIGHT, self.cards_area, border_radius=8)
        scr.set_clip(self.cards_area)
        self.scroll = max(0, min(self.scroll, self.max_scroll()))
        for i, c in enumerate(self.cards):
            y = self.cards_area.y + 8 + i * (Card.H + 8) - int(self.scroll)
            c.layout(self.cards_area.x + 6, y, self.cards_area.w - 12)
            if c.rect.bottom > self.cards_area.top and c.rect.top < self.cards_area.bottom:
                c.draw(scr)
        if not self.cards:
            msg = "Pulsa + para agregar una conexión" if self.selected is not None \
                else "Selecciona o crea un nodo"
            draw_text(scr, msg, FONT_S, GRAY, self.cards_area.center, "center")
        ms = self.max_scroll()
        if ms > 0:
            bar_h = max(30, self.cards_area.h * self.cards_area.h // (self.cards_area.h + ms))
            bar_y = self.cards_area.y + (self.cards_area.h - bar_h) * self.scroll // ms
            pygame.draw.rect(scr, GRAY, (self.cards_area.right - 6, bar_y, 4, bar_h), border_radius=2)
        scr.set_clip(None)

        # Ejecución
        pygame.draw.line(scr, GRAY, (PANEL_X + 10, 516), (W - 10, 516), 1)
        draw_text(scr, "Ejecutar Dijkstra", FONT_B, DARK, (PANEL_X + 16, 526))
        draw_text(scr, "Inicio", FONT_S, DARK, (self.dd_start.rect.x, 562))
        draw_text(scr, "Fin", FONT_S, DARK, (self.dd_end.rect.x, 562))
        self.dd_start.draw_box(scr)
        self.dd_end.draw_box(scr)
        pygame.draw.rect(scr, BLUE, self.run_rect, border_radius=8)
        draw_text(scr, "Ejecutar", FONT_B, WHITE, self.run_rect.center, "center")
        color = RED if self.result_kind == "error" else GREEN
        for i, line in enumerate(wrap_text(self.result_text, FONT_S, PW - 32)[:2]):
            draw_text(scr, line, FONT_S, color, (PANEL_X + 16, 672 + i * 18))

    def run(self):
        while True:
            self.handle_events()
            self.update()
            now = pygame.time.get_ticks()
            self.draw_canvas(now)
            self.draw_panel()
            if Dropdown.active:
                Dropdown.active.draw_list(self.screen)   # overlay siempre encima
            pygame.display.flip()
            self.clock.tick(60)


if __name__ == "__main__":
    App().run()