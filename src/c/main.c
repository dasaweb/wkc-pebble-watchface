/*
 * WKC – Würzburger Kneipenchor Watchface
 *
 * Basis ist der runde Teil des Logos ("CHOR" mit Flasche). Die beiden Ringe
 * sind die Zeiger: außen = Minuten, innen = Stunden.
 *
 * Drei Designs, Wechsel per Handgelenk-Schütteln (wird gespeichert):
 *   0 "Pegel"  – die Ringe füllen sich im Uhrzeigersinn (Original-Textur)
 *   1 "Lücke"  – die Ringe sind komplett, eine Lücke mit Kronkorken zeigt die Zeit
 *   2 "Prost"  – glatte Bögen, Stunden in Bier-Gelb, die Flasche zeigt den Akku
 */
#include <pebble.h>

#define STYLE_COUNT 3
#define PERSIST_STYLE 1

// Geometrie relativ zum Logo-Radius (aus tools/make_assets.py, R_CROP = 850)
#define F_CONTENT  706   // Inhalt endet hier
#define F_SPLIT    778   // Grenze zwischen innerem und äußerem Ring
#define F_INNER    735   // Mittellinie Stundenring
#define F_OUTER    822   // Mittellinie Minutenring
#define F_HALF      25   // halbe Ringbreite
#define F_CROP     850

// Bierfüllung (Flasche) in Anteilen der Bitmap-Höhe, in Promille
#define BEER_TOP    146
#define BEER_BOTTOM 842

static Window *s_window;
static Layer *s_canvas;
static GBitmap *s_logo;
#ifdef PBL_COLOR
static GBitmap *s_beer;
#endif
static int s_style;
static int s_battery = 100;

// "Bier": GColorChromeYellow wirkt auf den echten Displays lachsfarben, Yellow passt
#define ACCENT PBL_IF_COLOR_ELSE(GColorYellow, GColorWhite)
#define DOTS   PBL_IF_COLOR_ELSE(GColorLightGray, GColorWhite)

static int scale(int r_logo, int f) {
  return (r_logo * f + F_CROP / 2) / F_CROP;
}

static GPoint polar(GPoint c, int r, int32_t angle) {
  return GPoint(c.x + sin_lookup(angle) * r / TRIG_MAX_RATIO,
                c.y - cos_lookup(angle) * r / TRIG_MAX_RATIO);
}

// Füllt einen Kreisring-Sektor zwischen r_in und r_out von a0 bis a1 (TRIG-Winkel,
// 0 = 12 Uhr, im Uhrzeigersinn). Bereiche über 12 Uhr hinweg werden aufgeteilt.
static void fill_band(GContext *ctx, GPoint c, int r_in, int r_out,
                      int32_t a0, int32_t a1) {
  if (a1 <= a0) {
    return;
  }
  if (a0 < 0) {
    fill_band(ctx, c, r_in, r_out, a0 + TRIG_MAX_ANGLE, TRIG_MAX_ANGLE);
    a0 = 0;
  }
  if (a1 > TRIG_MAX_ANGLE) {
    fill_band(ctx, c, r_in, r_out, 0, a1 - TRIG_MAX_ANGLE);
    a1 = TRIG_MAX_ANGLE;
  }
  GRect rect = GRect(c.x - r_out, c.y - r_out, 2 * r_out + 1, 2 * r_out + 1);
  graphics_fill_radial(ctx, rect, GOvalScaleModeFitCircle, r_out - r_in, a0, a1);
}

static void draw_dots(GContext *ctx, GPoint c, int r, int32_t from, int step_deg,
                      int dot) {
  graphics_context_set_fill_color(ctx, DOTS);
  graphics_context_set_stroke_color(ctx, DOTS);
  for (int deg = 0; deg < 360; deg += step_deg) {
    int32_t a = DEG_TO_TRIGANGLE(deg);
    if (a > from) {
      if (dot > 0) {
        graphics_fill_circle(ctx, polar(c, r, a), dot);
      } else {
        graphics_draw_pixel(ctx, polar(c, r, a));
      }
    }
  }
}

static void draw_cap(GContext *ctx, GPoint c, int r, int32_t angle, int size) {
  GPoint p = polar(c, r, angle);
  graphics_context_set_fill_color(ctx, ACCENT);
  graphics_fill_circle(ctx, p, size);
#ifdef PBL_COLOR
  graphics_context_set_stroke_color(ctx, GColorWindsorTan);
  graphics_context_set_stroke_width(ctx, 1);
  graphics_draw_circle(ctx, p, size - 2);
#endif
}

static void canvas_update_proc(Layer *layer, GContext *ctx) {
  GRect bounds = layer_get_bounds(layer);
  GRect logo = gbitmap_get_bounds(s_logo);
  int d = logo.size.w;
  GPoint origin = GPoint((bounds.size.w - d) / 2, (bounds.size.h - d) / 2);
  GPoint c = GPoint(origin.x + d / 2, origin.y + d / 2);
  int R = d / 2;

  int r_content = scale(R, F_CONTENT);
  int r_split = scale(R, F_SPLIT);
  int r_inner = scale(R, F_INNER);
  int r_outer = scale(R, F_OUTER);
  int half = scale(R, F_HALF);
  if (half < 2) half = 2;

  time_t now = time(NULL);
  struct tm *t = localtime(&now);
#ifdef WKC_DEMO  // feste Uhrzeit für Screenshots
  t->tm_hour = 10;
  t->tm_min = 8;
#endif
  int32_t a_min = TRIG_MAX_ANGLE * t->tm_min / 60;
  int32_t a_hour = TRIG_MAX_ANGLE * ((t->tm_hour % 12) * 60 + t->tm_min) / 720;

  graphics_context_set_antialiased(ctx, true);
  graphics_context_set_fill_color(ctx, GColorBlack);
  graphics_fill_rect(ctx, bounds, 0, GCornerNone);
  graphics_draw_bitmap_in_rect(ctx, s_logo, GRect(origin.x, origin.y, d, d));

  graphics_context_set_fill_color(ctx, GColorBlack);
  switch (s_style) {
    case 0: {  // Pegel: verstrichener Teil bleibt stehen, der Rest wird gelöscht
      fill_band(ctx, c, r_content, r_split, a_hour, TRIG_MAX_ANGLE);
      fill_band(ctx, c, r_split, R + 2, a_min, TRIG_MAX_ANGLE);
      int dot = d >= 200 ? 1 : 0;
      draw_dots(ctx, c, r_outer, a_min, 6, dot);
      draw_dots(ctx, c, r_inner, a_hour, 30, dot + 1);
      break;
    }
    case 1: {  // Lücke: an der Zeigerposition fehlt ein Stück Ring
      int32_t gap = DEG_TO_TRIGANGLE(11);
      fill_band(ctx, c, r_content, r_split, a_hour - gap, a_hour + gap);
      fill_band(ctx, c, r_split, R + 2, a_min - gap, a_min + gap);
      draw_cap(ctx, c, r_inner, a_hour, half + 2);
      draw_cap(ctx, c, r_outer, a_min, half + 2);
      break;
    }
    default: {  // Prost: glatte Bögen, Flasche = Akkustand
      fill_band(ctx, c, r_content, R + 2, 0, TRIG_MAX_ANGLE);
#ifdef PBL_COLOR
      graphics_context_set_stroke_color(ctx, GColorDarkGray);
      graphics_context_set_stroke_width(ctx, 1);
      graphics_draw_circle(ctx, c, r_inner);
      graphics_draw_circle(ctx, c, r_outer);
#endif

      graphics_context_set_fill_color(ctx, ACCENT);
      fill_band(ctx, c, r_inner - half, r_inner + half, 0, a_hour);
      graphics_fill_circle(ctx, polar(c, r_inner, a_hour), half);
      graphics_fill_circle(ctx, polar(c, r_inner, 0), half);

      graphics_context_set_fill_color(ctx, GColorWhite);
      fill_band(ctx, c, r_outer - half, r_outer + half, 0, a_min);
      graphics_fill_circle(ctx, polar(c, r_outer, a_min), half);
      graphics_fill_circle(ctx, polar(c, r_outer, 0), half);

#ifdef PBL_COLOR
      int top = d * BEER_TOP / 1000;
      int bottom = d * BEER_BOTTOM / 1000;
      int level = bottom - (bottom - top) * s_battery / 100;
      GBitmap *sub = gbitmap_create_as_sub_bitmap(s_beer,
                                                  GRect(0, level, d, d - level));
      graphics_context_set_compositing_mode(ctx, GCompOpSet);
      graphics_draw_bitmap_in_rect(ctx, sub,
                                   GRect(origin.x, origin.y + level, d, d - level));
      graphics_context_set_compositing_mode(ctx, GCompOpAssign);
      gbitmap_destroy(sub);
#endif
      break;
    }
  }
}

static void tick_handler(struct tm *tick_time, TimeUnits changed) {
  layer_mark_dirty(s_canvas);
}

static void battery_handler(BatteryChargeState state) {
  s_battery = state.charge_percent;
  layer_mark_dirty(s_canvas);
}

static void tap_handler(AccelAxisType axis, int32_t direction) {
  s_style = (s_style + 1) % STYLE_COUNT;
  persist_write_int(PERSIST_STYLE, s_style);
  layer_mark_dirty(s_canvas);
}

static void window_load(Window *window) {
  Layer *root = window_get_root_layer(window);
  s_canvas = layer_create(layer_get_bounds(root));
  layer_set_update_proc(s_canvas, canvas_update_proc);
  layer_add_child(root, s_canvas);
}

static void window_unload(Window *window) {
  layer_destroy(s_canvas);
}

static void init(void) {
  s_style = persist_exists(PERSIST_STYLE) ? persist_read_int(PERSIST_STYLE) : 0;
  if (s_style < 0 || s_style >= STYLE_COUNT) s_style = 0;

  s_logo = gbitmap_create_with_resource(RESOURCE_ID_LOGO);
#ifdef PBL_COLOR
  s_beer = gbitmap_create_with_resource(RESOURCE_ID_BEER);
#endif

  s_window = window_create();
  window_set_background_color(s_window, GColorBlack);
  window_set_window_handlers(s_window, (WindowHandlers) {
    .load = window_load,
    .unload = window_unload,
  });
  window_stack_push(s_window, true);

  s_battery = battery_state_service_peek().charge_percent;
  tick_timer_service_subscribe(MINUTE_UNIT, tick_handler);
  battery_state_service_subscribe(battery_handler);
  accel_tap_service_subscribe(tap_handler);
}

static void deinit(void) {
  accel_tap_service_unsubscribe();
  battery_state_service_unsubscribe();
  tick_timer_service_unsubscribe();
  window_destroy(s_window);
  gbitmap_destroy(s_logo);
#ifdef PBL_COLOR
  gbitmap_destroy(s_beer);
#endif
}

int main(void) {
  init();
  app_event_loop();
  deinit();
}
