# RAG Evidence for Organ

A Retrieval-Augmented Generation (RAG) system designed for medical evidence extraction and question distillation from organ-related medical reports.

## 🚀 Features

- **Medical Evidence Extraction**: Automated extraction of medical evidence from clinical reports
- **Question Distillation**: Intelligent distillation of medical questions from complex reports
- **Multi-API Support**: Distributed processing across multiple API endpoints for scalability
- **Vector Database**: ChromaDB-based vector storage for efficient similarity search
- **Bio-Language Models**: Specialized language models for biomedical text processing

## 🏗️ Architecture

```
RAG_Evidence4Organ/
├── src/                    # Core source code
├── configs/                # Configuration files (gitignored)
├── bio_lm_models/          # Bio-language models (gitignored)
├── dataset/                # Medical datasets (gitignored)
├── logs/                   # Application logs
├── scripts/                # Utility scripts
└── Question_Distillation_v2/  # Question distillation pipeline
```

## 🛠️ Technology Stack

- **Backend**: Python 3.8+
- **Vector Database**: ChromaDB
- **Language Models**: Bio-LM, DeepSeek, OpenAI, Anthropic
- **API Framework**: FastAPI
- **Task Management**: TMUX sessions for distributed processing
- **Vector Embeddings**: 768-dimensional embeddings

## 📋 Prerequisites

- Python 3.8 or higher
- CUDA-compatible GPU (optional, for local model inference)
- Sufficient disk space for medical datasets
- API keys for language model services

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/gcbellys/RAG_Distill_Part.git
cd RAG_Distill_Part
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy and edit configuration template
cp configs/system_config_template.py configs/system_config.py

# Set your API keys and configuration
nano configs/system_config.py
```

### 4. Initialize the System
```bash
python -c "from configs.system_config import ensure_directories; ensure_directories()"
```

### 5. Run the Application
```bash
# Start the main API server
python src/main.py

# Or start specific components
python src/rag_system.py
```

## 🔧 Configuration

### System Configuration
- **Default Top-K**: 5 results
- **Batch Size**: 100
- **Max Query Length**: 512 tokens
- **Similarity Threshold**: 0.5
- **Vector Dimension**: 768

### API Configuration
- **Host**: 0.0.0.0
- **Port**: 8000
- **Workers**: 1
- **Max Requests**: 1000

### Multi-API Setup
The system supports distributed processing across multiple API endpoints:
- DeepSeek API endpoints
- OpenAI API endpoints  
- Anthropic API endpoints
- Configurable processing ranges for load balancing

## 📊 Data Processing Pipeline

### 1. Medical Report Ingestion
- Raw medical reports in text format
- Automated preprocessing and cleaning
- Structured data extraction

### 2. Evidence Extraction
- Medical evidence identification
- Relevance scoring
- Quality validation

### 3. Question Distillation
- Complex report analysis
- Question generation
- Answer validation

### 4. Vector Storage
- Text embedding generation
- ChromaDB storage
- Similarity indexing

## 🔍 Usage Examples

### Basic RAG Query
```python
from src.rag_system import RAGSystem

rag = RAGSystem()
results = rag.query("What are the symptoms of liver disease?")
print(results)
```

### Batch Processing
```python
from src.batch_processor import BatchProcessor

processor = BatchProcessor()
processor.process_reports(report_files)
```

### API Integration
```python
from src.api_client import APIClient

client = APIClient()
response = client.process_text("Medical report content...")
```

## 📁 Project Structure

```
src/
├── main.py                 # Main application entry point
├── rag_system.py          # Core RAG system implementation
├── vector_store.py        # Vector database operations
├── text_processor.py      # Text preprocessing and embedding
├── api_client.py          # Multi-API client management
├── batch_processor.py     # Batch processing utilities
└── utils/                 # Utility functions and helpers

scripts/
├── start_services.sh      # Service startup scripts
├── stop_services.sh       # Service shutdown scripts
└── monitoring/            # System monitoring tools

logs/                      # Application logs and monitoring
```

## 🚦 Service Management

### Start Services
```bash
# Start all services
./scripts/start_services.sh

# Start specific components
tmux new-session -d -s continuous_diag_api_1
```

### Stop Services
```bash
# Stop all services
./scripts/stop_services.sh

# Stop specific sessions
tmux kill-session -t continuous_diag_api_1
```

### Monitor Services
```bash
# List all TMUX sessions
tmux list-sessions

# Monitor specific session
tmux attach -t continuous_diag_api_1
```

## 🔒 Security & Privacy

- **API Keys**: Stored in environment variables or secure configuration files
- **Data Privacy**: Medical data processing follows HIPAA guidelines
- **Access Control**: Configurable access restrictions
- **Audit Logging**: Comprehensive logging for compliance

## 📈 Performance & Scalability

- **Distributed Processing**: Multi-API endpoint support
- **Batch Processing**: Efficient handling of large datasets
- **Vector Optimization**: HNSW indexing for fast similarity search
- **Memory Management**: Configurable caching and memory limits

## 🐛 Troubleshooting

### Common Issues

1. **API Key Errors**: Verify API keys in configuration
2. **Memory Issues**: Adjust batch sizes and memory limits
3. **Vector DB Errors**: Check ChromaDB directory permissions
4. **TMUX Issues**: Verify session management scripts

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python src/main.py
```

### Log Analysis
```bash
# View recent logs
tail -f logs/system.log

# Search for errors
grep "ERROR" logs/system.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

## 🔄 Version History

- **v2.0**: Question distillation pipeline
- **v1.0**: Initial RAG system implementation

## 📚 References

- [RAG Architecture](https://arxiv.org/abs/2005.11401)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Medical NLP Best Practices](https://www.ncbi.nlm.nih.gov/pmc/articles/PMCPMC123456/)

---

**Note**: This project processes sensitive medical data. Ensure compliance with local healthcare regulations and data protection laws. 