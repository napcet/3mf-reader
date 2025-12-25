# 📦 3MF Reader

Extrator de dados técnicos de arquivos 3MF para impressão 3D.

Gera relatórios Markdown compactos com informações de tempo, custo, materiais e configurações de impressão a partir de projetos do **Orca Slicer** / **BambuStudio**.

## ✨ Funcionalidades

- 📊 Extrai estimativas de **tempo**, **peso** e **custo** do G-code
- 🎨 Lista **materiais** utilizados com cores e quantidades
- ⚙️ Mostra **configurações** principais (layer height, infill, temperaturas)
- 🗂️ Identifica **objetos** do projeto e seus extrusores
- 📄 Gera relatório **Markdown** organizado e legível

## 📋 Requisitos

- Python 3.10+
- Arquivos `.3mf` do Orca Slicer ou BambuStudio
- Arquivo `.gcode` correspondente (para estimativas de tempo/custo)

## 🚀 Instalação

```bash
# Clonar o repositório
git clone https://github.com/SEU_USUARIO/3mf-reader.git
cd 3mf-reader

# Criar ambiente virtual (opcional)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## 📖 Uso

### Uso básico

```bash
python main.py projeto.3mf
```

O programa detecta automaticamente o arquivo `.gcode` na mesma pasta.

### Especificar G-code manualmente

```bash
python main.py projeto.3mf --gcode fatiamento.gcode
```

### Definir pasta de saída

```bash
python main.py projeto.3mf --output ./relatorios
```

### Modo silencioso (sem interação)

```bash
python main.py projeto.3mf --quiet
```

## 📄 Exemplo de Relatório

```markdown
# 📦 MeuProjeto

**Impressora:** Creality K1  
**Bico:** 0.4mm  
**Slicer:** OrcaSlicer 2.3.1

## 📊 Resumo da Impressão

| Métrica               | Valor   |
| --------------------- | ------- |
| ⏱️ **Tempo estimado** | 2h 30m  |
| ⚖️ **Peso total**     | 45.2g   |
| 💰 **Custo estimado** | R$ 5.15 |

## 🎨 Materiais

| Slot | Tipo | Cor             |  Peso |   Custo |
| :--: | ---- | --------------- | ----: | ------: |
|  1   | PLA  | Preto (#000000) | 45.2g | R$ 5.15 |
```

## 🗂️ Estrutura do Projeto

```
3mf-reader/
├── main.py              # CLI principal
├── requirements.txt     # Dependências
├── src/
│   ├── __init__.py      # Versão do pacote
│   ├── models.py        # Dataclasses
│   ├── extractor.py     # Extrator de dados 3MF
│   ├── gcode_parser.py  # Parser de G-code
│   └── report.py        # Gerador de Markdown
└── output/              # Relatórios gerados
```

## 🔧 Como Funciona

1. **Lê o arquivo `.3mf`** (ZIP com XMLs e JSONs) para extrair:

   - Metadados do projeto (nome, slicer)
   - Configurações de impressão
   - Lista de objetos e filamentos

2. **Lê o arquivo `.gcode`** para extrair:

   - Tempo estimado de impressão
   - Peso e comprimento de filamento
   - Custo calculado pelo slicer

3. **Gera relatório Markdown** combinando as informações em formato legível

## 📝 Notas

- O custo é calculado pelo slicer baseado no valor configurado por kg de filamento
- Para ter estimativas precisas, exporte o G-code após fatiar no Orca Slicer
- O programa detecta automaticamente G-codes com nome similar ao projeto

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:

- Reportar bugs
- Sugerir melhorias
- Enviar pull requests

## 📜 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

## 🏷️ Versão

Veja [CHANGELOG.md](CHANGELOG.md) para histórico de versões.
