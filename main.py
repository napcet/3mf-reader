#!/usr/bin/env python3
"""
3MF Reader - CLI para extração de dados técnicos de projetos 3D
Uso: python main.py <arquivo.3mf> [--gcode <arquivo.gcode>] [--output <pasta>]
"""

import argparse
import sys
from pathlib import Path

from src.extractor import ThreeMFExtractor
from src.report import MarkdownReportGenerator


def select_gcode_interactive(gcode_files: list[Path]) -> Path:
    """Permite ao usuário selecionar o arquivo G-code"""
    print("\n🔍 Múltiplos arquivos G-code encontrados:")
    print("-" * 50)
    
    for i, gcode in enumerate(gcode_files, 1):
        print(f"  [{i}] {gcode.name}")
    
    print("-" * 50)
    
    while True:
        try:
            choice = input(f"Selecione o arquivo (1-{len(gcode_files)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(gcode_files):
                return gcode_files[idx]
            print("❌ Opção inválida. Tente novamente.")
        except ValueError:
            print("❌ Digite um número válido.")
        except KeyboardInterrupt:
            print("\n\n⚠️ Operação cancelada.")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Extrai dados técnicos de arquivos 3MF e gera relatório Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py projeto.3mf
  python main.py projeto.3mf --gcode fatiamento.gcode
  python main.py projeto.3mf --output ./relatorios
        """
    )
    
    parser.add_argument(
        'arquivo_3mf',
        type=Path,
        help='Caminho para o arquivo .3mf do projeto'
    )
    
    parser.add_argument(
        '--gcode', '-g',
        type=Path,
        default=None,
        help='Caminho para o arquivo .gcode (opcional, será detectado automaticamente)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('./output'),
        help='Pasta de saída para o relatório (padrão: ./output)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Modo silencioso (sem saída interativa)'
    )
    
    args = parser.parse_args()
    
    # Validar arquivo 3MF
    if not args.arquivo_3mf.exists():
        print(f"❌ Arquivo não encontrado: {args.arquivo_3mf}")
        sys.exit(1)
    
    if not args.arquivo_3mf.suffix.lower() == '.3mf':
        print(f"❌ Arquivo deve ter extensão .3mf: {args.arquivo_3mf}")
        sys.exit(1)
    
    # Configurar seletor de G-code
    gcode_selector = None if args.quiet else select_gcode_interactive
    
    try:
        # Extrair dados
        print(f"\n📂 Processando: {args.arquivo_3mf.name}")
        
        extractor = ThreeMFExtractor(
            filepath=args.arquivo_3mf,
            gcode_path=args.gcode,
            gcode_selector=gcode_selector
        )
        
        # Verificar G-code
        if not args.gcode:
            gcode_files = extractor.find_gcode_files()
            if not gcode_files:
                print("⚠️  Nenhum arquivo G-code encontrado na pasta.")
                print("   Estimativas de tempo/custo não estarão disponíveis.")
            elif len(gcode_files) == 1:
                print(f"✅ G-code detectado: {gcode_files[0].name}")
        
        summary = extractor.extract()
        
        # Gerar relatório
        generator = MarkdownReportGenerator(summary)
        output_path = generator.save(args.output)
        
        # Resumo
        print("\n" + "=" * 50)
        print(f"✅ Relatório gerado: {output_path}")
        print("=" * 50)
        
        if summary.statistics:
            stats = summary.statistics
            print(f"\n📊 Resumo:")
            print(f"   ⏱️  Tempo: {stats.format_time()}")
            print(f"   ⚖️  Peso: {stats.total_weight_grams:.1f}g")
            print(f"   💰 Custo: R$ {stats.total_cost:.2f}")
        
        print()
        
    except FileNotFoundError as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
