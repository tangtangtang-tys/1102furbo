#!/usr/bin/env python3
"""仅整理本地研究文件。标准库即可运行；不访问网络、手机或设备。"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, html, json, re, struct
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
ASSETS = OUT / 'assets'
ASSETS.mkdir(exist_ok=True)
H = html.escape

def link(path):
    return quote(str(path).replace('\\', '/'), safe='/._-')

def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

docs = sorted(p for p in ROOT.rglob('*.md') if OUT not in p.parents)
pngs = sorted((ROOT / 'screenshots').rglob('*.png'))
phase1 = [p for p in pngs if p.parent.name == '阶段1_基础档案']
source_index = ROOT / 'evidence/阶段1_基础档案_证据索引.md'
records = {}
for line in source_index.read_text(encoding='utf-8').splitlines():
    cells = [v.strip() for v in line.strip().strip('|').split('|')]
    if not cells or not re.fullmatch(r'E\d{2}', cells[0]):
        continue
    eid, filename = cells[0], cells[1].strip('`')
    if len(cells) == 5:
        date, caption, state = cells[2:]
    else:
        date, caption, state = '2026-10-31', cells[2], cells[3]
    records[eid] = dict(id=eid, filename=filename, date=date, caption=caption, state=state)

DATA = json.loads((OUT / '报告数据.json').read_text(encoding='utf-8'))
SECTIONS = DATA['sections']
BYSEC = {s['id']:s for s in SECTIONS}
BYE = DATA['evidence']
evidence = []
for p in phase1:
    eid = 'E' + p.name[:2]
    rec = records[eid].copy()
    meta = BYE[eid]
    rec.update(meta)
    rec.update(filename=p.name, title=p.stem[3:], path=str(p.relative_to(ROOT)), url=link('../' + str(p.relative_to(ROOT))), sha256=sha(p))
    rec['image_id'] = eid + ('-O' if '原始桌面' in p.name else '-V' if eid == 'E12' else '')
    if '原始桌面' in p.name:
        rec['caption'] = 'E12手机视口派生图对应的原始桌面截图；保留完整取证上下文。'
        rec['finding'] = '与E12-V属于同一次采集，不另计为独立功能验证。'
        rec['relation'] = 'E12-V 的原始桌面来源'
    elif eid == 'E12':
        rec['relation'] = '从E12-O裁出的完整手机视口；原图保留'
    else:
        rec['relation'] = '原始归档文件'
    raw = p.read_bytes()
    rec['width'], rec['height'] = struct.unpack('>II',raw[16:24])
    evidence.append(rec)

environment = []
for n,p in enumerate(p for p in pngs if p not in phase1):
    environment.append(dict(image_id=f'ENV{n+1:02}', title=p.stem, filename=p.name,
        path=str(p.relative_to(ROOT)),url=link('../'+str(p.relative_to(ROOT))),
        caption='阶段0环境截图。只作测评环境附件，不计入E01–E38产品证据。',
        sha256=sha(p),section='overview',date='2026-10-30',
        state='已通过实际界面确认', steps='阶段0环境检查时保存；本次未进行手机操作。',
        finding='用于说明桌面与手机镜像取证环境，不证明产品功能执行。'))

groups = defaultdict(list)
for e in evidence:
    groups[e['section']].append(e)
snapshot = {
 'generated_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
 'original_document_count':len(docs), 'all_original_png_count':len(pngs),
 'phase1_screenshot_count':len(phase1), 'environment_screenshot_count':len(environment),
 'evidence_group_count':len(records), 'associated_phase1_screenshots':len(evidence),
 'unclassified_screenshots':sum(e['section'] not in BYSEC for e in evidence),
 'completed_research_chapters':sum(s['status']=='已完成' for s in SECTIONS if s.get('research')),
 'research_chapters':sum(bool(s.get('research')) for s in SECTIONS),
 'chapter_count_rule':'研究章节为目录中产品基础档案至创新机会共11章；项目概览与证据索引不纳入。已完成指当前阶段文档与页面走查完成，不代表能力实测完成。',
 'documents':[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in docs],
 'original_screenshots':[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in pngs],
 'exact_duplicate_groups':[]
}
hashes = defaultdict(list)
for p in pngs: hashes[sha(p)].append(str(p.relative_to(ROOT)))
snapshot['exact_duplicate_groups']=[v for v in hashes.values() if len(v)>1]
manifest = OUT/'原始资料清单.json'
if manifest.exists():
    previous=json.loads(manifest.read_text(encoding='utf-8'))
    original={x['path']:x['sha256'] for x in previous.get('baseline_originals', previous['documents']+previous['original_screenshots'])}
    snapshot['original_integrity']=all((ROOT/p).exists() and sha(ROOT/p)==s for p,s in original.items())
else:
    snapshot['original_integrity']=True
    original={}
for x in snapshot['documents']+snapshot['original_screenshots']:
    original.setdefault(x['path'],x['sha256'])
snapshot['baseline_originals']=[dict(path=p,sha256=h) for p,h in original.items()]
dump(manifest,snapshot)
dump(OUT/'截图证据库.json',dict(research=evidence, environment=environment))

def badge(s):
    cls = 'verified' if s in ['已通过实际操作确认','已完成'] else 'observed' if s in ['已通过实际界面确认','部分记录','问题线索'] else 'inference' if s=='分析推测' else 'pending'
    if s=='用户提供的实机体验': cls='user'
    return f'<span class="badge {cls}">{H(s)}</span>'

def refs(ids):
    return ' '.join(f'<button class="ref" data-evidence="{H(e)}" title="查看 {H(e)} 证据">{H(e)}</button>' for e in ids)

def table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join(f'<th>{H(h)}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+c+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>'

def card(e):
    return f'''<article class="evidence-card" id="img-{H(e['image_id'])}" data-search="{H(e['image_id']+' '+e['title']+' '+e['caption'])}">
      <button class="image-button" data-image="{H(e['image_id'])}" aria-label="放大 {H(e['image_id'])} {H(e['title'])}"><img loading="lazy" decoding="async" src="{e['url']}" alt="{H(e['image_id']+' '+e['title'])}"><span class="image-action">点击放大 ↗</span></button>
      <div class="evidence-copy"><div class="evidence-kicker">{H(e['image_id'])} · {H(e['date'])}</div><h4>{H(e['title'])}</h4><p>{H(e['caption'])}</p>
      <details><summary>步骤、结论与原始位置</summary><dl><dt>所属模块</dt><dd>{H(BYSEC[e['section']]['title'])}</dd><dt>操作步骤</dt><dd>{H(e['steps'])}</dd><dt>结论边界</dt><dd>{H(e['finding'])}</dd><dt>证据状态</dt><dd>{H(e['state'])}</dd><dt>原始文件</dt><dd><a href="{e['url']}" target="_blank" rel="noopener">查看原图 ↗</a><code>{H(e['path'])}</code></dd></dl></details></div></article>'''

def gallery(sid):
    es=groups.get(sid,[])
    return ('<div class="gallery-heading"><h3>截图证据</h3><span>'+str(len(es))+' 张 · 保持原始比例</span></div><div class="evidence-grid">'+''.join(card(e) for e in es)+'</div>') if es else ''

def steps(items):
    return '<ol class="flow">'+''.join('<li><b>'+str(i+1)+'</b><span>'+H(v)+'</span></li>' for i,v in enumerate(items))+'</ol>'

blocks={}
blocks['overview']=f'''
 <div class="hero-top"><span class="eyebrow">COMPETITIVE PRODUCT RESEARCH · 阶段 1</span><span class="version">资料整理版 · 2026.10.31</span></div>
 <h1>Furbo Mini 360°<small>AI 宠物摄像机竞品体验测评</small></h1>
 <p class="lead">为公司规划新款 AI 宠物摄像机提供决策依据。将产品事实、App 交互和待验证能力放在同一份可追溯报告中。</p>
 <div class="scope-banner"><span class="status-dot"></span><div><b>当前范围：阶段1非直播页面研究已完成</b><p>设备离线由用户确认；实时直播预览暂停。本次仅整理已有资料，没有新增手机操作或设备动作。</p></div></div>
 <div class="stats"><div><strong>{snapshot['completed_research_chapters']}<small> / {snapshot['research_chapters']}</small></strong><span>已完成研究章节</span><em>按本报告11个研究章节统计</em></div><div><strong>{len(phase1)}</strong><span>阶段1实际截图</span><em>另有 {len(environment)} 张阶段0环境附图</em></div><div><strong>{len(records)}</strong><span>原始证据组</span><em>E01–E38；E12含原始/派生图</em></div><div><strong>{len(docs)}</strong><span>原有研究文档</span><em>阶段1四份档案均已交付</em></div></div>
 <p class="fineprint">统计口径：已完成为产品基础档案、App信息架构、首页体验三章的当前阶段记录；硬件能力清单虽已成文，硬件实测仍未完成。原始PNG共 {len(pngs)} 张，研究日期为 2026-10-30—2026-10-31（Asia/Shanghai）。</p>
 <div class="overview-cards">{''.join('<a class="summary-card" href="#'+c['target']+'"><span>'+H(c['label'])+'</span><h3>'+H(c['title'])+'</h3><p>'+H(c['text'])+'</p><b>阅读章节 →</b></a>' for c in DATA['overview_cards'])}</div>
 <div class="section-subtitle"><h3>研究进度与材料覆盖</h3><span>不以页面入口代替功能验收</span></div>
 {table(['研究章节','当前状态','完成范围 / 缺口'],[[f'<a href="#{s["id"]}">{H(s["title"])}</a>',badge(s['status']),H(s['scope'])] for s in SECTIONS if s.get('research')])}
 <div class="timeline">{''.join('<div><i></i><b>'+H(t[0])+'</b><p>'+H(t[1])+'</p></div>' for t in DATA['timeline'])}</div>
 <details class="panel"><summary>资料盘点、统计口径与环境附图</summary><p>原有文档覆盖项目管理、产品基础档案、首页体验、阶段1证据索引。AI能力、商业化、问题与机会尚无独立原始研究文档；本报告只做证据整理与明确标记的分析。</p>{table(['原始文档','分类'],[[f'<a href="{link("../"+str(p.relative_to(ROOT)))}" target="_blank" rel="noopener">{H(p.name)}</a>',H(p.parent.name)] for p in docs])}<p>阶段0环境图单独使用ENV编号，不增加产品证据组数。镜像连接和Mac验证问题不计作Furbo产品缺陷。</p><div class="evidence-grid">{''.join(card(e) for e in environment)}</div><h3>阶段1镜像环境证据</h3>{gallery('overview')}</details>
'''

blocks['profile']=f'''
 <p class="section-intro">已读取型号名称、版本、设备与宠物档案。信息来自当时界面快照，具体SKU与绑定身份仍待核验。</p>
 <div class="fact-cards">{''.join('<div><span>'+H(x['label'])+'</span><strong>'+H(x['value'])+'</strong><p>'+H(x['note'])+'</p>'+refs(x['evidence'])+'</div>' for x in DATA['facts'][:4])}</div>
 {table(['信息项','当前记录','结论状态','证据'],[[H(x['label']),H(x['value'])+'<small>'+H(x['note'])+'</small>',badge(x['state']),refs(x['evidence'])] for x in DATA['facts']])}
 <div class="note">设备名“客厅”与宠物名“yoyo”属于不同对象。当前账号可访问设备与历史内容，不足以判断主账号或共享绑定身份。</div>
'''+gallery('profile')

blocks['hardware']=f'''
 <p class="section-intro">本章是界面能力与硬件核验边界清单。没有形成硬件执行效果结论。</p>
 {table(['能力','实际证据','目前可确认','尚待验证','状态 / 证据'],[[H(x['name']),H(x['observed']),H(x['confirmed']),H(x['pending']),badge(x['state'])+refs(x['evidence'])] for x in DATA['hardware']])}
 <div class="note warning">设置中的1440p（2K）、自动追踪和投喂相关项目，只能证明配置或入口可见；不能证明本型号实际输出、跟随效果或具备投喂硬件。</div>
'''+gallery('hardware')

branches=[]
for b in DATA['architecture']:
    branches.append('<div class="tree-branch"><a class="tree-root" href="#'+b['target']+'">'+H(b['title'])+'<span>→</span></a><ul>'+''.join('<li><b>'+H(c['title'])+'</b><p>'+H(c['text'])+'</p>'+refs(c['evidence'])+'</li>' for c in b['children'])+'</ul></div>')
blocks['architecture']='''<p class="section-intro">四个一级导航承接设备状态、历史事件、日常摘要与管理。下方树状图可跳转到对应章节，证据编号可直接打开截图。</p><div class="tree">'''+''.join(branches)+'</div><h3>已确认的安全浏览流程</h3>'+''.join('<div class="flow-panel"><h4>'+H(f['title'])+'</h4>'+steps(f['steps'])+'<p>'+badge('已通过实际操作确认')+' '+refs(f['evidence'])+'</p></div>' for f in DATA['flows'])+'<div class="note">搜索框、更多菜单、顶部爪印和设备切换/新增路径未核验。账户、画中画、帮助仅完成进入与返回；未登出、未改开关、未联系客服。</div>'+gallery('architecture')

def walkthrough(image_id, title, items):
    e=next(x for x in evidence if x['image_id']==image_id)
    # 文字分析与章节内唯一原图卡片并列，避免重复加载同一证据图片。
    return '<div class="walkthrough">'+card(e)+'<div class="walkthrough-copy"><span class="eyebrow">界面与任务分析</span><h3>'+H(title)+'</h3>'+''.join('<div class="reading-point"><span>'+str(i+1).zfill(2)+'</span><div><h4>'+H(x['title'])+'</h4><p>'+H(x['text'])+'</p>'+badge(x['state'])+refs(x['evidence'])+'</div></div>' for i,x in enumerate(items))+'</div></div>'

blocks['home']='<p class="section-intro">首页同时呈现“现在的设备状态”和“此前发生的事件”。本阶段评价布局与可见反馈，不评价直播画质与AI准确率。</p>'+walkthrough('E30','摄像状态在上，AI消息在下',DATA['home_points'])+'<h3>AI展开与档案退出的实际路径</h3>'+steps(['首页上拖AI手柄','进入爱宠管家聊','左上向下箭头收起','返回首页'])+'<p>'+badge('已通过实际操作确认')+refs(['E29','E30'])+'</p><div class="note">顶部宠物头像实际进入毛孩子档案；设备切换路径仍待验证。只读查看档案后返回出现未保存提示，触发条件未知，未保存或删除档案。</div><div class="gallery-heading"><h3>首页与宠物档案截图</h3><span>历史在线外观与当前离线分别记录</span></div><div class="evidence-grid">'+''.join(card(e) for e in groups['home'] if e['image_id']!='E30')+'</div>'

blocks['live']='<div class="empty-status"><span class="badge pending">待测评 · 用户要求暂停</span><h3>实时直播效果暂不评价</h3><p>用户已确认设备离线断网。本报告保留暂停前的横屏连接布局与错误弹窗，用于识别型号和异常文案；不把进入页面算作直播成功。</p>'+badge('用户提供的实机体验')+refs(['E25','E26','E27'])+'</div><div class="split-notes"><div><h4>已观察</h4><p>首页连接中断；横屏连接页；失去网络连接的弹窗。</p>'+badge('已通过实际界面确认')+'</div><div><h4>未验证</h4><p>连接成功率、延迟、画质、流畅度、夜视与跨App小窗播放。</p>'+badge('待进一步验证')+'</div></div>'+gallery('live')
blocks['ptz']='<div class="empty-status"><span class="badge pending">待测评</span><h3>云台与自动追踪仅有名称和入口证据</h3><p>产品名称含360度，横屏页有方向图标，设置有自动宠物追踪。未进行转动或跟随操作。</p>'+refs(['E21','E26','E27'])+'</div>'+table(['已有材料','待实测内容','状态'],[['名称与方向/追踪入口','旋转角度、盲区、噪声、速度、跟丢与恢复',badge('待进一步验证')]])
blocks['interaction']='<div class="empty-status"><span class="badge pending">待测评</span><h3>远程语音、安抚和投喂没有设备执行结论</h3><p>界面可见音量、零食投掷声、助投小助手、智能安抚与麦克风样式入口。共享App入口不能证明本型号具备投喂硬件。本轮没有触发声音、动作或真实投喂。</p>'+refs(['E21','E26','E34'])+'</div>'+table(['方向','已有证据','缺口'],[['语音/音频','音量60%与麦克风样式入口','链路、回声、延迟与宠物反应均待验证'],['安抚','设置与历史视频分类可见','触发条件、执行内容和效果待验证'],['投喂','设置项目与图标可见','本型号硬件规格待核验；未授权真实投喂']])

blocks['ai']='<p class="section-intro">本章展示AI相关界面与内容组织方式。仅有入口、既有消息、历史内容和页面切换证据，没有本轮新提问或识别准确率测试。</p>'+table(['能力','界面/操作事实','可确认边界','核心缺口','状态 / 证据'],[[H(x['name']),H(x['observed']),H(x['confirmed']),H(x['pending']),badge(x['state'])+refs(x['evidence'])] for x in DATA['ai']])+walkthrough('E37','报告以日期组织，并解释当前等待状态',[dict(title='日期切换',text='选择31日后显示生成中，30日有Vlog与回忆精选。',state='已通过实际操作确认',evidence=['E36','E37']),dict(title='等待时间文案',text='界面提示晚上7—8点左右查看。没有验证实际准时生成。',state='已通过实际界面确认',evidence=['E37']),dict(title='内容可信度',text='AI页提醒核验信息；既有消息出现字面[emoji]。均不据此推断AI模型质量或根因。',state='已通过实际界面确认',evidence=['E29'])])+'<div class="gallery-heading"><h3>AI、智能通知与报告截图</h3><span>通知长页以连续分段留证</span></div><div class="evidence-grid">'+''.join(card(e) for e in groups['ai'] if e['image_id']!='E37')+'</div>'

blocks['business']='<p class="section-intro">已记录会员推广与方案日期，尚未进入独立交易详情或做免费账号对照。下表保留未知项，不反推付费限制。</p><div class="membership"><div><span class="eyebrow">菜单会员区 · E13</span><h3>Furbo爱宠管家－单机会员</h3><p>页面文字：“2027-01-19 过期” · “重新开通”</p>'+badge('已通过实际界面确认')+refs(['E13'])+'</div><div><b>价格、权益与续费状态</b><p>待核验。日期文案不足以判断自动续费、扣费状态或免费/付费边界。</p></div></div>'+table(['能力/权益','免费账号','当前账号可见内容','付费方案权益','证据'],[[H(r[0]),'待核验',H(r[1]),'待核验',refs(r[2])] for r in DATA['rights']])+'<div class="note">收藏夹的“永久保存”和“最多50片段”为界面文案；不能当作已测存储承诺或免费权益。未见付费墙也不能证明功能免费。</div><div class="crossrefs"><h3>相关原图</h3><a href="#img-E13">E13 菜单会员区与版本 ↗</a><a href="#img-E01">E01 历史首页“送7天免费时长”横幅 ↗</a><a href="#img-E35">E35 收藏夹空状态与容量文案 ↗</a></div>'

blocks['issues']='<p class="section-intro">以下为观察事项与问题线索，尚未完成复现及用户影响评估。严重程度只作本次材料整理的研究判断，不作为正式缺陷定级。</p><div class="issue-grid">'+''.join('<article class="issue"><div class="issue-meta"><span>'+H(x['id'])+'</span>'+badge(x['severity'])+'</div><h3>'+H(x['title'])+'</h3><p><b>实际观察</b>'+H(x['observation'])+'</p><p><b>用户影响（分析推测）</b>'+H(x['impact'])+'</p><p><b>确认边界</b>'+H(x['limit'])+'</p>'+badge(x['state'])+refs(x['evidence'])+'</article>' for x in DATA['issues'])+'</div><div class="note">设备断网是用户提供的测评条件，不据此认定设备网络稳定性缺陷。iPhone使用中和Mac验证锁定属于环境问题，不计为Furbo产品问题。</div>'
blocks['opportunities']='<p class="section-intro">仅从已有截图提出产品设计假设。痛点与机会均属于分析推测，尚无用户研究、效果对比或商业结果证明。</p><div class="opportunity-grid">'+''.join('<article class="opportunity"><span class="eyebrow">'+H(x['id'])+' · '+H(x['label'])+'</span><h3>'+H(x['title'])+'</h3><dl><dt>竞品现象</dt><dd>'+H(x['phenomenon'])+refs(x['evidence'])+'</dd><dt>可能的用户痛点</dt><dd>'+H(x['pain'])+'</dd><dt>产品机会</dt><dd>'+H(x['opportunity'])+'</dd><dt>待验证假设</dt><dd>'+H(x['hypothesis'])+'</dd></dl>'+badge('分析推测')+badge('待进一步验证')+'</article>' for x in DATA['opportunities'])+'</div>'

indexrows=[]
for e in evidence:
    indexrows.append([f'<button class="ref" data-image="{e["image_id"]}">{H(e["image_id"])}</button>',f'<a href="#img-{e["image_id"]}">{H(e["filename"])}</a><small>{e["width"]} × {e["height"]}</small>',H(BYSEC[e['section']]['title']),H(e['caption']),H(e['state']),f'<a href="{e["url"]}" target="_blank" rel="noopener">原图 ↗</a>'])
blocks['evidence']='<p class="section-intro">分析结论中的证据编号可打开对应图片。下表逐一对应39张阶段1文件；原图全部保留。E12-V与E12-O为同组证据的派生/原始关系。</p><div class="evidence-tools"><label for="evidence-search">检索证据</label><input id="evidence-search" type="search" placeholder="输入编号、页面或文件名" autocomplete="off"><label for="evidence-filter" class="sr-only">按章节筛选</label><select id="evidence-filter"><option value="">全部章节</option>'+''.join(f'<option value="{H(s["title"])}">{H(s["title"])}</option>' for s in SECTIONS if groups.get(s['id']))+'</select><span id="evidence-count">39 张 / 38 组</span></div><div id="evidence-table">'+table(['图片编号','原始文件','所属章节','截图说明','证据状态','原图'],indexrows)+'</div><div class="note"><b>待归类证据：0 张。</b>所有39张阶段1截图均能依原索引关联。环境证据E10、E11、E28放在项目概览中；不用于产品能力结论。原始文件中无字节完全相同的重复PNG。E12的两张图片不作两次独立测评计数。</div><h3>证据等级与来源边界</h3>'+table(['标记','使用规则'],[[badge(s),H(t)] for s,t in DATA['evidence_rules']])+ '<h3>下一轮资料缺口</h3><ul class="pending-list">'+''.join('<li>'+H(x)+'</li>' for x in DATA['missing'])+'</ul><p class="fineprint">本报告仅整理原有文档与实机截图；未新增官方或第三方资料。待补资料不得被当前布局与入口推定为已实现能力。</p>'

nav=''.join(f'<a href="#{s["id"]}" data-nav="{s["id"]}"><span>{str(i+1).zfill(2)}</span>{H(s["title"])}'+('<i title="待测评"></i>' if s['status'] in ['待测评','暂停测评'] else '')+'</a>' for i,s in enumerate(SECTIONS))
content=''.join(f'<section id="{s["id"]}" class="report-section"><div class="section-heading">'+('' if s['id']=='overview' else f'<div><span class="eyebrow">CHAPTER {str(i).zfill(2)}</span><h2>{H(s["title"])}</h2></div>{badge(s["status"])}')+f'</div>{blocks[s["id"]]}</section>' for i,s in enumerate(SECTIONS))
client_data={e['image_id']:e for e in evidence+environment}
client_json = json.dumps(client_data,ensure_ascii=False).replace('</', '<' + chr(92) + '/')
document=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light"><title>Furbo Mini 360°｜可视化竞品体验报告</title><link rel="stylesheet" href="assets/报告样式.css"></head>
<body><button class="mobile-nav" aria-expanded="false" aria-controls="sidebar">☰ 研究目录</button><aside id="sidebar"><a class="brand" href="#overview"><span class="brand-mark">F</span><div>Furbo Mini 360°<small>竞品体验研究 / RESEARCH</small></div></a><div class="sidebar-label">阅读目录 <span>13</span></div><nav>{nav}</nav><div class="sidebar-footer"><span class="status-dot"></span>阶段1 · 非直播页面档案<small>研究日期 2026.10.30—10.31</small><button id="print-report">打印 / 保存 PDF</button><a href="Furbo_Mini360_可视化报告使用说明.md">阅读与维护说明 ↗</a></div></aside>
<main><div class="topbar"><span>产品规划 / 竞品研究 / Furbo Mini 360°</span><span>证据驱动 · 当前阶段记录</span></div>{content}<footer>Furbo Mini 360° 竞品体验研究 · 资料整理日期 2026-10-31<br>保留原始文件；产品能力与商业结论以证据边界为准。报告待审核，不自动启动后续实机测评。</footer></main>
<dialog id="lightbox" aria-labelledby="lightbox-title"><div class="lightbox-bar"><div><span id="lightbox-kicker"></span><h2 id="lightbox-title"></h2></div><div class="lightbox-actions"><button id="zoom-image" aria-pressed="false">原始尺寸</button><a id="original-image" target="_blank" rel="noopener">查看原图 ↗</a><button id="close-lightbox" aria-label="关闭放大图">关闭 ×</button></div></div><div id="lightbox-stage"><img id="lightbox-image" alt=""></div><div class="lightbox-info"><p id="lightbox-caption"></p><div id="lightbox-details"></div></div><div class="lightbox-bottom"><button id="previous-image">← 上一张</button><span id="lightbox-position"></span><button id="next-image">下一张 →</button></div></dialog>
<script id="report-evidence-data" type="application/json">{client_json}</script><script src="assets/报告交互.js"></script></body></html>'''
(OUT/'Furbo_Mini360_可视化竞品体验报告.html').write_text(document,encoding='utf-8')

# Markdown：同一数据源，与HTML结论、状态和索引同步。
def md_refs(ids):return '、'.join(f'[{i}](证据索引.md#{i.lower()})' for i in ids)
def mdtable(headers,rows):
    clean=lambda v:str(v).replace('|','／').replace('\n','<br>')
    return '| '+' | '.join(headers)+' |\n| '+' | '.join('---' for _ in headers)+' |\n'+''.join('| '+' | '.join(clean(v) for v in r)+' |\n' for r in rows)+'\n'

md=['# Furbo Mini 360° 竞品体验测评总报告\n',
'研究主题：AI宠物摄像机竞品体验测评。目的：为公司规划新款AI宠物摄像机提供决策依据。\n\n研究日期：2026-10-30—2026-10-31（Asia/Shanghai）；整理日期：2026-10-31。\n\n**当前版本为阶段1资料整理版，不代表完整功能测评完成。设备离线由用户确认，实时直播预览暂停。本次没有新增手机操作、配置修改或设备动作。**\n',
'## 项目概览\n',
f'原有Markdown文档 **{len(docs)}份**；阶段1截图 **{len(phase1)}张 / {len(records)}组证据**；另有阶段0环境截图 **{len(environment)}张**，原始PNG合计 **{len(pngs)}张**。阶段1截图全部关联，待归类0张。E12有原始桌面和手机视口派生图，不能计作两次独立测评。\n\n'+snapshot['chapter_count_rule']+'\n',
mdtable(['章节','状态','完成范围 / 缺口'],[[s['title'],s['status'],s['scope']] for s in SECTIONS if s.get('research')]),
'### 已有材料与研究阶段\n\n阶段0环境初始化与阶段1四份档案已完成。四份档案为设备基础信息、App信息架构、硬件能力清单、首页体验测评；硬件清单属于界面证据整理，不能算作硬件实测完成。其余阶段按下表保留研究状态。\n',
mdtable(['阶段','状态'],DATA['timeline']),
'### 证据规则\n',mdtable(['标记','边界'],DATA['evidence_rules']),
'## 产品基础档案\n',mdtable(['项目','记录','边界','状态','证据'],[[x['label'],x['value'],x['note'],x['state'],md_refs(x['evidence'])] for x in DATA['facts']]),
'## 硬件能力\n\n**部分记录，待实测。**\n',mdtable(['能力','实际证据','可确认','缺口','状态','证据'],[[x['name'],x['observed'],x['confirmed'],x['pending'],x['state'],md_refs(x['evidence'])] for x in DATA['hardware']]),
'## App信息架构\n']
for b in DATA['architecture']:
    md.append('### '+b['title']+'\n\n')
    for c in b['children']:md.append('- **'+c['title']+'**：'+c['text']+' '+md_refs(c['evidence'])+'\n')
    md.append('\n')
md.append('### 已确认流程\n\n')
for f in DATA['flows']:md.append('**'+f['title']+'**：'+' → '.join(f['steps'])+'。已通过实际操作确认，'+md_refs(f['evidence'])+'。\n\n')
md.append('## 首页体验\n\n')
for x in DATA['home_points']:md.append('### '+x['title']+'\n\n'+x['text']+' **'+x['state']+'**；'+md_refs(x['evidence'])+'。\n\n')
md.extend(['## 实时视频体验\n\n**待测评，按用户要求暂停。** 原有E26/E27只证明横屏连接布局、型号与错误文案，不证明直播成功；不评价画质、延迟、连接成功率或夜视效果。'+md_refs(['E25','E26','E27'])+'。\n',
'## 云台与自动追踪\n\n**待测评。** 仅有360度名称、方向图标与追踪入口证据；未进行转动、跟随、盲区或恢复测试。'+md_refs(['E21','E26','E27'])+'。\n',
'## 远程互动与投喂\n\n**待测评。** 音量、安抚、麦克风样式和零食设置入口可见，未进行声音或动作操作。共用App的投喂入口不能证明本型号有投喂硬件。'+md_refs(['E21','E26','E34'])+'。\n',
'## AI能力\n\n**部分界面记录，准确率与效果待测评。**\n',mdtable(['能力','事实','边界','缺口','状态','证据'],[[x['name'],x['observed'],x['confirmed'],x['pending'],x['state'],md_refs(x['evidence'])] for x in DATA['ai']]),
'## 订阅与商业化\n\n**部分记录，价格与权益待核验。** 菜单显示Furbo爱宠管家－单机会员、“2027-01-19过期”、重新开通及推广卡片；不据此判断自动续费或扣费状态。'+md_refs(['E13'])+'。\n',mdtable(['能力/权益','免费账号','当前账号所见','付费方案权益','证据'],[[r[0],'待核验',r[1],'待核验',md_refs(r[2])] for r in DATA['rights']]),
'## 竞品问题\n\n以下为观察事项与问题线索，未完成复现及影响评估；严重程度未定级。\n'])
for x in DATA['issues']:md.append('### '+x['id']+' '+x['title']+'\n\n- 实际观察：'+x['observation']+'\n- 可能影响（分析推测）：'+x['impact']+'\n- 严重程度：'+x['severity']+'\n- 确认边界：'+x['limit']+'\n- 证据状态：'+x['state']+'；'+md_refs(x['evidence'])+'\n\n')
md.append('## 创新机会\n\n以下为基于现有证据的分析推测和待验证假设，不代表用户痛点或产品效果已验证。\n\n')
for x in DATA['opportunities']:md.append('### '+x['id']+' '+x['title']+'\n\n- 竞品现象：'+x['phenomenon']+' '+md_refs(x['evidence'])+'\n- 可能痛点：'+x['pain']+'\n- 产品机会：'+x['opportunity']+'\n- 待验证假设：'+x['hypothesis']+'\n- 状态：分析推测 / 待进一步验证。\n\n')
md.append('## 待补资料与下一轮验证\n\n'+''.join('- '+x+'\n' for x in DATA['missing'])+'\n**整理完成后等待用户审核，不自动开展后续实机测评。**\n\n## 原始材料\n\n'+''.join('- ['+p.name+']('+link('../'+str(p.relative_to(ROOT)))+')\n' for p in docs)+'\n## 截图证据附录\n\n以下逐图列出操作、说明、结论、状态和来源。原图维持原始比例；HTML提供点击放大。\n\n')
for s in SECTIONS:
    es=groups.get(s['id'],[])
    if not es:continue
    md.append('### '+s['title']+'\n\n')
    for e in es:
        md.append('#### '+e['image_id']+' '+e['title']+'\n\n![ '+e['image_id']+' '+e['title']+']('+e['url']+')\n\n- 图片说明：'+e['caption']+'\n- 操作步骤：'+e['steps']+'\n- 结论边界：'+e['finding']+'\n- 证据状态：'+e['state']+'\n- 原始位置：['+e['path']+']('+e['url']+')\n\n')
(OUT/'Furbo_Mini360_竞品体验测评总报告.md').write_text('\n'.join(md),encoding='utf-8')

idx=['# 证据索引\n','研究日期：2026-10-30—2026-10-31。来源为原始阶段1证据索引。38组证据关联39张PNG；E12-O / E12-V为同组的原始/派生关系。另列2张阶段0环境附件，不纳入产品证据组计数。\n','## 按章节分类\n']
idx.append(mdtable(['章节','截图数','证据'],[[s['title'],len(groups[s['id']]),'、'.join(dict.fromkeys(e['id'] for e in groups[s['id']]))] for s in SECTIONS if groups.get(s['id'])]))
idx.append('## 完整图片索引\n'+mdtable(['证据 / 图片编号','图片文件名','所属章节','图片说明','对应测评记录','证据状态'],[[f'[{e["image_id"]}](#{e["id"].lower()})',f'[{e["filename"]}]({e["url"]})',BYSEC[e['section']]['title'],e['caption'],e['record'],e['state']] for e in evidence]))
for eid in records:
    es=[e for e in evidence if e['id']==eid]
    idx.append('## '+eid+'\n\n')
    for e in es:
        idx.append('### '+e['image_id']+' · '+e['title']+'\n\n- 图片：['+e['filename']+']('+e['url']+')\n- 所属章节：'+BYSEC[e['section']]['title']+'\n- 日期：'+e['date']+'\n- 图片说明：'+e['caption']+'\n- 操作步骤：'+e['steps']+'\n- 对应测评记录：'+e['record']+'\n- 测评结论/边界：'+e['finding']+'\n- 证据状态：'+e['state']+'\n- 原始文件：`'+e['path']+'`\n- 原始/派生关系：'+e['relation']+'\n- SHA-256：`'+e['sha256']+'`\n\n')
idx.append('## 阶段0环境附图\n\n'+mdtable(['编号','原始文件','说明'],[[e['image_id'],f'[{e["filename"]}]({e["url"]})',e['caption']] for e in environment])+'\n## 待归类证据\n\n0张。所有阶段1图片均有原始索引对应；未将环境阻塞当作产品缺陷。\n')
(OUT/'证据索引.md').write_text('\n'.join(idx),encoding='utf-8')
print(json.dumps({k:snapshot[k] for k in ['original_document_count','phase1_screenshot_count','environment_screenshot_count','evidence_group_count','completed_research_chapters','research_chapters','unclassified_screenshots','original_integrity','exact_duplicate_groups']},ensure_ascii=False))
