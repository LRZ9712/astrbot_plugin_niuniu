import asyncio
import os
import re
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont


class NiuniuCardRenderer:
    WIDTH = 760
    OUTER_PADDING = 28
    CARD_WIDTH = 704
    HEADER_HEIGHT = 112
    FOOTER_HEIGHT = 52

    COLORS = {
        "ink": "#292B2D",
        "paper": "#FFFDF8",
        "pasture": "#DFF3D8",
        "grass": "#BDE5AA",
        "pink": "#FFD9E2",
        "pink_light": "#FFF1F4",
        "yellow": "#FFF6B8",
        "yellow_light": "#FFF9DB",
        "blue_light": "#EDF7FF",
        "green": "#8ECF76",
        "blue": "#79AACF",
        "gold": "#E4B92C",
        "muted": "#596157",
        "white": "#FFFFFF",
    }

    def __init__(self, plugin):
        self.plugin = plugin
        self.output_dir = os.path.join("data", "plugin_data", "niuniu", "cards")
        os.makedirs(self.output_dir, exist_ok=True)
        self.font_path = self._find_font()

    async def result(self, event, text):
        content = str(text).strip() or "牛牛正在发呆，请稍后再试。"
        try:
            image_path = await asyncio.to_thread(self._render, content)
            return event.image_result(image_path)
        except Exception as error:
            self.plugin.context.logger.error(f"牛牛卡片生成失败: {error}")
            return event.plain_result("牛牛卡片生成失败，请稍后再试。")

    def _render(self, content):
        self._cleanup_old_cards()
        title, badge = self._card_meta(content)
        fonts = self._load_fonts()

        measure_image = Image.new("RGB", (self.WIDTH, 100), self.COLORS["paper"])
        measure_draw = ImageDraw.Draw(measure_image)
        blocks = self._layout_lines(measure_draw, content, fonts["body"])
        content_height = 54 + sum(block["height"] + 11 for block in blocks)
        card_height = self.HEADER_HEIGHT + max(136, content_height) + self.FOOTER_HEIGHT
        canvas_height = card_height + self.OUTER_PADDING * 2 + 10

        image = Image.new("RGB", (self.WIDTH, canvas_height), self.COLORS["pasture"])
        draw = ImageDraw.Draw(image)
        left = self.OUTER_PADDING
        top = self.OUTER_PADDING
        right = left + self.CARD_WIDTH
        bottom = top + card_height

        draw.rounded_rectangle((left + 10, top + 10, right + 10, bottom + 10), radius=8, fill="#B7C9B0")
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=8,
            fill=self.COLORS["paper"],
            outline=self.COLORS["ink"],
            width=3,
        )
        self._draw_spots(draw, left, top, right, bottom)
        self._draw_header(draw, left, top, right, title, badge, fonts)
        self._draw_content(draw, left, top + self.HEADER_HEIGHT, blocks, fonts)
        self._draw_footer(draw, left, right, bottom, fonts)

        with tempfile.NamedTemporaryFile(
            prefix="niuniu_card_",
            suffix=".png",
            dir=self.output_dir,
            delete=False,
        ) as output:
            output_path = output.name
        image.save(output_path, "PNG", optimize=True)
        return os.path.abspath(output_path)

    def _draw_header(self, draw, left, top, right, title, badge, fonts):
        header_bottom = top + self.HEADER_HEIGHT
        draw.rectangle((left + 2, top + 2, right - 2, header_bottom), fill=self.COLORS["pink"])
        draw.line((left, header_bottom, right, header_bottom), fill=self.COLORS["ink"], width=3)
        self._draw_cow(draw, left + 60, top + 56)

        text_left = left + 112
        draw.text(
            (text_left, top + 21),
            "NIUNIU PASTURE · 牛牛牧场",
            font=fonts["eyebrow"],
            fill=self.COLORS["muted"],
        )
        draw.text((text_left, top + 49), title, font=fonts["title"], fill=self.COLORS["ink"])

        badge_width = int(draw.textlength(badge, font=fonts["badge"])) + 24
        badge_left = right - badge_width - 22
        draw.rounded_rectangle(
            (badge_left, top + 39, right - 22, top + 75),
            radius=18,
            fill=self.COLORS["yellow"],
            outline=self.COLORS["ink"],
            width=2,
        )
        draw.text((badge_left + 12, top + 46), badge, font=fonts["badge"], fill=self.COLORS["ink"])

    def _draw_content(self, draw, left, content_top, blocks, fonts):
        current_y = content_top + 24
        box_left = left + 28
        box_right = left + self.CARD_WIDTH - 28
        for block in blocks:
            fill, accent = self._block_colors(block["kind"])
            box_bottom = current_y + block["height"]
            draw.rounded_rectangle((box_left, current_y, box_right, box_bottom), radius=6, fill=fill)
            draw.rectangle((box_left, current_y, box_left + 5, box_bottom), fill=accent)
            text_y = current_y + 10
            for line in block["lines"]:
                draw.text((box_left + 15, text_y), line, font=fonts["body"], fill=self.COLORS["ink"])
                text_y += 38
            current_y = box_bottom + 11

    def _draw_footer(self, draw, left, right, bottom, fonts):
        footer_top = bottom - self.FOOTER_HEIGHT
        draw.rectangle((left + 2, footer_top, right - 2, bottom - 2), fill=self.COLORS["grass"])
        draw.line((left, footer_top, right, footer_top), fill=self.COLORS["ink"], width=3)
        draw.text((left + 26, footer_top + 14), "今日也要元气满满", font=fonts["footer"], fill="#384136")
        draw.text(
            (right - 126, footer_top + 11),
            "✿  ·  ✿  ·  ✿",
            font=fonts["flower"],
            fill=self.COLORS["white"],
            stroke_width=1,
            stroke_fill="#67815D",
        )

    def _draw_cow(self, draw, center_x, center_y):
        ink = self.COLORS["ink"]
        draw.ellipse((center_x - 36, center_y - 34, center_x + 36, center_y + 34), fill="#FFFFFF", outline=ink, width=3)
        draw.ellipse((center_x - 45, center_y - 21, center_x - 28, center_y - 5), fill="#F2A9B9", outline=ink, width=2)
        draw.ellipse((center_x + 28, center_y - 21, center_x + 45, center_y - 5), fill="#F2A9B9", outline=ink, width=2)
        draw.polygon(((center_x - 25, center_y - 28), (center_x - 18, center_y - 43), (center_x - 10, center_y - 30)), fill="#FFF6B8", outline=ink)
        draw.polygon(((center_x + 10, center_y - 30), (center_x + 18, center_y - 43), (center_x + 25, center_y - 28)), fill="#FFF6B8", outline=ink)
        draw.ellipse((center_x - 28, center_y - 28, center_x - 7, center_y - 4), fill=ink)
        draw.ellipse((center_x + 12, center_y - 8, center_x + 29, center_y + 9), fill=ink)
        draw.ellipse((center_x - 16, center_y - 7, center_x - 10, center_y - 1), fill=ink)
        draw.ellipse((center_x + 8, center_y - 7, center_x + 14, center_y - 1), fill=ink)
        draw.rounded_rectangle((center_x - 21, center_y + 7, center_x + 21, center_y + 26), radius=9, fill="#F7B8C5", outline=ink, width=2)
        draw.ellipse((center_x - 10, center_y + 14, center_x - 6, center_y + 18), fill=ink)
        draw.ellipse((center_x + 6, center_y + 14, center_x + 10, center_y + 18), fill=ink)

    def _draw_spots(self, draw, left, top, right, bottom):
        spot = "#EEEDE8"
        draw.ellipse((left + 70, top - 24, left + 230, top + 62), fill=spot)
        draw.ellipse((right - 82, top + 138, right + 34, top + 220), fill=spot)
        draw.ellipse((left - 48, bottom - 152, left + 96, bottom - 72), fill=spot)

    def _layout_lines(self, draw, content, font):
        blocks = []
        clean_content = self._clean_symbols(content)
        for index, raw_line in enumerate(clean_content.splitlines()):
            value = raw_line.strip()
            if not value:
                continue
            wrapped = self._wrap_text(draw, value, font, 590)
            blocks.append(
                {
                    "lines": wrapped,
                    "height": max(54, len(wrapped) * 38 + 20),
                    "kind": self._line_kind(value, index),
                }
            )
        if not blocks:
            blocks.append({"lines": ["牛牛正在发呆，请稍后再试。"], "height": 58, "kind": "hint"})
        return blocks

    def _wrap_text(self, draw, text, font, max_width):
        lines = []
        current = ""
        for character in text:
            candidate = current + character
            if current and draw.textlength(candidate, font=font) > max_width:
                lines.append(current)
                current = character
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines or [text]

    def _line_kind(self, value, index):
        if re.match(r"^\d+[.、]", value):
            return "rank"
        if index == 0 or re.search(r"成功|获胜|战胜|喜报|排行榜|商城", value):
            return "major"
        if re.search(r"格式|例[:：]|等待|冷却|未启用|失败|错误|不足|不能", value):
            return "hint"
        return "normal"

    def _block_colors(self, kind):
        if kind == "major":
            return self.COLORS["pink_light"], "#EF8FA5"
        if kind == "rank":
            return self.COLORS["yellow_light"], self.COLORS["gold"]
        if kind == "hint":
            return self.COLORS["blue_light"], self.COLORS["blue"]
        return self.COLORS["white"], self.COLORS["green"]

    def _card_meta(self, content):
        rules = (
            (r"排行榜|TOP\s*10", "牛牛排行榜", "牧场风云榜"),
            (r"商城|购买|商品编号|金币不足", "牧场小铺", "牛牛商城"),
            (r"状态|当前长度|硬度|评价", "成长档案", "今日状态"),
            (r"比划|战胜|败给|获胜|势均力敌|长度减半", "牧场对决", "对战播报"),
            (r"注册", "新牛报到", "欢迎加入"),
            (r"菜单", "牛牛乐园", "功能菜单"),
            (r"开冲|冲够|起飞|飞机|油箱", "牧场活动", "活力记录"),
            (r"成功|获得|增加|茁壮成长", "今日喜报", "好运发生"),
            (r"失败|未启用|冷却|等待|不能|不足|错误|无效|休息", "温馨提示", "慢慢来"),
        )
        for pattern, title, badge in rules:
            if re.search(pattern, content, re.IGNORECASE):
                return title, badge
        return "牛牛播报", "牧场来信"

    def _load_fonts(self):
        return {
            "eyebrow": ImageFont.truetype(self.font_path, 17),
            "title": ImageFont.truetype(self.font_path, 34),
            "badge": ImageFont.truetype(self.font_path, 16),
            "body": ImageFont.truetype(self.font_path, 24),
            "footer": ImageFont.truetype(self.font_path, 16),
            "flower": ImageFont.truetype(self.font_path, 20),
        }

    def _find_font(self):
        candidates = (
            "/AstrBot/data/plugins/astrbot_plugin_touchi/NotoSansSC-Regular.ttf",
            "/AstrBot/data/plugin_data/astrbot_plugin_shoubanhua/fonts/NotoSansCJKsc-Regular.otf",
            "/AstrBot/data/plugins/astrbot_plugin_qzone/default_style/fonts/OPPOSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
        )
        for path in candidates:
            if os.path.exists(path):
                return path
        raise FileNotFoundError("未找到可用的卡片字体")

    def _cleanup_old_cards(self):
        cutoff = time.time() - 3600
        for filename in os.listdir(self.output_dir):
            if not filename.startswith("niuniu_card_") or not filename.endswith(".png"):
                continue
            path = os.path.join(self.output_dir, filename)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                continue

    def _clean_symbols(self, text):
        text = re.sub(r"[\U0001F000-\U0001FAFF]", "", text)
        replacements = {
            "➜": "→",
            "❌": "×",
            "✅": "√",
            "⚠": "注意",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return text.replace("\ufe0f", "")
