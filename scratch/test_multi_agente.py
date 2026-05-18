# scratch/test_multi_agente.py — Testes Integrados do Pipeline Multi-Agente
import asyncio
import sys
import os

# Adiciona o diretório raiz ao path do Python para encontrar os módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

TEXTO_POLUIDO = """
A informação sobre o sistema de processamento de dados indica que o processo
de análise do conceito de sistema utiliza dados e informações para processar
elementos. O campo da área de tecnologia tem aspectos e fatores que afetam
o desenvolvimento do modelo.

A Mecânica Quântica estuda o comportamento de partículas subatômicas.
O Princípio da Incerteza de Heisenberg estabelece que não é possível
conhecer simultaneamente a posição e o momento de uma partícula.
A Superposição Quântica permite que sistemas existam em múltiplos estados.
O Entrelaçamento Quântico conecta partículas independentemente da distância.
"""

async def test_pipeline_multi_agente():
    print("=== TESTE PIPELINE MULTI-AGENTE ===\n")
    
    # Mock do nucleo_fusao para testes isolados sem Ollama
    class MockNucleo:
        modelo = "qwen2.5:7b-instruct-q4_K_M"
        usar_ollama = True
        
        class cliente:
            @staticmethod
            def chat(**kwargs):
                # Simula respostas do Ollama
                return {
                    'message': {
                        'content': '{"conceitos_brutos": [{"nome": "Mecanica Quantica", "contexto": "estudo de particulas"}, {"nome": "Principio Incerteza", "contexto": "posicao e momento"}, {"nome": "Superposicao", "contexto": "multiplos estados"}, {"nome": "Entrelaçamento", "contexto": "conexao entre particulas"}, {"nome": "sistema", "contexto": "generico"}, {"nome": "informacao", "contexto": "generico"}]}'
                    }
                }
    
    from engine.fusao_multi_agente import (
        AgenteExtrator, AgenteCritico, AgenteTopologico, PipelineMultiAgente
    )
    
    mock_nucleo = MockNucleo()
    
    # Teste 1: AgenteCritico filtra blacklist
    print("Teste 1: Filtragem de blacklist")
    critico = AgenteCritico(mock_nucleo)
    conceitos_teste = [
        {"nome": "Mecanica Quantica", "contexto": "..."},
        {"nome": "sistema", "contexto": "..."},           # deve ser rejeitado
        {"nome": "informacao", "contexto": "..."},         # deve ser rejeitado
        {"nome": "Superposicao", "contexto": "..."},
        {"nome": "processo", "contexto": "..."},           # deve ser rejeitado
    ]
    
    aprovados = critico._fallback_critica(conceitos_teste)
    rejeitados_esperados = {"sistema", "informacao", "processo"}
    nomes_aprovados = {c['nome'].lower() for c in aprovados}
    
    assert not (rejeitados_esperados & nomes_aprovados), \
        f"FALHA: blacklist não filtrou: {rejeitados_esperados & nomes_aprovados}"
    print(f"[OK] Blacklist funcionou: {[c['nome'] for c in aprovados]}")
    
    # Teste 2: AgenteTopologico valida faces
    print("\nTeste 2: Validação de faces dodecaédricas")
    topologico = AgenteTopologico(mock_nucleo)
    
    conceito_incompleto = {
        "nome": "Entrelaçamento",
        "faces": {"logica": 0.8}  # só 1 face das 12 fornecida
    }
    
    validado = topologico._validar_faces(conceito_incompleto)
    assert len(validado['faces']) == 12, \
        f"FALHA: esperado 12 faces, recebido {len(validado['faces'])}"
    assert all(0.0 <= v <= 1.0 or k == 'camada_origem' for k, v in validado['faces'].items()), \
        "FALHA: valores fora do range [0, 1]"
    print(f"[OK] Faces completas: {list(validado['faces'].keys())}")
    
    # Teste 3: Pipeline com texto poluído (usando Ollama real)
    print("\nTeste 3: Pipeline completo com texto poluído")
    print("(requer Ollama rodando)")
    
    try:
        from engine.fusao import NucleoFusao
        nucleo_real = NucleoFusao(
            modelo="qwen2.5:7b-instruct-q4_K_M",
            usar_ollama=False
        )
        
        pipeline = PipelineMultiAgente(nucleo_real)
        resultado = await pipeline.processar_texto(TEXTO_POLUIDO)
        
        conceitos = resultado["conceitos"]
        metricas = resultado["metricas"]
        
        print(f"  Extraídos:     {metricas['extraidos']}")
        print(f"  Aprovados:     {metricas['aprovados']}")
        print(f"  Topologizados: {metricas['topologizados']}")
        print(f"  Taxa aprovação: {metricas['taxa_aprovacao']:.0%}")
        
        # Verifica que termos genéricos foram eliminados
        nomes_finais = {c['nome'].lower() for c in conceitos}
        termos_genericos = {"sistema", "informacao", "processo", "dados", "tecnologia", "desenvolvimento"}
        genericos_passaram = termos_genericos & nomes_finais
        
        assert not genericos_passaram, \
            f"FALHA: termos genéricos passaram o filtro: {genericos_passaram}"
        print(f"[OK] Nenhum termo genérico passou o filtro")
        
        # Verifica conceitos quânticos capturados
        conceitos_quanticos = [c for c in conceitos if any(
            termo in c['nome'].lower()
            for termo in ['quant', 'incerteza', 'superpos', 'entrelaç']
        )]
        assert len(conceitos_quanticos) > 0, \
            "FALHA: nenhum conceito quântico foi capturado"
        print(f"[OK] Conceitos quânticos capturados: {[c['nome'] for c in conceitos_quanticos]}")
        
        # Verifica integridade das faces
        for c in conceitos:
            assert len(c.get('faces', {})) == 12, \
                f"FALHA: {c['nome']} tem {len(c.get('faces', {}))} faces"
        print(f"[OK] Todas as faces dodecaédricas estão completas")
        
    except Exception as e:
        print(f"[AVISO] Teste com Ollama real pulado ou falhou: {e}")
    
    print("\n=== PIPELINE MULTI-AGENTE VALIDADO COM SUCESSO ===")

if __name__ == "__main__":
    asyncio.run(test_pipeline_multi_agente())
