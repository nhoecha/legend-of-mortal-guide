"""Render Mortal condition data (ConditionResultItem / StatValueReference) as readable text."""
import struct
try:
    from flag_ko import FLAG_KO
except Exception:
    FLAG_KO = {}


STAT_KO = {
 '體力':'체력','內力':'내력','輕功':'경공','銀兩':'은자','魅力':'매력','學問':'학문',
 '心理衛生':'심상','命運':'운명','性情':'성정','處世':'처세','修養':'수양','道德':'도덕',
 '嘴力':'구력','門派規模':'문파 규모','門派名聲':'명성','門派人數':'문인','向心力':'단합',
 '鍛造':'단조','毒藥':'연단','行動次數':'행동력','個人貢獻度':'공헌도','廚藝':'요리',
 '抗毒':'항독','抗麻':'항마','稱號':'칭호','愛人':'마음에 둔 사람',
 '額外行動次數_1':'추가 행동1','額外行動次數_2':'추가 행동2','額外行動次數_3':'추가 행동3',
 '娘化':'낭화','陰陽內功':'음양','防禦':'방어','變心':'변심','武學點數':'무학',
 '全武學點數':'누적 무학','門派資產':'문파 자산','門派貢獻':'문파 공헌',
 '全鍛造點數':'누적 단조','全毒藥點數':'누적 연단','全貢獻度':'누적 공헌',
 '武功刀劍':'도검','武功暗器':'암기','武功拳掌':'권장','武功腿法':'각법','武功奇門':'기문',
 '武功軟兵器':'연병기','武功槍棍':'창곤','武功內功':'내공',
 '儒學':'유교','道學':'도학','佛學':'불교','戰役預設血量':'문인 체력',
 '攻擊爆擊':'폭발','暗器爆擊':'암기 폭발',
}
import re as _re

def _idpart(name, prefixes):
    for p in prefixes:
        m = _re.match(p, name or '')
        if m:
            return m.group(1)
    return None

REL_KO = {
 '小師妹':'소사매','大師兄':'대사형','二師兄':'이사형','三師兄':'삼사형','四師兄':'사사형',
 '掌門人':'장문인','瑞杏':'서행','葉雲舟':'엽운주','葉雲裳':'엽운상','樊嘯天':'번소천',
 '萬里鵬程':'만리붕정','劉顎':'유악','龍湘':'용상','龍淵':'용연','石公遠':'석공원',
 '南宮深':'남궁심','南宮淺':'남궁천','尹志平':'윤지평','福韞':'복운','虞小梅':'우소매',
 '夏侯蘭':'하후란','郁竹':'욱죽','魏菊':'위국','上官螢':'상관형','王二壯':'왕이장',
 '趙逵':'조규','丹霞子':'단하자','申屠龍':'신도룡','車軒轅':'차헌원','宋悲':'송비',
 '解無塵':'해무진','李富貴':'이부귀','夏靈犀':'하영서','瑞笙':'서생',
 '葉雲啾_1':'엽운추','葉雲啾_2':'엽운추',
}

CMP = ['==', '!=', '<', '<=', '>', '>=']
LOGIC = ['그리고', '또는']


def enum_values(w, typename):
    """enum type -> {value: name} using the Constant table"""
    m, ti = w.find(typename)
    if m is None:
        return {}
    out = {}
    # map field row -> constant value
    consts = {}
    for i in range(1, m.nrows(0x0b) + 1):
        r = m.row(0x0b, i)
        t, idx = m.coded('HasConstant', r['Parent'])
        if t != 4:
            continue
        blob = m.blobv(r['Value'])
        et = r['Type']
        try:
            if et == 0x08:
                consts[idx] = struct.unpack_from('<i', blob, 0)[0]
            elif et == 0x09:
                consts[idx] = struct.unpack_from('<I', blob, 0)[0]
            elif et in (0x04, 0x05):
                consts[idx] = blob[0]
            elif et in (0x06, 0x07):
                consts[idx] = struct.unpack_from('<h', blob, 0)[0]
        except Exception:
            pass
    for nm, flags, sig, fi in m.fields_of(ti):
        if flags & 0x0010 and fi in consts:
            out[consts[fi]] = nm
    return out


class Renderer:
    def __init__(self, g):
        self.g = g
        w = g.w
        self.E = {n: enum_values(w, 'Mortal.Core.' + n) for n in
                  ['StatCheckType', 'GameStatType', 'RelationshipStatType', 'StatCompareType',
                   'LogicOperatorType', 'GameStatPropertyType', 'StatGroupType']}
        self.E['DicePropertyType'] = enum_values(w, 'Mortal.Story.DicePropertyType')
        # Chinese character name -> character key (for Character/<key> localization)
        self.charkey = {}
        for ref, o in g.all_of('StoryMappingItem', 'OBB.Framework.Data.StoryMappingItem'):
            if o and o.get('Key'):
                self.charkey.setdefault(o['Key'], o.get('Value'))

    def ko(self, zh, kind='Stat'):
        """try localization for a Chinese stat/character name"""
        for k in (f'{kind}/Name/{zh}', f'Name/{zh}', zh):
            v = self.g.t(k)
            if v:
                return v
        return zh

    def stat_name(self, ref):
        o = self.g.obj(ref, 'Mortal.Core.GameStat')
        if not o:
            return '?'
        t = self.E['GameStatType'].get(o.get('_type'), o.get('_name') or '?')
        return STAT_KO.get(t, t)

    def rel_name(self, ref):
        o = self.g.obj(ref, 'Mortal.Core.RelationshipStat')
        if not o:
            return '?'
        zh = self.E['RelationshipStatType'].get(o.get('_type'), o.get('_note') or '?')
        if zh in REL_KO:
            return REL_KO[zh]
        key = self.charkey.get(zh)
        if key:
            ko = self.g.t(f'Character/{key}')
            if ko and ko != '？？？':
                return ko
        return zh

    def asset_ko(self, ref, kind):
        """talent/book/misc/special asset -> Korean name via id in the asset name"""
        nm = self.g.name(ref) or ''
        pats = {
            'talent': (r'天賦_(\d+)', 'PlayerTalent/Name/'),
            'book': (r'Book(\d+)', 'Book/Name/'),
            'misc': (r'Misc(\d+)', 'Misc/Name/'),
            'special': (r'Special(\d+)', 'Special/Name/'),
        }
        pat, pre = pats[kind]
        import re
        m = re.search(pat, nm)
        if m:
            ko = self.g.t(pre + m.group(1))
            if ko:
                return ko
        return nm.split('_')[-1] or nm or '?'

    @staticmethod
    def gametime_ko(name):
        """第三年三月上旬 -> 3년차 3월 상순"""
        import re
        NUM = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
        def cn(s):
            if not s: return None
            if s.startswith('十'): return 10 + NUM.get(s[1:], 0) if len(s) > 1 else 10
            if len(s) == 1: return NUM.get(s)
            if '十' in s:
                a, _, b = s.partition('十')
                return NUM.get(a, 1) * 10 + (NUM.get(b, 0) if b else 0)
            return NUM.get(s)
        m = re.match(r'第([一二三四五六七八九十]+)年(?:([一二三四五六七八九十]+)月)?(上旬|中旬|下旬)?', name or '')
        if not m:
            return name
        y, mo, st = cn(m.group(1)), cn(m.group(2)), m.group(3)
        out = f'{y}년차'
        if mo: out += f' {mo}월'
        if st: out += ' ' + {'上旬':'상순','中旬':'중순','下旬':'하순'}[st]
        return out

    def flag_name(self, ref):
        o = self.g.obj(ref, 'Mortal.Core.FlagData')
        if not o:
            return '?'
        nm = o.get('__name') or '?'
        ko = FLAG_KO.get(nm) or self.g.t(f'Flag/Name/{nm}')
        if ko:
            return ko
        note = (o.get('_devNote') or '').strip()
        return f'{nm} ({note})' if note else nm

    def svr(self, f, obj):
        """StatValueReference dict -> text"""
        if obj is None:
            return '?'
        ct = self.E['StatCheckType'].get(obj.get('_checkType'), str(obj.get('_checkType')))
        R = lambda p: self.g.resolve(f, p)
        neg = '-' if obj.get('_negative') else ''
        if ct == '常數':
            return f"{neg}{obj.get('_constant')}"
        if ct == '角色數值':
            return f"{neg}[{self.stat_name(R(obj['_stat']))}]"
        if ct == '好感度':
            return f"{neg}[{self.rel_name(R(obj['_relationship']))} 호감도]"
        if ct == '旗標':
            return f"{neg}[플래그 {self.flag_name(R(obj['_flag']))}]"
        if ct == '隨機值':
            return f"난수({obj.get('_randomMin')}~{obj.get('_randomMax')})"
        if ct == '書籍':
            return f"[비급 {self.asset_ko(R(obj['_book']), 'book')}]"
        if ct == '雜物':
            return f"[잡물 {self.asset_ko(R(obj['_misc']), 'misc')}]"
        if ct == '貴重品':
            return f"[귀중품 {self.asset_ko(R(obj['_specialItem']), 'special')}]"
        if ct == '技能':
            return f"[기술 {self.asset_ko(R(obj['_talentData']), 'talent')}]"
        if ct == '秘笈等級':
            return f"[비급 등급 {self.asset_ko(R(obj['_book']), 'book')}]"
        if ct == '遊戲時間':
            return f"[시점 {self.gametime_ko(self.g.name(R(obj['_gameTime'])) or '?')}]"
        if ct == '數值群組':
            return self.group(R(obj['_statGroup']))
        if ct == '已開發項目' or ct == '開發項目等級':
            return f"[개발 {self.g.name(R(obj['_upgradeItemData'])) or '?'}]"
        if ct == '書籍精通':
            return f"[서적숙련 {self.g.name(R(obj['_bookCollection'])) or '?'}]"
        if ct == '風雲史':
            lr = R(obj['_libraryAchieve'])
            return f"[도감달성 {self.g.name(lr) or '?'}]"
        if ct == '條件設定':
            return f"({self.condition_data(R(obj['_condition']))})"
        return f'<{ct}>'

    def group(self, ref):
        """StatGroupVariable -> text"""
        if not ref:
            return '?'
        o = self.g.obj(ref, 'Mortal.Core.StatGroupVariable')
        if not o or '_value' not in o:
            return '?'
        f = ref[0]
        parts = [self.svr(f, v) for v in o['_value']]
        gt = self.E['StatGroupType'].get(o.get('_groupType'), '')
        joiner = {'加總': ' + ', '相乘': ' * ', '最大值': ' max ', '最小值': ' min '}.get(gt, ' + ')
        if len(parts) == 1:
            return parts[0]
        return '(' + joiner.join(parts) + ')'

    def compare_item(self, f, it):
        op = CMP[it.get('_compareOp', 0)] if it.get('_compareOp', 0) < len(CMP) else '?'
        a = self.group(self.g.resolve(f, it['_value1']))
        b = self.group(self.g.resolve(f, it['_value2']))
        return f'{a} {op} {b}'

    def condition_item(self, f, ci):
        """ConditionResultItem -> text"""
        if not ci:
            return ''
        items = ci.get('_items') or []
        if not items:
            return ''
        j = f" {LOGIC[ci.get('_logicOp', 0)]} "
        return j.join(self.compare_item(f, it) for it in items)

    def condition_data(self, ref):
        """ConditionResultData -> text"""
        if not ref:
            return ''
        o = self.g.obj(ref, 'Mortal.Core.ConditionResultData')
        if not o:
            return ''
        f = ref[0]
        items = o.get('_items') or []
        return ' / '.join(x for x in (self.condition_item(f, i) for i in items) if x)
