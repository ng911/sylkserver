from .psap import Psap
from .db import Base, getUniqueId
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint


class MapLayer(Base):
    map_layer_id = Column(String, primary_key=True, default=getUniqueId(), index=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    description = Column(String)
    __table_args__ = (UniqueConstraint('map_layer_id'))

class MapFile(Base):
    map_layer_id = Column(String, ForeignKey(MapLayer.map_layer_id), index=True)
    map_file_id = Column(String, primary_key=True, default=getUniqueId(), index=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False, index=True)
    filename = Column(String, nullable=False)
    relative_path = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint('map_file_id'))