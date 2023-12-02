import shared_pb2 as _shared_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FIXED_FRAME_GROUP(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FIXED_FRAME_GROUP_OUTFIT_IDLE: _ClassVar[FIXED_FRAME_GROUP]
    FIXED_FRAME_GROUP_OUTFIT_MOVING: _ClassVar[FIXED_FRAME_GROUP]
    FIXED_FRAME_GROUP_OBJECT_INITIAL: _ClassVar[FIXED_FRAME_GROUP]
FIXED_FRAME_GROUP_OUTFIT_IDLE: FIXED_FRAME_GROUP
FIXED_FRAME_GROUP_OUTFIT_MOVING: FIXED_FRAME_GROUP
FIXED_FRAME_GROUP_OBJECT_INITIAL: FIXED_FRAME_GROUP

class Appearances(_message.Message):
    __slots__ = ("object", "outfit", "effect", "missile", "special_meaning_appearance_ids")
    OBJECT_FIELD_NUMBER: _ClassVar[int]
    OUTFIT_FIELD_NUMBER: _ClassVar[int]
    EFFECT_FIELD_NUMBER: _ClassVar[int]
    MISSILE_FIELD_NUMBER: _ClassVar[int]
    SPECIAL_MEANING_APPEARANCE_IDS_FIELD_NUMBER: _ClassVar[int]
    object: _containers.RepeatedCompositeFieldContainer[Appearance]
    outfit: _containers.RepeatedCompositeFieldContainer[Appearance]
    effect: _containers.RepeatedCompositeFieldContainer[Appearance]
    missile: _containers.RepeatedCompositeFieldContainer[Appearance]
    special_meaning_appearance_ids: SpecialMeaningAppearanceIds
    def __init__(self, object: _Optional[_Iterable[_Union[Appearance, _Mapping]]] = ..., outfit: _Optional[_Iterable[_Union[Appearance, _Mapping]]] = ..., effect: _Optional[_Iterable[_Union[Appearance, _Mapping]]] = ..., missile: _Optional[_Iterable[_Union[Appearance, _Mapping]]] = ..., special_meaning_appearance_ids: _Optional[_Union[SpecialMeaningAppearanceIds, _Mapping]] = ...) -> None: ...

class SpritePhase(_message.Message):
    __slots__ = ("duration_min", "duration_max")
    DURATION_MIN_FIELD_NUMBER: _ClassVar[int]
    DURATION_MAX_FIELD_NUMBER: _ClassVar[int]
    duration_min: int
    duration_max: int
    def __init__(self, duration_min: _Optional[int] = ..., duration_max: _Optional[int] = ...) -> None: ...

class SpriteAnimation(_message.Message):
    __slots__ = ("default_start_phase", "synchronized", "random_start_phase", "loop_type", "loop_count", "sprite_phase")
    DEFAULT_START_PHASE_FIELD_NUMBER: _ClassVar[int]
    SYNCHRONIZED_FIELD_NUMBER: _ClassVar[int]
    RANDOM_START_PHASE_FIELD_NUMBER: _ClassVar[int]
    LOOP_TYPE_FIELD_NUMBER: _ClassVar[int]
    LOOP_COUNT_FIELD_NUMBER: _ClassVar[int]
    SPRITE_PHASE_FIELD_NUMBER: _ClassVar[int]
    default_start_phase: int
    synchronized: bool
    random_start_phase: bool
    loop_type: _shared_pb2.ANIMATION_LOOP_TYPE
    loop_count: int
    sprite_phase: _containers.RepeatedCompositeFieldContainer[SpritePhase]
    def __init__(self, default_start_phase: _Optional[int] = ..., synchronized: bool = ..., random_start_phase: bool = ..., loop_type: _Optional[_Union[_shared_pb2.ANIMATION_LOOP_TYPE, str]] = ..., loop_count: _Optional[int] = ..., sprite_phase: _Optional[_Iterable[_Union[SpritePhase, _Mapping]]] = ...) -> None: ...

class Box(_message.Message):
    __slots__ = ("x", "y", "width", "height")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    x: int
    y: int
    width: int
    height: int
    def __init__(self, x: _Optional[int] = ..., y: _Optional[int] = ..., width: _Optional[int] = ..., height: _Optional[int] = ...) -> None: ...

class SpriteInfo(_message.Message):
    __slots__ = ("pattern_width", "pattern_height", "pattern_depth", "layers", "sprite_id", "bounding_square", "animation", "is_opaque", "bounding_box_per_direction")
    PATTERN_WIDTH_FIELD_NUMBER: _ClassVar[int]
    PATTERN_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    PATTERN_DEPTH_FIELD_NUMBER: _ClassVar[int]
    LAYERS_FIELD_NUMBER: _ClassVar[int]
    SPRITE_ID_FIELD_NUMBER: _ClassVar[int]
    BOUNDING_SQUARE_FIELD_NUMBER: _ClassVar[int]
    ANIMATION_FIELD_NUMBER: _ClassVar[int]
    IS_OPAQUE_FIELD_NUMBER: _ClassVar[int]
    BOUNDING_BOX_PER_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    pattern_width: int
    pattern_height: int
    pattern_depth: int
    layers: int
    sprite_id: _containers.RepeatedScalarFieldContainer[int]
    bounding_square: int
    animation: SpriteAnimation
    is_opaque: bool
    bounding_box_per_direction: _containers.RepeatedCompositeFieldContainer[Box]
    def __init__(self, pattern_width: _Optional[int] = ..., pattern_height: _Optional[int] = ..., pattern_depth: _Optional[int] = ..., layers: _Optional[int] = ..., sprite_id: _Optional[_Iterable[int]] = ..., bounding_square: _Optional[int] = ..., animation: _Optional[_Union[SpriteAnimation, _Mapping]] = ..., is_opaque: bool = ..., bounding_box_per_direction: _Optional[_Iterable[_Union[Box, _Mapping]]] = ...) -> None: ...

class FrameGroup(_message.Message):
    __slots__ = ("fixed_frame_group", "id", "sprite_info")
    FIXED_FRAME_GROUP_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    SPRITE_INFO_FIELD_NUMBER: _ClassVar[int]
    fixed_frame_group: FIXED_FRAME_GROUP
    id: int
    sprite_info: SpriteInfo
    def __init__(self, fixed_frame_group: _Optional[_Union[FIXED_FRAME_GROUP, str]] = ..., id: _Optional[int] = ..., sprite_info: _Optional[_Union[SpriteInfo, _Mapping]] = ...) -> None: ...

class Appearance(_message.Message):
    __slots__ = ("id", "frame_group", "flags", "name", "description")
    ID_FIELD_NUMBER: _ClassVar[int]
    FRAME_GROUP_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    id: int
    frame_group: _containers.RepeatedCompositeFieldContainer[FrameGroup]
    flags: AppearanceFlags
    name: str
    description: str
    def __init__(self, id: _Optional[int] = ..., frame_group: _Optional[_Iterable[_Union[FrameGroup, _Mapping]]] = ..., flags: _Optional[_Union[AppearanceFlags, _Mapping]] = ..., name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class AppearanceFlags(_message.Message):
    __slots__ = ("bank", "clip", "bottom", "top", "container", "cumulative", "usable", "forceuse", "multiuse", "write", "write_once", "liquidpool", "unpass", "unmove", "unsight", "avoid", "no_movement_animation", "take", "liquidcontainer", "hang", "hook", "rotate", "light", "dont_hide", "translucent", "shift", "height", "lying_object", "animate_always", "automap", "lenshelp", "fullbank", "ignore_look", "clothes", "default_action", "market", "wrap", "unwrap", "topeffect", "npcsaledata", "changedtoexpire", "corpse", "player_corpse", "cyclopediaitem", "ammo", "show_off_socket", "reportable", "upgradeclassification", "reverse_addons_east", "reverse_addons_west", "reverse_addons_south", "reverse_addons_north", "wearout", "clockexpire", "expire", "expirestop", "deco_item_kit")
    BANK_FIELD_NUMBER: _ClassVar[int]
    CLIP_FIELD_NUMBER: _ClassVar[int]
    BOTTOM_FIELD_NUMBER: _ClassVar[int]
    TOP_FIELD_NUMBER: _ClassVar[int]
    CONTAINER_FIELD_NUMBER: _ClassVar[int]
    CUMULATIVE_FIELD_NUMBER: _ClassVar[int]
    USABLE_FIELD_NUMBER: _ClassVar[int]
    FORCEUSE_FIELD_NUMBER: _ClassVar[int]
    MULTIUSE_FIELD_NUMBER: _ClassVar[int]
    WRITE_FIELD_NUMBER: _ClassVar[int]
    WRITE_ONCE_FIELD_NUMBER: _ClassVar[int]
    LIQUIDPOOL_FIELD_NUMBER: _ClassVar[int]
    UNPASS_FIELD_NUMBER: _ClassVar[int]
    UNMOVE_FIELD_NUMBER: _ClassVar[int]
    UNSIGHT_FIELD_NUMBER: _ClassVar[int]
    AVOID_FIELD_NUMBER: _ClassVar[int]
    NO_MOVEMENT_ANIMATION_FIELD_NUMBER: _ClassVar[int]
    TAKE_FIELD_NUMBER: _ClassVar[int]
    LIQUIDCONTAINER_FIELD_NUMBER: _ClassVar[int]
    HANG_FIELD_NUMBER: _ClassVar[int]
    HOOK_FIELD_NUMBER: _ClassVar[int]
    ROTATE_FIELD_NUMBER: _ClassVar[int]
    LIGHT_FIELD_NUMBER: _ClassVar[int]
    DONT_HIDE_FIELD_NUMBER: _ClassVar[int]
    TRANSLUCENT_FIELD_NUMBER: _ClassVar[int]
    SHIFT_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    LYING_OBJECT_FIELD_NUMBER: _ClassVar[int]
    ANIMATE_ALWAYS_FIELD_NUMBER: _ClassVar[int]
    AUTOMAP_FIELD_NUMBER: _ClassVar[int]
    LENSHELP_FIELD_NUMBER: _ClassVar[int]
    FULLBANK_FIELD_NUMBER: _ClassVar[int]
    IGNORE_LOOK_FIELD_NUMBER: _ClassVar[int]
    CLOTHES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ACTION_FIELD_NUMBER: _ClassVar[int]
    MARKET_FIELD_NUMBER: _ClassVar[int]
    WRAP_FIELD_NUMBER: _ClassVar[int]
    UNWRAP_FIELD_NUMBER: _ClassVar[int]
    TOPEFFECT_FIELD_NUMBER: _ClassVar[int]
    NPCSALEDATA_FIELD_NUMBER: _ClassVar[int]
    CHANGEDTOEXPIRE_FIELD_NUMBER: _ClassVar[int]
    CORPSE_FIELD_NUMBER: _ClassVar[int]
    PLAYER_CORPSE_FIELD_NUMBER: _ClassVar[int]
    CYCLOPEDIAITEM_FIELD_NUMBER: _ClassVar[int]
    AMMO_FIELD_NUMBER: _ClassVar[int]
    SHOW_OFF_SOCKET_FIELD_NUMBER: _ClassVar[int]
    REPORTABLE_FIELD_NUMBER: _ClassVar[int]
    UPGRADECLASSIFICATION_FIELD_NUMBER: _ClassVar[int]
    REVERSE_ADDONS_EAST_FIELD_NUMBER: _ClassVar[int]
    REVERSE_ADDONS_WEST_FIELD_NUMBER: _ClassVar[int]
    REVERSE_ADDONS_SOUTH_FIELD_NUMBER: _ClassVar[int]
    REVERSE_ADDONS_NORTH_FIELD_NUMBER: _ClassVar[int]
    WEAROUT_FIELD_NUMBER: _ClassVar[int]
    CLOCKEXPIRE_FIELD_NUMBER: _ClassVar[int]
    EXPIRE_FIELD_NUMBER: _ClassVar[int]
    EXPIRESTOP_FIELD_NUMBER: _ClassVar[int]
    DECO_ITEM_KIT_FIELD_NUMBER: _ClassVar[int]
    bank: AppearanceFlagBank
    clip: bool
    bottom: bool
    top: bool
    container: bool
    cumulative: bool
    usable: bool
    forceuse: bool
    multiuse: bool
    write: AppearanceFlagWrite
    write_once: AppearanceFlagWriteOnce
    liquidpool: bool
    unpass: bool
    unmove: bool
    unsight: bool
    avoid: bool
    no_movement_animation: bool
    take: bool
    liquidcontainer: bool
    hang: bool
    hook: AppearanceFlagHook
    rotate: bool
    light: AppearanceFlagLight
    dont_hide: bool
    translucent: bool
    shift: AppearanceFlagShift
    height: AppearanceFlagHeight
    lying_object: bool
    animate_always: bool
    automap: AppearanceFlagAutomap
    lenshelp: AppearanceFlagLenshelp
    fullbank: bool
    ignore_look: bool
    clothes: AppearanceFlagClothes
    default_action: AppearanceFlagDefaultAction
    market: AppearanceFlagMarket
    wrap: bool
    unwrap: bool
    topeffect: bool
    npcsaledata: _containers.RepeatedCompositeFieldContainer[AppearanceFlagNPC]
    changedtoexpire: AppearanceFlagChangedToExpire
    corpse: bool
    player_corpse: bool
    cyclopediaitem: AppearanceFlagCyclopedia
    ammo: bool
    show_off_socket: bool
    reportable: bool
    upgradeclassification: AppearanceFlagUpgradeClassification
    reverse_addons_east: bool
    reverse_addons_west: bool
    reverse_addons_south: bool
    reverse_addons_north: bool
    wearout: bool
    clockexpire: bool
    expire: bool
    expirestop: bool
    deco_item_kit: bool
    def __init__(self, bank: _Optional[_Union[AppearanceFlagBank, _Mapping]] = ..., clip: bool = ..., bottom: bool = ..., top: bool = ..., container: bool = ..., cumulative: bool = ..., usable: bool = ..., forceuse: bool = ..., multiuse: bool = ..., write: _Optional[_Union[AppearanceFlagWrite, _Mapping]] = ..., write_once: _Optional[_Union[AppearanceFlagWriteOnce, _Mapping]] = ..., liquidpool: bool = ..., unpass: bool = ..., unmove: bool = ..., unsight: bool = ..., avoid: bool = ..., no_movement_animation: bool = ..., take: bool = ..., liquidcontainer: bool = ..., hang: bool = ..., hook: _Optional[_Union[AppearanceFlagHook, _Mapping]] = ..., rotate: bool = ..., light: _Optional[_Union[AppearanceFlagLight, _Mapping]] = ..., dont_hide: bool = ..., translucent: bool = ..., shift: _Optional[_Union[AppearanceFlagShift, _Mapping]] = ..., height: _Optional[_Union[AppearanceFlagHeight, _Mapping]] = ..., lying_object: bool = ..., animate_always: bool = ..., automap: _Optional[_Union[AppearanceFlagAutomap, _Mapping]] = ..., lenshelp: _Optional[_Union[AppearanceFlagLenshelp, _Mapping]] = ..., fullbank: bool = ..., ignore_look: bool = ..., clothes: _Optional[_Union[AppearanceFlagClothes, _Mapping]] = ..., default_action: _Optional[_Union[AppearanceFlagDefaultAction, _Mapping]] = ..., market: _Optional[_Union[AppearanceFlagMarket, _Mapping]] = ..., wrap: bool = ..., unwrap: bool = ..., topeffect: bool = ..., npcsaledata: _Optional[_Iterable[_Union[AppearanceFlagNPC, _Mapping]]] = ..., changedtoexpire: _Optional[_Union[AppearanceFlagChangedToExpire, _Mapping]] = ..., corpse: bool = ..., player_corpse: bool = ..., cyclopediaitem: _Optional[_Union[AppearanceFlagCyclopedia, _Mapping]] = ..., ammo: bool = ..., show_off_socket: bool = ..., reportable: bool = ..., upgradeclassification: _Optional[_Union[AppearanceFlagUpgradeClassification, _Mapping]] = ..., reverse_addons_east: bool = ..., reverse_addons_west: bool = ..., reverse_addons_south: bool = ..., reverse_addons_north: bool = ..., wearout: bool = ..., clockexpire: bool = ..., expire: bool = ..., expirestop: bool = ..., deco_item_kit: bool = ...) -> None: ...

class AppearanceFlagBank(_message.Message):
    __slots__ = ("waypoints",)
    WAYPOINTS_FIELD_NUMBER: _ClassVar[int]
    waypoints: int
    def __init__(self, waypoints: _Optional[int] = ...) -> None: ...

class AppearanceFlagWrite(_message.Message):
    __slots__ = ("max_text_length",)
    MAX_TEXT_LENGTH_FIELD_NUMBER: _ClassVar[int]
    max_text_length: int
    def __init__(self, max_text_length: _Optional[int] = ...) -> None: ...

class AppearanceFlagWriteOnce(_message.Message):
    __slots__ = ("max_text_length_once",)
    MAX_TEXT_LENGTH_ONCE_FIELD_NUMBER: _ClassVar[int]
    max_text_length_once: int
    def __init__(self, max_text_length_once: _Optional[int] = ...) -> None: ...

class AppearanceFlagLight(_message.Message):
    __slots__ = ("brightness", "color")
    BRIGHTNESS_FIELD_NUMBER: _ClassVar[int]
    COLOR_FIELD_NUMBER: _ClassVar[int]
    brightness: int
    color: int
    def __init__(self, brightness: _Optional[int] = ..., color: _Optional[int] = ...) -> None: ...

class AppearanceFlagHeight(_message.Message):
    __slots__ = ("elevation",)
    ELEVATION_FIELD_NUMBER: _ClassVar[int]
    elevation: int
    def __init__(self, elevation: _Optional[int] = ...) -> None: ...

class AppearanceFlagShift(_message.Message):
    __slots__ = ("x", "y")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: int
    y: int
    def __init__(self, x: _Optional[int] = ..., y: _Optional[int] = ...) -> None: ...

class AppearanceFlagClothes(_message.Message):
    __slots__ = ("slot",)
    SLOT_FIELD_NUMBER: _ClassVar[int]
    slot: int
    def __init__(self, slot: _Optional[int] = ...) -> None: ...

class AppearanceFlagDefaultAction(_message.Message):
    __slots__ = ("action",)
    ACTION_FIELD_NUMBER: _ClassVar[int]
    action: _shared_pb2.PLAYER_ACTION
    def __init__(self, action: _Optional[_Union[_shared_pb2.PLAYER_ACTION, str]] = ...) -> None: ...

class AppearanceFlagMarket(_message.Message):
    __slots__ = ("category", "trade_as_object_id", "show_as_object_id", "restrict_to_vocation", "minimum_level")
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TRADE_AS_OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    SHOW_AS_OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    RESTRICT_TO_VOCATION_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_LEVEL_FIELD_NUMBER: _ClassVar[int]
    category: _shared_pb2.ITEM_CATEGORY
    trade_as_object_id: int
    show_as_object_id: int
    restrict_to_vocation: _containers.RepeatedScalarFieldContainer[_shared_pb2.VOCATION]
    minimum_level: int
    def __init__(self, category: _Optional[_Union[_shared_pb2.ITEM_CATEGORY, str]] = ..., trade_as_object_id: _Optional[int] = ..., show_as_object_id: _Optional[int] = ..., restrict_to_vocation: _Optional[_Iterable[_Union[_shared_pb2.VOCATION, str]]] = ..., minimum_level: _Optional[int] = ...) -> None: ...

class AppearanceFlagNPC(_message.Message):
    __slots__ = ("name", "location", "sale_price", "buy_price", "currency_object_type_id", "currency_quest_flag_display_name")
    NAME_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    SALE_PRICE_FIELD_NUMBER: _ClassVar[int]
    BUY_PRICE_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_OBJECT_TYPE_ID_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_QUEST_FLAG_DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    location: str
    sale_price: int
    buy_price: int
    currency_object_type_id: int
    currency_quest_flag_display_name: str
    def __init__(self, name: _Optional[str] = ..., location: _Optional[str] = ..., sale_price: _Optional[int] = ..., buy_price: _Optional[int] = ..., currency_object_type_id: _Optional[int] = ..., currency_quest_flag_display_name: _Optional[str] = ...) -> None: ...

class AppearanceFlagAutomap(_message.Message):
    __slots__ = ("color",)
    COLOR_FIELD_NUMBER: _ClassVar[int]
    color: int
    def __init__(self, color: _Optional[int] = ...) -> None: ...

class AppearanceFlagHook(_message.Message):
    __slots__ = ("direction",)
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    direction: _shared_pb2.HOOK_TYPE
    def __init__(self, direction: _Optional[_Union[_shared_pb2.HOOK_TYPE, str]] = ...) -> None: ...

class AppearanceFlagLenshelp(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class AppearanceFlagChangedToExpire(_message.Message):
    __slots__ = ("former_object_typeid",)
    FORMER_OBJECT_TYPEID_FIELD_NUMBER: _ClassVar[int]
    former_object_typeid: int
    def __init__(self, former_object_typeid: _Optional[int] = ...) -> None: ...

class AppearanceFlagCyclopedia(_message.Message):
    __slots__ = ("cyclopedia_type",)
    CYCLOPEDIA_TYPE_FIELD_NUMBER: _ClassVar[int]
    cyclopedia_type: int
    def __init__(self, cyclopedia_type: _Optional[int] = ...) -> None: ...

class AppearanceFlagUpgradeClassification(_message.Message):
    __slots__ = ("upgrade_classification",)
    UPGRADE_CLASSIFICATION_FIELD_NUMBER: _ClassVar[int]
    upgrade_classification: int
    def __init__(self, upgrade_classification: _Optional[int] = ...) -> None: ...

class SpecialMeaningAppearanceIds(_message.Message):
    __slots__ = ("gold_coin_id", "platinum_coin_id", "crystal_coin_id", "tibia_coin_id", "stamped_letter_id", "supply_stash_id", "standard_reward_chest_id")
    GOLD_COIN_ID_FIELD_NUMBER: _ClassVar[int]
    PLATINUM_COIN_ID_FIELD_NUMBER: _ClassVar[int]
    CRYSTAL_COIN_ID_FIELD_NUMBER: _ClassVar[int]
    TIBIA_COIN_ID_FIELD_NUMBER: _ClassVar[int]
    STAMPED_LETTER_ID_FIELD_NUMBER: _ClassVar[int]
    SUPPLY_STASH_ID_FIELD_NUMBER: _ClassVar[int]
    STANDARD_REWARD_CHEST_ID_FIELD_NUMBER: _ClassVar[int]
    gold_coin_id: int
    platinum_coin_id: int
    crystal_coin_id: int
    tibia_coin_id: int
    stamped_letter_id: int
    supply_stash_id: int
    standard_reward_chest_id: int
    def __init__(self, gold_coin_id: _Optional[int] = ..., platinum_coin_id: _Optional[int] = ..., crystal_coin_id: _Optional[int] = ..., tibia_coin_id: _Optional[int] = ..., stamped_letter_id: _Optional[int] = ..., supply_stash_id: _Optional[int] = ..., standard_reward_chest_id: _Optional[int] = ...) -> None: ...
