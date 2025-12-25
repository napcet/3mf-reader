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
            "| Parâmetro | Valor |",
            "|-----------|-------|",
            f"| Layer height | {settings.layer_height}mm |",
            f"| Primeira camada | {settings.initial_layer_height}mm |",
            f"| Paredes | {settings.wall_loops} |",
            f"| Topo/Fundo | {settings.top_shell_layers}/{settings.bottom_shell_layers} camadas |",
            f"| Preenchimento | {settings.infill_density} |",
            f"| Temp. bico | {settings.nozzle_temp}°C |",
            f"| Temp. mesa | {settings.bed_temp}°C ({settings.bed_type}) |",
        ]
        
        if settings.support_enabled:
            lines.append(f"| Suporte | ✅ {settings.support_type or 'Ativado'} |")
        else:
            lines.append("| Suporte | ❌ Desativado |")
        
        lines.append("")
        return '\n'.join(lines)
    
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
