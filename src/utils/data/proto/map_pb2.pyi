import shared_pb2 as _shared_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MAP_FILE_TYPE(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MAP_FILE_TYPE_SUBAREA: _ClassVar[MAP_FILE_TYPE]
    MAP_FILE_TYPE_SATELLITE: _ClassVar[MAP_FILE_TYPE]
    MAP_FILE_TYPE_MINIMAP: _ClassVar[MAP_FILE_TYPE]

class AREA_TYPE(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AREA_TYPE_NONE: _ClassVar[AREA_TYPE]
    AREA_TYPE_AREA: _ClassVar[AREA_TYPE]
    AREA_TYPE_SUBAREA: _ClassVar[AREA_TYPE]
MAP_FILE_TYPE_SUBAREA: MAP_FILE_TYPE
MAP_FILE_TYPE_SATELLITE: MAP_FILE_TYPE
MAP_FILE_TYPE_MINIMAP: MAP_FILE_TYPE
AREA_TYPE_NONE: AREA_TYPE
AREA_TYPE_AREA: AREA_TYPE
AREA_TYPE_SUBAREA: AREA_TYPE

class Map(_message.Message):
    __slots__ = ("areas", "npcs", "resource_files", "top_left_tile_coordinate", "bottom_right_tile_coordinate")
    AREAS_FIELD_NUMBER: _ClassVar[int]
    NPCS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FILES_FIELD_NUMBER: _ClassVar[int]
    TOP_LEFT_TILE_COORDINATE_FIELD_NUMBER: _ClassVar[int]
    BOTTOM_RIGHT_TILE_COORDINATE_FIELD_NUMBER: _ClassVar[int]
    areas: _containers.RepeatedCompositeFieldContainer[Area]
    npcs: _containers.RepeatedCompositeFieldContainer[Npc]
    resource_files: _containers.RepeatedCompositeFieldContainer[MapFile]
    top_left_tile_coordinate: _shared_pb2.Coordinate
    bottom_right_tile_coordinate: _shared_pb2.Coordinate
    def __init__(self, areas: _Optional[_Iterable[_Union[Area, _Mapping]]] = ..., npcs: _Optional[_Iterable[_Union[Npc, _Mapping]]] = ..., resource_files: _Optional[_Iterable[_Union[MapFile, _Mapping]]] = ..., top_left_tile_coordinate: _Optional[_Union[_shared_pb2.Coordinate, _Mapping]] = ..., bottom_right_tile_coordinate: _Optional[_Union[_shared_pb2.Coordinate, _Mapping]] = ...) -> None: ...

class Area(_message.Message):
    __slots__ = ("area_id", "name", "area_type", "subarea_ids", "label_coordinate", "reject_donations", "alias")
    AREA_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    AREA_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBAREA_IDS_FIELD_NUMBER: _ClassVar[int]
    LABEL_COORDINATE_FIELD_NUMBER: _ClassVar[int]
    REJECT_DONATIONS_FIELD_NUMBER: _ClassVar[int]
    ALIAS_FIELD_NUMBER: _ClassVar[int]
    area_id: int
    name: str
    area_type: AREA_TYPE
    subarea_ids: _containers.RepeatedScalarFieldContainer[int]
    label_coordinate: _shared_pb2.Coordinate
    reject_donations: bool
    alias: str
    def __init__(self, area_id: _Optional[int] = ..., name: _Optional[str] = ..., area_type: _Optional[_Union[AREA_TYPE, str]] = ..., subarea_ids: _Optional[_Iterable[int]] = ..., label_coordinate: _Optional[_Union[_shared_pb2.Coordinate, _Mapping]] = ..., reject_donations: bool = ..., alias: _Optional[str] = ...) -> None: ...

class Npc(_message.Message):
    __slots__ = ("name", "tile_coordinate", "subarea_id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TILE_COORDINATE_FIELD_NUMBER: _ClassVar[int]
    SUBAREA_ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    tile_coordinate: _shared_pb2.Coordinate
    subarea_id: int
    def __init__(self, name: _Optional[str] = ..., tile_coordinate: _Optional[_Union[_shared_pb2.Coordinate, _Mapping]] = ..., subarea_id: _Optional[int] = ...) -> None: ...

class MapFile(_message.Message):
    __slots__ = ("file_type", "top_left_coordinate", "file_name", "fields_width", "fields_height", "area_id", "scale_factor")
    FILE_TYPE_FIELD_NUMBER: _ClassVar[int]
    TOP_LEFT_COORDINATE_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    FIELDS_WIDTH_FIELD_NUMBER: _ClassVar[int]
    FIELDS_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    AREA_ID_FIELD_NUMBER: _ClassVar[int]
    SCALE_FACTOR_FIELD_NUMBER: _ClassVar[int]
    file_type: MAP_FILE_TYPE
    top_left_coordinate: _shared_pb2.Coordinate
    file_name: str
    fields_width: int
    fields_height: int
    area_id: int
    scale_factor: float
    def __init__(self, file_type: _Optional[_Union[MAP_FILE_TYPE, str]] = ..., top_left_coordinate: _Optional[_Union[_shared_pb2.Coordinate, _Mapping]] = ..., file_name: _Optional[str] = ..., fields_width: _Optional[int] = ..., fields_height: _Optional[int] = ..., area_id: _Optional[int] = ..., scale_factor: _Optional[float] = ...) -> None: ...
