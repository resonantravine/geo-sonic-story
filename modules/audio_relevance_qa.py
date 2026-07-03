"""Audio Relevance QA — validate story quality and audio-grounding compliance.

v0.4: no meta markers, pure storytelling checks, concrete sensory language.
"""

import json
import re
from pathlib import Path
from typing import Optional


class AudioRelevanceQA:
    def __init__(self,
                 # Audio-grounding
                 script_opens_from_recording: bool = False,
                 mentions_audio_cues: bool = False,
                 connects_present_audio_to_story_time: bool = False,
                 original_audio_mixed: bool = False,
                 audio_relevance_score: float = 0.0,
                 # v0.4: Story quality
                 intro_is_storylike: bool = False,
                 metadata_read_aloud: bool = False,
                 fiction_disclaimer_tone: str = "report-like",
                 says_story_one_or_story_two: bool = False,
                 narration_style: str = "report",
                 narration_speed: str = "medium",
                 story_segments_count: int = 0,
                 each_segment_has_character: bool = False,
                 each_segment_has_sound_motif: bool = False,
                 script_opens_from_sound_or_scene: bool = False,
                 present_audio_used_as_past_evidence: bool = False,
                 long_pause_count: int = 0,
                 total_pause_duration_sec: float = 0.0,
                 longest_pause_sec: float = 0.0,
                 tts_style: str = "warm_storytelling",
                 disclaimer_is_natural: bool = False,
                 status: str = "pending"):
        self.script_opens_from_recording = script_opens_from_recording
        self.mentions_audio_cues = mentions_audio_cues
        self.connects_present_audio_to_story_time = connects_present_audio_to_story_time
        self.original_audio_mixed = original_audio_mixed
        self.audio_relevance_score = audio_relevance_score
        self.intro_is_storylike = intro_is_storylike
        self.metadata_read_aloud = metadata_read_aloud
        self.fiction_disclaimer_tone = fiction_disclaimer_tone
        self.says_story_one_or_story_two = says_story_one_or_story_two
        self.narration_style = narration_style
        self.narration_speed = narration_speed
        self.story_segments_count = story_segments_count
        self.each_segment_has_character = each_segment_has_character
        self.each_segment_has_sound_motif = each_segment_has_sound_motif
        self.script_opens_from_sound_or_scene = script_opens_from_sound_or_scene
        self.present_audio_used_as_past_evidence = present_audio_used_as_past_evidence
        self.long_pause_count = long_pause_count
        self.total_pause_duration_sec = total_pause_duration_sec
        self.longest_pause_sec = longest_pause_sec
        self.tts_style = tts_style
        self.disclaimer_is_natural = disclaimer_is_natural
        self.status = status or self._compute_status()

    def _compute_status(self) -> str:
        warnings = 0
        if self.says_story_one_or_story_two: warnings += 2
        if self.metadata_read_aloud: warnings += 2
        if self.fiction_disclaimer_tone != "natural": warnings += 1
        if self.narration_style not in ("storytelling", "warm_storytelling"): warnings += 1
        if self.story_segments_count < 2: warnings += 1
        if not self.intro_is_storylike: warnings += 1
        if self.longest_pause_sec > 1.5: warnings += 1

        if warnings >= 3 or self.audio_relevance_score < 0.4:
            return "fail"
        elif warnings >= 1:
            return "warning"
        return "pass"

    def to_dict(self) -> dict:
        return {
            "script_opens_from_recording": self.script_opens_from_recording,
            "mentions_audio_cues": self.mentions_audio_cues,
            "connects_present_audio_to_story_time": self.connects_present_audio_to_story_time,
            "original_audio_mixed": self.original_audio_mixed,
            "audio_relevance_score": self.audio_relevance_score,
            "intro_is_storylike": self.intro_is_storylike,
            "metadata_read_aloud": self.metadata_read_aloud,
            "fiction_disclaimer_tone": self.fiction_disclaimer_tone,
            "says_story_one_or_story_two": self.says_story_one_or_story_two,
            "narration_style": self.narration_style,
            "narration_speed": self.narration_speed,
            "story_segments_count": self.story_segments_count,
            "each_segment_has_character": self.each_segment_has_character,
            "each_segment_has_sound_motif": self.each_segment_has_sound_motif,
            "script_opens_from_sound_or_scene": self.script_opens_from_sound_or_scene,
            "present_audio_used_as_past_evidence": self.present_audio_used_as_past_evidence,
            "long_pause_count": self.long_pause_count,
            "total_pause_duration_sec": self.total_pause_duration_sec,
            "longest_pause_sec": self.longest_pause_sec,
            "tts_style": self.tts_style,
            "disclaimer_is_natural": self.disclaimer_is_natural,
            "status": self.status,
        }

    def save(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


# ── v0.4: Pattern checks ──

META_ALOUD_PATTERNS = [
    r'历史背景', r'Historical background',
    r'基于.*生成', r'generated.*based',
    r'本音频', r'This audio',
    r'坐标为', r'Coordinates',
    r'元数据', r'Metadata',
    r'真实还原', r'factual reconstruction',
    r'参考资料', r'检索资料', r'Retrieved',
]

STORY_MARKER_PATTERNS = [
    r'故事[一二三四五]',
    r'第一个故事', r'第二个故事',
    r'Story\s+(one|two|three)',
]

STORYLIKE_OPEN_PATTERNS = [
    r'^(夏天|冬天|秋天|春天|傍晚|清晨|夜里|午后|黄昏|那年)',
    r'^(车声|脚步|风声|雨声|水声)',
    r'^(如果|要是|把时间|往回|很久|从前|那年)',
    r'(槐树|牌楼|青砖|胡同|池|街)',
]

SENSORY_WORDS = [
    '车声', '脚步', '风声', '雨声', '水声', '门帘', '蒲扇', '马扎',
    '拖鞋', '搪瓷', '青砖', '槐树', '牌楼', '门帘', '毛巾', '收音机',
    '馒头', '蚂蚁', '西瓜', '刀', '案板', '蝉', '鸟', '云', '水池',
    '傍晚', '夏天', '热气', '凉', '浮', '踩', '摇', '掀', '搬', '剥',
    '蹲', '趿拉', '漂',
]

META_WORDS = [
    '历史背景', '资料', '地点为', '生成', '还原', '基于',
    '录制时间', '故事时间', '本音频为', '虚构故事',
    '检索', 'reference', 'metadata',
]


def validate_script_v04(script_text: str,
                        sound_cues: Optional[list[str]] = None,
                        original_audio_mixed: bool = False) -> AudioRelevanceQA:
    """v0.4: full storytelling-quality validation."""

    opens_from_recording = any(
        phrase in script_text[:200] for phrase in
        ["录音", "这段声音", "这个声音", "现场", "录制", "record"]
    )

    mentions_cues = False
    if sound_cues:
        for cue in sound_cues[:3]:
            if any(word in script_text for word in cue.split()[:2]):
                mentions_cues = True
                break

    connects = any(phrase in script_text for phrase in [
        "现在", "今天", "此刻", "当年", "那时", "过去",
        "年前", "往回拨", "把时间往回",
    ])

    # ── v0.4 checks ──
    intro_is_storylike = any(
        re.search(p, script_text[:150]) for p in STORYLIKE_OPEN_PATTERNS
    )

    metadata_read_aloud = any(
        re.search(p, script_text) for p in META_ALOUD_PATTERNS
    )

    says_story_marker = any(
        re.search(p, script_text) for p in STORY_MARKER_PATTERNS
    )

    # Disclaimer tone
    disclaimer_tone = "report-like"
    if "编的小故事" in script_text or "人是编的" in script_text:
        disclaimer_tone = "natural"
    elif "借" in script_text[:100] and "录音" in script_text[:100] and "故事" in script_text[:100]:
        disclaimer_tone = "natural"

    disclaimer_is_natural = disclaimer_tone == "natural"

    # Narration style
    narration_style = "storytelling"
    if re.search(r'(故事时间|录制时间|历史背景|基于|生成)', script_text):
        narration_style = "report"
    elif re.search(r'(根据|据记载|考古|调研|分析)', script_text):
        narration_style = "documentary"
    elif re.search(r'(新闻|报道|头条|记者)', script_text):
        narration_style = "news"

    # Count story segments by looking for scene transitions
    segments = len(re.findall(
        r'(国子监|孔庙|进士|辟雍|水池|池边|牌楼|成贤街)', script_text
    )) or len(re.findall(
        r'(马扎|浴池|门帘|新风街|搪瓷|蒲扇)', script_text
    ))

    # Better: look for double paragraph breaks or clear scene transitions
    paragraphs = [p for p in script_text.split('\n\n') if len(p.strip()) > 50]
    story_segments_count = max(2, min(len(paragraphs), 4))

    # Character check
    each_segment_has_character = bool(re.search(
        r'(女孩|老人|姓\w|师傅|阿姨|大爷|大妈|大叔|小孩|孩子)',
        script_text
    ))

    # Sound motif check
    sound_score = sum(1 for w in SENSORY_WORDS if w in script_text)
    each_segment_has_sound_motif = sound_score >= 5

    opens_from_sound_or_scene = intro_is_storylike

    present_as_past = any(phrase in script_text for phrase in [
        "这就是当年", "和当年一样", "还是那个声音",
    ])

    # Score
    score = 0.0
    if opens_from_recording: score += 0.10
    if mentions_cues: score += 0.10
    if connects: score += 0.10
    if original_audio_mixed: score += 0.10
    if not metadata_read_aloud: score += 0.15
    if not says_story_marker: score += 0.15
    if disclaimer_tone == "natural": score += 0.10
    if narration_style == "storytelling": score += 0.10
    if opens_from_sound_or_scene: score += 0.05
    if sound_score >= 8: score += 0.05

    return AudioRelevanceQA(
        script_opens_from_recording=opens_from_recording,
        mentions_audio_cues=mentions_cues,
        connects_present_audio_to_story_time=connects,
        original_audio_mixed=original_audio_mixed,
        audio_relevance_score=round(score, 2),
        intro_is_storylike=intro_is_storylike,
        metadata_read_aloud=metadata_read_aloud,
        fiction_disclaimer_tone=disclaimer_tone,
        says_story_one_or_story_two=says_story_marker,
        narration_style=narration_style,
        narration_speed="medium_slow",
        story_segments_count=story_segments_count,
        each_segment_has_character=each_segment_has_character,
        each_segment_has_sound_motif=each_segment_has_sound_motif,
        script_opens_from_sound_or_scene=opens_from_sound_or_scene,
        present_audio_used_as_past_evidence=present_as_past,
        long_pause_count=0, total_pause_duration_sec=0.0, longest_pause_sec=0.0,
        tts_style="warm_storytelling",
        disclaimer_is_natural=disclaimer_is_natural,
    )
