"""
Modelos de dados para informações extraídas de arquivos 3MF
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class FilamentInfo:
    """Informações de um filamento/extrusor"""
    slot: int
    filament_type: str  # PLA, PETG, ABS, etc.
    color: str  # Hex color (#FFFFFF)
    color_name: str  # Nome da cor se disponível
    vendor: str
    density: float  # g/cm³
    cost_per_kg: float  # Custo por kg
    
    # Dados de uso (disponível apenas em arquivos fatiados)
    used_grams: Optional[float] = None
    used_meters: Optional[float] = None
    estimated_cost: Optional[float] = None


@dataclass
class PrintSettings:
    """Configurações principais de impressão"""
    layer_height: float
    initial_layer_height: float
    wall_loops: int
    top_shell_layers: int
    bottom_shell_layers: int
    infill_density: str  # "15%"
    infill_pattern: str
    
    # Temperaturas
    nozzle_temp: int
    nozzle_temp_initial: int
    bed_temp: int
    bed_type: str  # "High Temp Plate", etc.
    
    # Velocidades (mm/s)
    outer_wall_speed: Optional[int] = None
    inner_wall_speed: Optional[int] = None
    infill_speed: Optional[int] = None
    travel_speed: Optional[int] = None
    initial_layer_speed: Optional[int] = None
    top_surface_speed: Optional[int] = None
    
    # Aceleração (mm/s²)
    default_acceleration: Optional[int] = None
    outer_wall_acceleration: Optional[int] = None
    inner_wall_acceleration: Optional[int] = None
    
    # Largura de linha (mm)
    line_width: Optional[float] = None
    outer_wall_line_width: Optional[float] = None
    inner_wall_line_width: Optional[float] = None
    infill_line_width: Optional[float] = None
    
    # Retração
    retraction_length: Optional[float] = None
    retraction_speed: Optional[int] = None
    z_hop: Optional[float] = None
    z_hop_type: Optional[str] = None
    
    # Ventilação
    fan_min_speed: Optional[int] = None
    fan_max_speed: Optional[int] = None
    
    # Costura
    seam_position: Optional[str] = None
    
    # Adesão à mesa
    brim_type: Optional[str] = None
    brim_width: Optional[float] = None
    skirt_loops: Optional[int] = None
    
    # Suporte
    support_enabled: bool = False
    support_type: Optional[str] = None
    
    # Extras
    ironing_enabled: bool = False
    fuzzy_skin: Optional[str] = None


@dataclass
class ObjectInfo:
    """Informações de um objeto no projeto"""
    obj_id: int
    name: str
    extruder: int
    layer_height: Optional[float] = None
    source_file: Optional[str] = None


@dataclass 
class PlateInfo:
    """Informações de uma placa de impressão"""
    plate_id: int
    name: str
    bed_type: str
    nozzle_diameter: float
    is_sequential: bool
    objects: list[ObjectInfo] = field(default_factory=list)
    
    # Dados de fatiamento (disponível apenas em arquivos fatiados)
    print_time_seconds: Optional[int] = None
    weight_grams: Optional[float] = None
    filament_used: Optional[dict[int, float]] = None  # slot -> grams


@dataclass
class PrintStatistics:
    """Estatísticas de impressão (extraídas do G-code)"""
    total_print_time_seconds: int
    total_print_time_str: str  # String original do slicer (ex: "2h 6m 5s")
    total_weight_grams: float
    total_filament_meters: float
    total_cost: float
    total_layers: int = 0
    max_z_height: float = 0.0
    
    def format_time(self) -> str:
        """Retorna tempo formatado"""
        if self.total_print_time_str:
            return self.total_print_time_str
        hours = self.total_print_time_seconds // 3600
        minutes = (self.total_print_time_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


@dataclass
class ProjectSummary:
    """Resumo completo do projeto 3MF + G-code"""
    # Identificação
    title: str
    source_file: str
    gcode_file: Optional[str]  # Nome do arquivo G-code usado
    extraction_date: datetime
    
    # Software
    application: str  # "OrcaSlicer-2.2.0", etc.
    printer_model: str
    nozzle_diameter: float
    
    # Conteúdo
    plates: list[PlateInfo] = field(default_factory=list)
    objects: list[ObjectInfo] = field(default_factory=list)
    filaments: list[FilamentInfo] = field(default_factory=list)
    
    # Configurações
    settings: Optional[PrintSettings] = None
    
    # Estatísticas (apenas se fatiado)
    statistics: Optional[PrintStatistics] = None
    is_sliced: bool = False
    
    @property
    def total_plates(self) -> int:
        return len(self.plates)
    
    @property
    def total_objects(self) -> int:
        return len(self.objects)
    
    @property
    def active_filaments(self) -> list[FilamentInfo]:
        """Retorna apenas filamentos que são usados no projeto"""
        used_slots = {obj.extruder for obj in self.objects}
        return [f for f in self.filaments if f.slot in used_slots]
