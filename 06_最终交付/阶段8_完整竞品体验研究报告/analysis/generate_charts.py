"""阶段8用户评价图表生成脚本。
数据源是同目录上级的 user_reviews_coded.csv；本阶段没有可核验逐条评论样本。
图表使用可读的数据状态面板，不用平台总评价数填充硬件统计。
"""
from pathlib import Path
import csv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CHARTS = ROOT / "charts"
CHARTS.mkdir(exist_ok=True)
with (ROOT / "user_reviews_coded.csv").open(encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

font_path = "/System/Library/Fonts/Hiragino Sans GB.ttc"
try:
    title_font = ImageFont.truetype(font_path, 34)
    heading_font = ImageFont.truetype(font_path, 25)
    body_font = ImageFont.truetype(font_path, 20)
    small_font = ImageFont.truetype(font_path, 17)
except OSError:
    title_font = heading_font = body_font = small_font = ImageFont.load_default()

BG = "#f7f9fc"
INK = "#172033"
MUTED = "#667085"
BLUE = "#2057a6"
LINE = "#dbe3ef"
WARN = "#b45309"
GREEN = "#19724a"


def panel(draw, box, title, body, state, state_color=WARN):
    draw.rounded_rectangle(box, radius=14, fill="white", outline=LINE, width=2)
    x1, y1, x2, y2 = box
    draw.text((x1 + 22, y1 + 20), title, font=heading_font, fill=INK)
    draw.text((x1 + 22, y1 + 64), body, font=small_font, fill=MUTED)
    pill_w = max(108, draw.textlength(state, font=small_font) + 28)
    draw.rounded_rectangle((x1 + 22, y2 - 48, x1 + 22 + pill_w, y2 - 18), radius=15, fill="#fff3d6")
    draw.text((x1 + 36, y2 - 42), state, font=small_font, fill=state_color)


def state_chart(title, detail):
    image = Image.new("RGB", (1400, 760), BG)
    draw = ImageDraw.Draw(image)
    draw.text((70, 58), title, font=title_font, fill=INK)
    draw.text((70, 112), "逐条评论样本为0；App级聚合评分不进入硬件评论统计", font=body_font, fill=MUTED)
    draw.rounded_rectangle((70, 175, 1330, 290), radius=16, fill="#eef4ff", outline="#c8dafa", width=2)
    draw.text((105, 205), "本阶段可核验逐条评论", font=heading_font, fill=BLUE)
    draw.text((105, 247), "0 条", font=title_font, fill=BLUE)
    draw.text((360, 220), detail, font=body_font, fill=INK)
    draw.text((360, 258), "不能据此计算硬件评分分布、主题提及率、情感比例或时间趋势。", font=small_font, fill=MUTED)
    panel(draw, (70, 335, 475, 570), "已有数据", "Furbo App聚合评分4.78465/5\n评分数5,591，独立口径", "App聚合可用", GREEN)
    panel(draw, (500, 335, 905, 570), "仍缺数据", "Mini 360°逐条评论文本\n星级、主题、情感、日期", "不可计算", "#b91c1c")
    panel(draw, (930, 335, 1330, 570), "补齐条件", "取得可去重、可确认型号\n并保留原文与日期的样本", "后续补齐", WARN)
    draw.text((70, 665), "数据限制：不使用平台总评论数代替逐条样本，不把App评分写成硬件评分。", font=small_font, fill=MUTED)
    return image


titles = [
    ("各平台实际采集样本分布", "Apple聚合指标已取得；逐条评论接口和其他来源尚未形成样本。"),
    ("用户评分分布", "App聚合评分单独记录；Mini 360°逐条星级分布暂不能计算。"),
    ("用户情感分布", "没有评论原文，不能对正面、中性、负面或混合情感编码。"),
    ("用户关注主题排名", "没有可编码评论文本，不能计算主题提及数或排名。"),
    ("各主题情感对比", "没有逐条样本，不能比较不同主题的情感方向。"),
    ("用户主要痛点 TOP10", "没有逐条样本，不能将体验问题排序为用户痛点。"),
    ("用户正面体验 TOP10", "没有逐条样本，不能将App或媒体描述当作用户正面评价。"),
    ("用户评价时间趋势", "没有可核验发布日期样本，不能形成月度或季度趋势。"),
]
for index, (title, detail) in enumerate(titles, 1):
    state_chart(title, detail).save(CHARTS / f"图{index:02d}.png")
