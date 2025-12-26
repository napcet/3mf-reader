"""
Gerador de relatório Markdown para projetos 3MF
Formato compacto (~1 página A4)
"""

from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import ProjectSummary, FilamentInfo


class MarkdownReportGenerator:
    """Gera relatório Markdown a partir do resumo do projeto"""
    
    def __init__(self, summary: ProjectSummary):
        self.summary = summary
    
    def generate(self) -> str:
        """Gera o conteúdo Markdown completo"""
        sections = [
            self._header(),
            self._print_summary(),
            self._materials_table(),
            self._print_settings(),
            self._objects_list(),
            self._footer()
        ]
        
        return '\n'.join(filter(None, sections))
    
    def save(self, output_dir: str | Path = '.') -> Path:
        """Salva o relatório como arquivo .md"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Nome do arquivo baseado no título do projeto
        safe_name = self._safe_filename(self.summary.title)
        output_path = output_dir / f"{safe_name}.md"
        
        content = self.generate()
        output_path.write_text(content, encoding='utf-8')
        
        return output_path
    
    def _header(self) -> str:
        """Cabeçalho do relatório"""
        s = self.summary
        lines = [
            f"# 📦 {s.title}",
            "",
            f"**Impressora:** {s.printer_model}  ",
            f"**Bico:** {s.nozzle_diameter}mm  ",
            f"**Slicer:** {s.application}  ",
            f"**Data do relatório:** {s.extraction_date.strftime('%d/%m/%Y %H:%M')}",
            ""
        ]
        return '\n'.join(lines)
    
    def _print_summary(self) -> str:
        """Resumo principal da impressão"""
        stats = self.summary.statistics
        
        if not stats:
            return "> ⚠️ *Arquivo G-code não encontrado. Estimativas não disponíveis.*\n"
        
        lines = [
            "## 📊 Resumo da Impressão",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| ⏱️ **Tempo estimado** | {stats.format_time()} |",
            f"| ⚖️ **Peso total** | {stats.total_weight_grams:.1f}g |",
            f"| 📏 **Filamento** | {stats.total_filament_meters:.2f}m |",
            f"| 💰 **Custo estimado** | R$ {stats.total_cost:.2f} |",
            f"| 📐 **Camadas** | {stats.total_layers} |",
            f"| 📏 **Altura máxima** | {stats.max_z_height:.2f}mm |",
            ""
        ]
        return '\n'.join(lines)
    
    def _materials_table(self) -> str:
        """Tabela de materiais utilizados"""
        # Filtrar apenas filamentos com uso
        active = [f for f in self.summary.filaments if f.used_grams and f.used_grams > 0]
        
        if not active:
            # Mostrar filamentos configurados mesmo sem uso
            active = self.summary.active_filaments[:4]  # Limitar a 4
            if not active:
                return ""
        
        lines = [
            "## 🎨 Materiais",
            "",
            "| Slot | Tipo | Cor | Peso | Custo |",
            "|:----:|------|-----|-----:|------:|",
        ]
        
        for f in active:
            color_display = self._color_display(f)
            weight = f"{f.used_grams:.1f}g" if f.used_grams else "-"
            cost = f"R$ {f.estimated_cost:.2f}" if f.estimated_cost else "-"
            
            lines.append(f"| {f.slot} | {f.filament_type} | {color_display} | {weight} | {cost} |")
        
        lines.append("")
        return '\n'.join(lines)
    
    def _print_settings(self) -> str:
        """Configurações de impressão"""
        settings = self.summary.settings
        if not settings:
            return ""
        
        lines = [
            "## ⚙️ Configurações",
            "",
            "### Qualidade",
            "",
            "| Parâmetro | Valor |",
            "|-----------|-------|",
            f"| Altura de camada | {settings.layer_height}mm |",
            f"| Primeira camada | {settings.initial_layer_height}mm |",
            f"| Paredes | {settings.wall_loops} |",
            f"| Topo/Fundo | {settings.top_shell_layers}/{settings.bottom_shell_layers} camadas |",
            f"| Preenchimento | {settings.infill_density} ({self._format_pattern(settings.infill_pattern)}) |",
        ]
        
        # Largura de linha
        if settings.line_width:
            lines.append(f"| Largura de linha | {settings.line_width}mm |")
        if settings.outer_wall_line_width and settings.outer_wall_line_width != settings.line_width:
            lines.append(f"| Largura parede externa | {settings.outer_wall_line_width}mm |")
        
        # Costura
        if settings.seam_position:
            seam_names = {
                'aligned': 'Alinhada',
                'back': 'Traseira',
                'random': 'Aleatória',
                'nearest': 'Mais próxima'
            }
            lines.append(f"| Posição da costura | {seam_names.get(settings.seam_position, settings.seam_position)} |")
        
        lines.append("")
        
        # Velocidades
        lines.extend([
            "### Velocidades",
            "",
            "| Parâmetro | Valor |",
            "|-----------|-------|",
        ])
        
        if settings.outer_wall_speed:
            lines.append(f"| Parede externa | {settings.outer_wall_speed} mm/s |")
        if settings.inner_wall_speed:
            lines.append(f"| Parede interna | {settings.inner_wall_speed} mm/s |")
        if settings.infill_speed:
            lines.append(f"| Preenchimento | {settings.infill_speed} mm/s |")
        if settings.top_surface_speed:
            lines.append(f"| Superfície superior | {settings.top_surface_speed} mm/s |")
        if settings.initial_layer_speed:
            lines.append(f"| Primeira camada | {settings.initial_layer_speed} mm/s |")
        if settings.travel_speed:
            lines.append(f"| Viagem | {settings.travel_speed} mm/s |")
        
        lines.append("")
        
        # Aceleração
        if settings.default_acceleration or settings.outer_wall_acceleration:
            lines.extend([
                "### Aceleração",
                "",
                "| Parâmetro | Valor |",
                "|-----------|-------|",
            ])
            if settings.default_acceleration:
                lines.append(f"| Padrão | {settings.default_acceleration} mm/s² |")
            if settings.outer_wall_acceleration:
                lines.append(f"| Parede externa | {settings.outer_wall_acceleration} mm/s² |")
            if settings.inner_wall_acceleration and settings.inner_wall_acceleration != settings.outer_wall_acceleration:
                lines.append(f"| Parede interna | {settings.inner_wall_acceleration} mm/s² |")
            lines.append("")
        
        # Temperaturas
        lines.extend([
            "### Temperaturas",
            "",
            "| Parâmetro | Valor |",
            "|-----------|-------|",
            f"| Bico | {settings.nozzle_temp}°C |",
        ])
        if settings.nozzle_temp_initial != settings.nozzle_temp:
            lines.append(f"| Bico (1ª camada) | {settings.nozzle_temp_initial}°C |")
        lines.append(f"| Mesa | {settings.bed_temp}°C ({settings.bed_type}) |")
        lines.append("")
        
        # Retração
        if settings.retraction_length or settings.z_hop:
            lines.extend([
                "### Retração",
                "",
                "| Parâmetro | Valor |",
                "|-----------|-------|",
            ])
            if settings.retraction_length:
                lines.append(f"| Distância | {settings.retraction_length}mm |")
            if settings.retraction_speed:
                lines.append(f"| Velocidade | {settings.retraction_speed} mm/s |")
            if settings.z_hop:
                z_hop_info = f"{settings.z_hop}mm"
                if settings.z_hop_type:
                    z_hop_info += f" ({settings.z_hop_type})"
                lines.append(f"| Z-Hop | {z_hop_info} |")
            lines.append("")
        
        # Ventilação
        if settings.fan_max_speed:
            lines.extend([
                "### Ventilação",
                "",
                "| Parâmetro | Valor |",
                "|-----------|-------|",
            ])
            if settings.fan_min_speed == settings.fan_max_speed:
                lines.append(f"| Velocidade | {settings.fan_max_speed}% |")
            else:
                lines.append(f"| Mínima | {settings.fan_min_speed}% |")
                lines.append(f"| Máxima | {settings.fan_max_speed}% |")
            lines.append("")
        
        # Recursos especiais
        special_features = []
        
        # Suporte
        if settings.support_enabled:
            special_features.append(f"✅ Suporte: {settings.support_type or 'Ativado'}")
        
        # Adesão
        if settings.brim_type:
            brim_names = {
                'auto_brim': 'Auto',
                'brim_ears': 'Orelhas',
                'outer_only': 'Externo',
                'inner_only': 'Interno',
                'outer_and_inner': 'Completo'
            }
            brim_name = brim_names.get(settings.brim_type, settings.brim_type)
            brim_info = f"Brim {brim_name}"
            if settings.brim_width:
                brim_info += f" ({settings.brim_width}mm)"
            special_features.append(f"✅ {brim_info}")
        elif settings.skirt_loops and settings.skirt_loops > 0:
            special_features.append(f"✅ Skirt ({settings.skirt_loops} voltas)")
        
        # Ironing
        if settings.ironing_enabled:
            special_features.append("✅ Ironing ativado")
        
        # Fuzzy skin
        if settings.fuzzy_skin:
            special_features.append(f"✅ Fuzzy Skin: {settings.fuzzy_skin}")
        
        if special_features:
            lines.extend([
                "### Recursos Especiais",
                "",
            ])
            for feature in special_features:
                lines.append(f"- {feature}")
            if not settings.support_enabled:
                lines.append("- ❌ Suporte desativado")
            lines.append("")
        else:
            # Apenas mostrar suporte desativado se não há outros recursos
            lines.append("- ❌ Suporte desativado")
            lines.append("")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _format_pattern(pattern: str) -> str:
        """Formata nome do padrão de preenchimento"""
        patterns = {
            'grid': 'Grade',
            'gyroid': 'Gyroid',
            'honeycomb': 'Colmeia',
            'line': 'Linhas',
            'cubic': 'Cúbico',
            'triangles': 'Triângulos',
            'lightning': 'Relâmpago',
            'rectilinear': 'Retilíneo',
            'alignedrectilinear': 'Retilíneo Alinhado',
            'concentric': 'Concêntrico',
            'hilbertcurve': 'Curva de Hilbert',
            'archimedeanchords': 'Cordas de Arquimedes',
            'octagramspiral': 'Espiral Octograma',
            'supportcubic': 'Cúbico (suporte)',
            'adaptivecubic': 'Cúbico Adaptativo',
            '3dhoneycomb': 'Colmeia 3D',
            'crosshatch': 'Hachurado'
        }
        return patterns.get(pattern.lower(), pattern.capitalize())
    
    def _objects_list(self) -> str:
        """Lista de objetos no projeto"""
        objects = self.summary.objects
        if not objects:
            return ""
        
        lines = [
            "## 🗂️ Objetos",
            "",
        ]
        
        for obj in objects:
            filament = next((f for f in self.summary.filaments if f.slot == obj.extruder), None)
            filament_info = f" ({filament.filament_type})" if filament else ""
            lines.append(f"- **{obj.name}** — Extrusor {obj.extruder}{filament_info}")
        
        lines.append("")
        lines.append(f"*Total: {len(objects)} objeto(s) em {self.summary.total_plates} placa(s)*")
        lines.append("")
        
        return '\n'.join(lines)
    
    def _footer(self) -> str:
        """Rodapé com informações de origem"""
        s = self.summary
        lines = [
            "---",
            "",
            f"📁 **Projeto:** `{s.source_file}`  ",
        ]
        
        if s.gcode_file:
            lines.append(f"📄 **G-code:** `{s.gcode_file}`  ")
        
        lines.append(f"🕐 **Gerado em:** {s.extraction_date.strftime('%d/%m/%Y às %H:%M')}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _color_display(filament: FilamentInfo) -> str:
        """Formata exibição da cor"""
        if filament.color_name:
            return f"{filament.color_name} ({filament.color})"
        return filament.color
    
    @staticmethod
    def _safe_filename(name: str) -> str:
        """Converte nome para nome de arquivo seguro"""
        # Remover/substituir caracteres inválidos
        invalid = '<>:"/\\|?*'
        for char in invalid:
            name = name.replace(char, '_')
        return name.strip()
