"""Request bodies for the established HTTP API."""

from pydantic import BaseModel

class JoinBody(BaseModel):
    name: str
    room_code: str  # 4 位数字房间号,须与说书人设定一致



class SitBody(BaseModel):
    seat: int



class ConfigBody(BaseModel):
    script: str
    player_count: int
    balloonist_version: str | None = None
    balloonist_outsider_delta: int | None = None



class PasswordBody(BaseModel):
    password: str



class ManualAssignBody(BaseModel):
    assignments: list[dict]  # [{"seat": int, "role": str}, ...]
    bluffs: list[str] | None = None  # 伪装:3 个不在场好角色 id(可选,缺省自动抽取)
    fakes: list[dict] | None = None  # 认知覆盖:[{"seat": int, "role": str}],疯子/酒鬼看到的假身份



class FakeBody(BaseModel):
    seat: int
    role: str | None = None  # 玩家看到的假角色;None 表示清除认知覆盖
    minions: list[int] | None = None  # 疯子:以为的爪牙座位(说书人选,不一定是真的)
    bluffs: list[str] | None = None  # 疯子:3 个伪装(说书人选,不一定是恶魔的真伪装)



class MarkerBody(BaseModel):
    seat: int
    marker: str  # poisoned | drunk | mad | role-change | team-change
    on: bool
    role: str | None = None  # role-change 时必填:变成的角色 id
    team: str | None = None  # team-change 时必填:新阵营 good/evil
    about: str | None = None  # mad 时必填:疯狂宣称的善良角色 id



class NominationBody(BaseModel):
    nominator: int | str  # 座位号或旅行者 id("t1")
    nominee: int | str



class VoteBody(BaseModel):
    seat: int | str  # 座位号或旅行者 id("t1")



class NomineeBody(BaseModel):
    nominee: int | str  # 被提名者:座位号或旅行者 id("t1")



class DayStageBody(BaseModel):
    stage: str  # talk 公聊私聊 | nom 提名阶段(说书人控节奏)



class KillBody(BaseModel):
    seat: int  # 刀杀目标座位



class NightChoiceBody(BaseModel):
    targets: list[int]  # 夜晚选择的目标座位(数量按角色配置)
    char: str | None = None  # 麻脸巫婆:变身后的角色 id(必须不在场)



class TransformBody(BaseModel):
    seat: int  # 麻脸巫婆的座位(说书人确认其变身)



class NightReplyBody(BaseModel):
    seat: int  # 回复给哪个座位
    text: str  # 回复内容(占卜师:有恶魔/无恶魔 等)
    role: str | None = None  # 无选择直接发信息时的角色标注(教父首夜信息等)



class RedHerringBody(BaseModel):
    seat: int | None = None  # 宿敌座位;None = 清除



class WishBody(BaseModel):
    wish: str | None = None  # 许愿内容(善良/邪恶或自定义);None/空 = 清除



class ResolveBody(BaseModel):
    passed: bool  # 结票:通过 → 待处决(天黑结算最多票者);旅行者通过 → 当场流放



class TravelerAddBody(BaseModel):
    name: str  # 旅行者名字(说书人直接添加,无手机关联)



class TravelerAssignBody(BaseModel):
    id: str  # 旅行者 id(t1..)
    role: str  # 旅行者角色 id(官方旅行者池)
    align: str | None = None  # good/evil,缺省保持原值(新增时默认 good)



class TravelerExileBody(BaseModel):
    id: str
    exiled: bool = True  # False = 撤销流放



class TravelerAliveBody(BaseModel):
    id: str



class GotoBody(BaseModel):
    idx: int



class SentinelBody(BaseModel):
    value: int  # -1 / 0 / +1 / 2:哨兵对外来者数量的调整(0 = 关,2 = 在场但不调整)



class RoomBody(BaseModel):
    code: str  # 4 位数字房间号



class EndBody(BaseModel):
    winner: str | None = None  # good/evil;None = 撤销结算



class ReviewMarkBody(BaseModel):
    seat: int  # 回复接收者座位
    night: int  # 第几夜
    wrong: bool = True  # True 标注错误 / False 撤销标注



class FabledBody(BaseModel):
    id: str  # 传奇角色 id
    on: bool = True  # True 勾选在场 / False 移除



class ChatCreateBody(BaseModel):
    invitees: list  # 被邀请者:座位号(int)/旅行者 id(str)/说书人 "st"



class ChatInviteBody(BaseModel):
    accept: bool  # 接受邀请



class ChatApproveBody(BaseModel):
    who: int | str  # 申请者
    approve: bool  # 同意



class ChatSendBody(BaseModel):
    text: str



class SeatKillBody(BaseModel):
    target: int  # 刀杀目标座位



class SeatChoiceBody(BaseModel):
    targets: list[int]
    char: str | None = None  # 麻脸巫婆/洗脑师的角色选择
