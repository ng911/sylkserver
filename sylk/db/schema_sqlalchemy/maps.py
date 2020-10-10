from .psap import Psap
from .db import Base
from sqlalchemy import Column, String, ForeignKey


class MapLayer(Base):
    map_layer_id = Column(String, primary_key=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    description = Column(String)

class MapFile(Base):
    map_layer_id = Column(String, ForeignKey(MapLayer.map_layer_id))
    map_file_id = Column(String, primary_key=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    filename = Column(String, nullable=False)
    relative_path = Column(String, nullable=False)