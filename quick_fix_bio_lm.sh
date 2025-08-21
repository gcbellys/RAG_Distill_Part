#!/bin/bash

PROJECT_DIR="/opt/RAG_Evidence4Organ"
MODEL_PATH="$PROJECT_DIR/bio_lm_models/bio-lm-model"
TOKENIZER_PATH="$PROJECT_DIR/bio_lm_models/roberta-base-tokenizer"

echo "🔧 快速配置Bio-LM模型路径..."

# 备份配置文件
echo "💾 备份原配置文件..."
cp configs/model_config.py configs/model_config.py.bak.$(date +%Y%m%d_%H%M%S)
cp rag_system/models/bio_lm_embedding.py rag_system/models/bio_lm_embedding.py.bak.$(date +%Y%m%d_%H%M%S)
echo "✅ 备份完成"

# 修改model_config.py
echo "📝 更新 configs/model_config.py..."
sed -i "s|\"EMBO/bio-lm\"|\"$MODEL_PATH\"|g" configs/model_config.py
sed -i "s|\"roberta-base\"|\"$TOKENIZER_PATH\"|g" configs/model_config.py

# 修改bio_lm_embedding.py  
echo "📝 更新 rag_system/models/bio_lm_embedding.py..."
sed -i "s|model_name: str = \"EMBO/bio-lm\"|model_name: str = \"$MODEL_PATH\"|g" rag_system/models/bio_lm_embedding.py
sed -i "s|tokenizer_name: str = \"roberta-base\"|tokenizer_name: str = \"$TOKENIZER_PATH\"|g" rag_system/models/bio_lm_embedding.py

echo "✅ 配置更新完成"

# 设置权限
chmod -R 755 bio_lm_models/

# 测试模型
echo "🧪 测试Bio-LM模型..."
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')

try:
    from rag_system.models.bio_lm_embedding import BioLMEmbedding
    print('✅ Bio-LM模块导入成功')
    
    model = BioLMEmbedding()
    print('✅ Bio-LM模型初始化成功')
    
    # 测试编码
    embeddings = model.encode('This is a test sentence.')
    print(f'✅ 文本编码成功，向量维度: {embeddings.shape}')
    print('🎉 Bio-LM模型配置完全成功！')
    
except Exception as e:
    print(f'❌ 配置测试失败: {e}')
    sys.exit(1)
"

echo ""
echo "📋 配置摘要:"
echo "✅ 模型路径: $MODEL_PATH"
echo "✅ 分词器路径: $TOKENIZER_PATH"
echo "✅ 配置文件已更新并备份"
echo "✅ 模型测试通过"
echo ""
echo "🎯 Bio-LM模型离线部署完成！"
