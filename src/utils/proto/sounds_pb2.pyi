import sounds_common_pb2 as _sounds_common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Sounds(_message.Message):
    __slots__ = ("sound", "numeric_sound_effect", "ambience_stream", "ambience_object_stream", "music_template")
    SOUND_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_SOUND_EFFECT_FIELD_NUMBER: _ClassVar[int]
    AMBIENCE_STREAM_FIELD_NUMBER: _ClassVar[int]
    AMBIENCE_OBJECT_STREAM_FIELD_NUMBER: _ClassVar[int]
    MUSIC_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    sound: _containers.RepeatedCompositeFieldContainer[Sound]
    numeric_sound_effect: _containers.RepeatedCompositeFieldContainer[NumericSoundEffect]
    ambience_stream: _containers.RepeatedCompositeFieldContainer[AmbienceStream]
    ambience_object_stream: _containers.RepeatedCompositeFieldContainer[AmbienceObjectStream]
    music_template: _containers.RepeatedCompositeFieldContainer[MusicTemplate]
    def __init__(self, sound: _Optional[_Iterable[_Union[Sound, _Mapping]]] = ..., numeric_sound_effect: _Optional[_Iterable[_Union[NumericSoundEffect, _Mapping]]] = ..., ambience_stream: _Optional[_Iterable[_Union[AmbienceStream, _Mapping]]] = ..., ambience_object_stream: _Optional[_Iterable[_Union[AmbienceObjectStream, _Mapping]]] = ..., music_template: _Optional[_Iterable[_Union[MusicTemplate, _Mapping]]] = ...) -> None: ...

class Sound(_message.Message):
    __slots__ = ("id", "filename", "original_filename", "is_stream")
    ID_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_FILENAME_FIELD_NUMBER: _ClassVar[int]
    IS_STREAM_FIELD_NUMBER: _ClassVar[int]
    id: int
    filename: str
    original_filename: str
    is_stream: bool
    def __init__(self, id: _Optional[int] = ..., filename: _Optional[str] = ..., original_filename: _Optional[str] = ..., is_stream: bool = ...) -> None: ...

class NumericSoundEffect(_message.Message):
    __slots__ = ("id", "numeric_sound_type", "random_pitch", "random_volume", "simple_sound_effect", "random_sound_effect")
    ID_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_SOUND_TYPE_FIELD_NUMBER: _ClassVar[int]
    RANDOM_PITCH_FIELD_NUMBER: _ClassVar[int]
    RANDOM_VOLUME_FIELD_NUMBER: _ClassVar[int]
    SIMPLE_SOUND_EFFECT_FIELD_NUMBER: _ClassVar[int]
    RANDOM_SOUND_EFFECT_FIELD_NUMBER: _ClassVar[int]
    id: int
    numeric_sound_type: _sounds_common_pb2.ENumericSoundType
    random_pitch: _sounds_common_pb2.MinMaxFloat
    random_volume: _sounds_common_pb2.MinMaxFloat
    simple_sound_effect: _sounds_common_pb2.SimpleSoundEffect
    random_sound_effect: _sounds_common_pb2.RandomSoundEffect
    def __init__(self, id: _Optional[int] = ..., numeric_sound_type: _Optional[_Union[_sounds_common_pb2.ENumericSoundType, str]] = ..., random_pitch: _Optional[_Union[_sounds_common_pb2.MinMaxFloat, _Mapping]] = ..., random_volume: _Optional[_Union[_sounds_common_pb2.MinMaxFloat, _Mapping]] = ..., simple_sound_effect: _Optional[_Union[_sounds_common_pb2.SimpleSoundEffect, _Mapping]] = ..., random_sound_effect: _Optional[_Union[_sounds_common_pb2.RandomSoundEffect, _Mapping]] = ...) -> None: ...

class AmbienceStream(_message.Message):
    __slots__ = ("id", "looping_sound_id", "delayed_effects")
    ID_FIELD_NUMBER: _ClassVar[int]
    LOOPING_SOUND_ID_FIELD_NUMBER: _ClassVar[int]
    DELAYED_EFFECTS_FIELD_NUMBER: _ClassVar[int]
    id: int
    looping_sound_id: int
    delayed_effects: _containers.RepeatedCompositeFieldContainer[_sounds_common_pb2.DelayedSoundEffect]
    def __init__(self, id: _Optional[int] = ..., looping_sound_id: _Optional[int] = ..., delayed_effects: _Optional[_Iterable[_Union[_sounds_common_pb2.DelayedSoundEffect, _Mapping]]] = ...) -> None: ...

class AmbienceObjectStream(_message.Message):
    __slots__ = ("id", "counted_appearance_types", "sound_effects", "max_sound_distance")
    ID_FIELD_NUMBER: _ClassVar[int]
    COUNTED_APPEARANCE_TYPES_FIELD_NUMBER: _ClassVar[int]
    SOUND_EFFECTS_FIELD_NUMBER: _ClassVar[int]
    MAX_SOUND_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    id: int
    counted_appearance_types: _containers.RepeatedScalarFieldContainer[int]
    sound_effects: _containers.RepeatedCompositeFieldContainer[_sounds_common_pb2.AppearanceTypesCountSoundEffect]
    max_sound_distance: int
    def __init__(self, id: _Optional[int] = ..., counted_appearance_types: _Optional[_Iterable[int]] = ..., sound_effects: _Optional[_Iterable[_Union[_sounds_common_pb2.AppearanceTypesCountSoundEffect, _Mapping]]] = ..., max_sound_distance: _Optional[int] = ...) -> None: ...

class MusicTemplate(_message.Message):
    __slots__ = ("id", "sound_id", "music_type")
    ID_FIELD_NUMBER: _ClassVar[int]
    SOUND_ID_FIELD_NUMBER: _ClassVar[int]
    MUSIC_TYPE_FIELD_NUMBER: _ClassVar[int]
    id: int
    sound_id: int
    music_type: _sounds_common_pb2.EMusicType
    def __init__(self, id: _Optional[int] = ..., sound_id: _Optional[int] = ..., music_type: _Optional[_Union[_sounds_common_pb2.EMusicType, str]] = ...) -> None: ...
