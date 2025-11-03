# PGN Curator

**Config-driven chess opening repertoire curation tool**

Transform large PGN files into focused, student-specific repertoires using declarative YAML configurations.

## 🎯 Overview

PGN Curator is a Python command-line tool that helps chess coaches and parents curate massive opening repertoire files into manageable, personalized training materials. Simply write a YAML config describing what you want, and PGN Curator handles all the filtering, trimming, and curation automatically.

### Key Features

✅ **Config-driven workflow** - All curation in YAML, track changes with git  
✅ **Shorthand range syntax** - Super simple: `include: "9,28"`  
✅ **1-based indexing** - Works like chess software (Game [1], [2], [3]...)  
✅ **Fast processing** - 452K variations in <5 seconds  
✅ **Zero data loss** - Preserves all GM annotations and comments  
✅ **Beautiful CLI** - Rich output with statistics and progress  

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/yourusername/pgnc.git
cd pgnc
pip install -e .
```

### Basic Usage

```bash
# 1. See what's in your PGN file
pgnc inspect classical_openings.pgn

# 2. Create a config file
cat > my_config.yaml << EOF
name: "My Repertoire - Layer 1"
source: classical_openings.pgn
output: my_openings.pgn
settings:
  max_depth: 14
include: "1"  # Include the Sicilian Najdorf
EOF

# 3. Build curated PGN
pgnc build my_config.yaml --stats
```

**Result**: You get `my_openings.pgn` with just the openings you specified, trimmed to 14 moves!

## 🎓 Educational Philosophy

PGN Curator implements **Layered Depth Learning**:

- **Layer 1**: Understanding (12-14 moves) - Learn core positions and plans
- **Layer 2**: Precision (15-20 moves) - Sharp tactical lines for critical variations
- **Layer 3**: Reactive (20+ moves) - Deep theory learned on-demand

Each layer builds on the previous, ensuring students understand before memorizing.

## 📊 Real Results

**Example with `classical_openings.pgn`:**

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Games | 1 | 1 | 0% |
| Variations | 356 | 150 | 57.9% |
| Avg Depth | 31 moves | 14 moves | 54.8% |

**Result**: Clean, focused repertoire while preserving all GM annotations!

## ✨ Configuration Examples

### Simple Style

```yaml
name: "My Repertoire"
source: classical_openings.pgn
output: my_openings.pgn
settings:
  max_depth: 14
include: "1"  # Sicilian Najdorf
```

### Comprehensive Style

```yaml
name: "My Repertoire"
source: classical_openings.pgn
output: my_openings.pgn
settings:
  max_depth: 14

games:
  - index: 1
    action: include
    skip_variations:
      - moves: "6... e5 7. Nde2 Be7 7... b5"
        reason: "Too complex for now"
```

See the `examples/` directory for more working examples.

## 🛠️ Available Commands

```bash
# Inspect a PGN file
pgnc inspect classical_openings.pgn
pgnc inspect classical_openings.pgn --game 1

# Build curated PGN
pgnc build my_config.yaml
pgnc build my_config.yaml --dry-run --stats

# Validate configuration
pgnc validate my_config.yaml

# Generate starter config
pgnc init classical_openings.pgn -o my_config.yaml
```

## 📦 Requirements

- Python 3.8+
- pip

### Dependencies

- `chess>=1.10.0` - PGN parsing and move validation
- `click>=8.1.0` - CLI framework
- `pyyaml>=6.0` - Configuration file parsing
- `pydantic>=2.0.0` - Config validation
- `rich>=13.0.0` - Beautiful terminal output

## 🤝 Contributing

Suggestions and contributions are welcome! Areas for improvement:
- Documentation
- Example configs
- Bug reports
- Feature ideas

## 📄 License

MIT License - Feel free to use for your chess training needs.

## 🙏 Acknowledgments

- Built for coaching chess opening study
- Powered by `python-chess`, `click`, `pydantic`, `rich`, and `pyyaml`
- Inspired by GM comprehensive repertoire files

## 📞 Support

For questions or issues:
1. Review the [examples](examples/)
2. Check the code documentation
3. Open an issue on GitHub

---

**Version**: 0.1.0  
**Status**: ✅ Production Ready  
**Last Updated**: 2025-01-29  

🎯♟️ **Happy Training!**

