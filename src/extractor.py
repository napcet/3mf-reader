"""
Extrator de dados de arquivos 3MF (Orca Slicer / BambuStudio)
Combina dados do projeto .3mf com estatísticas do .gcode
"""

import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Callable

from .models import (
    ProjectSummary, PlateInfo, ObjectInfo, FilamentInfo,
    PrintSettings, PrintStatistics
)
from .gcode_parser import GCodeParser, GCodeStatistics


class ThreeMFExtractor:
    """Extrai dados técnicos de arquivos 3MF + G-code"""
    
    # Namespaces XML usados no 3MF
    NAMESPACES = {
        'model': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02',
        'p': 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06',
        'bambu': 'http://schemas.bambulab.com/package/2021'
    }
    
    def __init__(
        self, 
        filepath: str | Path, 
        gcode_path: Optional[str | Path] = None,
        gcode_selector: Optional[Callable[[list[Path]], Path]] = None
    ):
        """
        Args:
            filepath: Caminho para o arquivo .3mf
            gcode_path: Caminho para o arquivo .gcode (opcional, será detectado)
            gcode_selector: Função para selecionar G-code quando há múltiplos
        """
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        if not self.filepath.suffix.lower() == '.3mf':
            raise ValueError(f"Arquivo deve ter extensão .3mf: {filepath}")
        
        self._gcode_path: Optional[Path] = None
        self._gcode_selector = gcode_selector
        
        if gcode_path:
            self._gcode_path = Path(gcode_path)
            if not self._gcode_path.exists():
                raise FileNotFoundError(f"Arquivo G-code não encontrado: {gcode_path}")
        
        self._zip: Optional[zipfile.ZipFile] = None
        self._project_settings: Optional[dict] = None
        self._model_settings: Optional[ET.Element] = None
        self._main_model: Optional[ET.Element] = None
        self._gcode_stats: Optional[GCodeStatistics] = None
    
    def find_gcode_files(self) -> list[Path]:
        """Encontra arquivos .gcode na mesma pasta do .3mf"""
        folder = self.filepath.parent
        return sorted(folder.glob('*.gcode'))
    
    def find_matching_gcode(self) -> Optional[Path]:
        """
        Encontra o G-code correspondente ao projeto.
        Busca por nome similar ou usa o seletor se houver múltiplos.
        """
        gcode_files = self.find_gcode_files()
        
        if not gcode_files:
            return None
        
        if len(gcode_files) == 1:
            return gcode_files[0]
        
        # Buscar por nome similar (início do nome igual)
        project_name = self.filepath.stem.lower()
        for gcode in gcode_files:
            gcode_name = gcode.stem.lower()
            # Verificar se começa com o mesmo nome
            if gcode_name.startswith(project_name) or project_name.startswith(gcode_name.split('_')[0]):
                return gcode
        
        # Múltiplos arquivos, usar seletor
        if self._gcode_selector:
            return self._gcode_selector(gcode_files)
        
        # Sem seletor, retornar None (usuário precisa escolher)
        return None
    
    def extract(self) -> ProjectSummary:
        """Extrai todos os dados do arquivo 3MF + G-code"""
        
        # Resolver caminho do G-code se não fornecido
        if not self._gcode_path:
            self._gcode_path = self.find_matching_gcode()
        
        # Carregar estatísticas do G-code
        if self._gcode_path and self._gcode_path.exists():
            parser = GCodeParser(self._gcode_path)
            self._gcode_stats = parser.parse()
        
        with zipfile.ZipFile(self.filepath, 'r') as zf:
            self._zip = zf
            
            # Carregar arquivos principais
            self._load_main_model()
            self._load_project_settings()
            self._load_model_settings()
            
            # Extrair dados
            title = self._get_title()
            
            # Preferir generator do G-code (mais preciso) sobre metadata do 3MF
            # OrcaSlicer é fork do BambuStudio e pode herdar o nome incorreto no 3MF
            application = self._get_metadata('Application') or 'Unknown'
            if self._gcode_stats and self._gcode_stats.generator:
                application = self._gcode_stats.generator
            
            # Extrair filamentos e atualizar com dados do G-code
            filaments = self._extract_filaments()
            self._update_filaments_from_gcode(filaments)
            
            # Construir resumo
            summary = ProjectSummary(
                title=title,
                source_file=self.filepath.name,
                gcode_file=self._gcode_path.name if self._gcode_path else None,
                extraction_date=datetime.now(),
                application=application,
                printer_model=self._get_setting('printer_model', 'Unknown'),
                nozzle_diameter=float(self._get_setting('nozzle_diameter', ['0.4'])[0]),
                filaments=filaments,
                objects=self._extract_objects(),
                plates=self._extract_plates(),
                settings=self._extract_print_settings(),
                statistics=self._extract_statistics(),
                is_sliced=self._gcode_stats is not None
            )
            
            self._zip = None
            return summary
    
    def _update_filaments_from_gcode(self, filaments: list[FilamentInfo]) -> None:
        """Atualiza informações dos filamentos com dados do G-code"""
        if not self._gcode_stats:
            return
        
        for filament in filaments:
            slot = filament.slot
            
            # Peso usado
            if slot in self._gcode_stats.weight_per_slot:
                filament.used_grams = self._gcode_stats.weight_per_slot[slot]
            
            # Comprimento usado (converter mm para metros)
            if slot in self._gcode_stats.length_per_slot:
                filament.used_meters = self._gcode_stats.length_per_slot[slot] / 1000.0
            
            # Custo
            if slot in self._gcode_stats.cost_per_slot:
                filament.estimated_cost = self._gcode_stats.cost_per_slot[slot]
    
    def _load_main_model(self) -> None:
        """Carrega o modelo 3D principal"""
        try:
            with self._zip.open('3D/3dmodel.model') as f:
                self._main_model = ET.parse(f).getroot()
        except KeyError:
            self._main_model = None
    
    def _load_project_settings(self) -> None:
        """Carrega configurações do projeto (JSON)"""
        try:
            with self._zip.open('Metadata/project_settings.config') as f:
                self._project_settings = json.load(f)
        except (KeyError, json.JSONDecodeError):
            self._project_settings = {}
    
    def _load_model_settings(self) -> None:
        """Carrega configurações do modelo (XML)"""
        try:
            with self._zip.open('Metadata/model_settings.config') as f:
                self._model_settings = ET.parse(f).getroot()
        except (KeyError, ET.ParseError):
            self._model_settings = None
    
    def _get_metadata(self, name: str) -> Optional[str]:
        """Obtém metadado do modelo principal"""
        if self._main_model is None:
            return None
        
        for meta in self._main_model.findall('model:metadata', self.NAMESPACES):
            if meta.get('name') == name:
                return meta.text
        
        # Tentar sem namespace
        for meta in self._main_model.findall('metadata'):
            if meta.get('name') == name:
                return meta.text
        
        return None
    
    def _get_setting(self, key: str, default: Any = None) -> Any:
        """Obtém configuração do project_settings"""
        return self._project_settings.get(key, default)
    
    def _get_title(self) -> str:
        """Obtém título do projeto (metadado ou nome do arquivo)"""
        title = self._get_metadata('Title')
        if title and title.strip():
            return title.strip()
        
        # Fallback: nome do arquivo sem extensão
        return self.filepath.stem
    
    def _extract_filaments(self) -> list[FilamentInfo]:
        """Extrai informações de todos os filamentos configurados"""
        filaments = []
        
        types = self._get_setting('filament_type', [])
        colors = self._get_setting('filament_colour', [])
        vendors = self._get_setting('filament_vendor', [])
        densities = self._get_setting('filament_density', [])
        costs = self._get_setting('filament_cost', [])
        
        num_filaments = max(len(types), len(colors), 1)
        
        for i in range(num_filaments):
            filament = FilamentInfo(
                slot=i + 1,  # Slots são 1-indexed
                filament_type=types[i] if i < len(types) else 'Unknown',
                color=colors[i] if i < len(colors) else '#808080',
                color_name=self._hex_to_color_name(colors[i] if i < len(colors) else ''),
                vendor=vendors[i] if i < len(vendors) else 'Unknown',
                density=float(densities[i]) if i < len(densities) else 1.24,
                cost_per_kg=float(costs[i]) if i < len(costs) else 0.0
            )
            filaments.append(filament)
        
        return filaments
    
    def _extract_objects(self) -> list[ObjectInfo]:
        """Extrai informações dos objetos do projeto"""
        objects = []
        
        if self._model_settings is None:
            return objects
        
        for obj_elem in self._model_settings.findall('object'):
            obj_id = int(obj_elem.get('id', 0))
            name = ''
            extruder = 1
            source_file = None
            
            for meta in obj_elem.findall('metadata'):
                key = meta.get('key', '')
                value = meta.get('value', '')
                
                if key == 'name':
                    name = value
                elif key == 'extruder':
                    extruder = int(value) if value else 1
                elif key == 'source_file':
                    source_file = Path(value).name if value else None
            
            objects.append(ObjectInfo(
                obj_id=obj_id,
                name=name,
                extruder=extruder,
                source_file=source_file
            ))
        
        return objects
    
    def _extract_plates(self) -> list[PlateInfo]:
        """Extrai informações das placas de impressão"""
        plates = []
        
        # Procurar arquivos plate_*.json
        for name in self._zip.namelist():
            if name.startswith('Metadata/plate_') and name.endswith('.json'):
                try:
                    with self._zip.open(name) as f:
                        plate_data = json.load(f)
                    
                    # Extrair número da placa do nome do arquivo
                    plate_num = int(name.split('plate_')[1].split('.')[0])
                    
                    plate = PlateInfo(
                        plate_id=plate_num,
                        name=f"Plate {plate_num}",
                        bed_type=plate_data.get('bed_type', 'unknown'),
                        nozzle_diameter=plate_data.get('nozzle_diameter', 0.4),
                        is_sequential=plate_data.get('is_seq_print', False),
                        objects=self._extract_plate_objects(plate_data),
                        print_time_seconds=plate_data.get('prediction'),
                        weight_grams=plate_data.get('weight')
                    )
                    plates.append(plate)
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # Se não há JSONs, criar placa padrão baseada no model_settings
        if not plates and self._model_settings is not None:
            plate_elem = self._model_settings.find('plate')
            if plate_elem is not None:
                plate_id = 1
                for meta in plate_elem.findall('metadata'):
                    if meta.get('key') == 'plater_id':
                        plate_id = int(meta.get('value', 1))
                
                plates.append(PlateInfo(
                    plate_id=plate_id,
                    name=f"Plate {plate_id}",
                    bed_type=self._get_setting('curr_bed_type', 'unknown'),
                    nozzle_diameter=float(self._get_setting('nozzle_diameter', ['0.4'])[0]),
                    is_sequential=self._get_setting('print_sequence', '') == 'by object'
                ))
        
        return plates
    
    def _extract_plate_objects(self, plate_data: dict) -> list[ObjectInfo]:
        """Extrai objetos de uma placa específica"""
        objects = []
        
        for bbox_obj in plate_data.get('bbox_objects', []):
            objects.append(ObjectInfo(
                obj_id=bbox_obj.get('id', 0),
                name=bbox_obj.get('name', 'Unknown'),
                extruder=1,
                layer_height=bbox_obj.get('layer_height')
            ))
        
        return objects
    
    def _extract_print_settings(self) -> PrintSettings:
        """Extrai configurações principais de impressão"""
        
        def get_first(key: str, default: str = '0') -> str:
            val = self._get_setting(key, default)
            if isinstance(val, list):
                return val[0] if val else default
            return str(val) if val else default
        
        def get_int(key: str, default: int = 0) -> int:
            val = get_first(key, str(default))
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return default
        
        def get_float(key: str, default: float = 0.0) -> float:
            val = get_first(key, str(default))
            try:
                return float(val)
            except (ValueError, TypeError):
                return default
        
        # Determinar temperatura da mesa baseado no tipo de placa
        bed_type = self._get_setting('curr_bed_type', 'High Temp Plate')
        bed_temp_key = 'hot_plate_temp'
        if 'cool' in bed_type.lower():
            bed_temp_key = 'cool_plate_temp'
        elif 'textured' in bed_type.lower():
            bed_temp_key = 'textured_plate_temp'
        elif 'eng' in bed_type.lower():
            bed_temp_key = 'eng_plate_temp'
        
        return PrintSettings(
            layer_height=get_float('layer_height', 0.2),
            initial_layer_height=get_float('initial_layer_print_height', 0.2),
            wall_loops=get_int('wall_loops', 2),
            top_shell_layers=get_int('top_shell_layers', 4),
            bottom_shell_layers=get_int('bottom_shell_layers', 3),
            infill_density=self._get_setting('sparse_infill_density', '15%'),
            infill_pattern=self._get_setting('sparse_infill_pattern', 'grid'),
            nozzle_temp=get_int('nozzle_temperature', 200),
            nozzle_temp_initial=get_int('nozzle_temperature_initial_layer', 200),
            bed_temp=get_int(bed_temp_key, 60),
            bed_type=bed_type,
            print_speed=get_int('inner_wall_speed') or None,
            travel_speed=get_int('travel_speed') or None,
            support_enabled=self._get_setting('enable_support', '0') == '1',
            support_type=self._get_setting('support_type') if self._get_setting('enable_support', '0') == '1' else None
        )
    
    def _extract_statistics(self) -> Optional[PrintStatistics]:
        """Extrai estatísticas de impressão do G-code"""
        if not self._gcode_stats:
            return None
        
        return PrintStatistics(
            total_print_time_seconds=self._gcode_stats.estimated_time_seconds,
            total_print_time_str=self._gcode_stats.estimated_time_str,
            total_weight_grams=self._gcode_stats.total_weight_grams,
            total_filament_meters=self._gcode_stats.total_length_mm / 1000.0,
            total_cost=self._gcode_stats.total_cost,
            total_layers=self._gcode_stats.total_layers,
            max_z_height=self._gcode_stats.max_z_height
        )
    
    @staticmethod
    def _hex_to_color_name(hex_color: str) -> str:
        """Converte cor hex para nome aproximado"""
        if not hex_color or not hex_color.startswith('#'):
            return ''
        
        try:
            hex_clean = hex_color.lstrip('#')
            r = int(hex_clean[0:2], 16)
            g = int(hex_clean[2:4], 16)
            b = int(hex_clean[4:6], 16)
        except (ValueError, IndexError):
            return ''
        
        # Mapeamento simples de cores
        colors = {
            (255, 255, 255): 'Branco',
            (0, 0, 0): 'Preto',
            (255, 0, 0): 'Vermelho',
            (0, 255, 0): 'Verde',
            (0, 0, 255): 'Azul',
            (255, 255, 0): 'Amarelo',
            (255, 165, 0): 'Laranja',
            (128, 128, 128): 'Cinza',
            (229, 229, 229): 'Branco',
            (77, 77, 77): 'Cinza Escuro',
        }
        
        # Encontrar cor mais próxima
        min_dist = float('inf')
        closest = ''
        for (cr, cg, cb), name in colors.items():
            dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if dist < min_dist:
                min_dist = dist
                closest = name
        
        return closest if min_dist < 10000 else ''
