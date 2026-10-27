# scratch/test_curiosidade.py
# Teste de integração assíncrona do Motor de Curiosidade e Consolidação REM

import sys
import os
import asyncio

# Adiciona o diretório raiz ao path para poder importar core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.curiosidade import CircuitBreaker, MotorCuriosidade
from main import ConscienciaGeometrica
from core.absorvedor import AbsorvedorCognitivo

async def test_circuit_breaker():
    print("\n=== Testando Circuit Breaker ===")
    cb = CircuitBreaker(max_falhas=3, janela_minutos=1)
    
    # Registra falhas
    print("Registrando 2 falhas...")
    cb.registrar_fail = cb.registrar_falha
    cb.registrar_fail()
    cb.registrar_fail()
    assert not cb.bloqueado, "Não deveria estar bloqueado ainda"
    
    print("Registrando a 3ª falha...")
    cb.registrar_fail()
    assert cb.bloqueado, "Deveria estar bloqueado após 3 falhas"
    print("Circuit Breaker bloqueado com sucesso.")
    
    print("Registrando sucesso...")
    cb.registrar_sucesso()
    assert not cb.bloqueado, "Deveria desbloquear após sucesso"
    print("Circuit Breaker desbloqueado com sucesso.")

async def test_motor_curiosidade_lacunas():
    print("\n=== Testando Análise de Lacunas Topológicas ===")
    milla = ConscienciaGeometrica()
    absorvedor = AbsorvedorCognitivo()
    motor = MotorCuriosidade(milla, absorvedor)
    
    # Inicializa alguns nós com alta energia
    faces_vazio = {str(i): 0.1 for i in range(12)}
    
    # 5 nós sementes para satisfazer o mínimo
    nos = ["Consciência", "Tempo", "Mente", "Redes Neurais", "Geometria"]
    for idx, no_id in enumerate(nos):
        faces = faces_vazio.copy()
        # Adiciona ativação alta para um dos vetores
        faces[str(idx)] = 0.9
        no = milla.instanciar_conceito(no_id, faces, origem="semente")
        no.energia_ativacao = 0.95
        no.frequencia_ativacao = 10
        
    print(f"Grafo inicial criado com {len(milla.grafo.nodes)} nós e {len(milla.grafo.edges)} arestas.")
    
    # Remove arestas para forçar a detecção de furos/componentes desconectados
    milla.grafo.clear_edges()
    print("Arestas removidas para criar lacunas topológicas.")
    
    lacunas = await motor.analisar_lacunas()
    print(f"Lacunas detectadas: {len(lacunas)}")
    for lacuna in lacunas:
        print(f" - Tipo: {lacuna['tipo']}, Prioridade: {lacuna['prioridade']:.3f}, Nós: {lacuna['no_a']} e {lacuna.get('no_b')}")
        
    assert len(lacunas) > 0, "Deveria detectar pelo menos uma lacuna"
    
    # Testa formulação de query
    query = motor._formular_query(lacunas[0])
    print(f"Query formulada para a lacuna principal: '{query}'")
    assert query, "Query não pode ser vazia"

async def test_duckduckgo_scraper():
    print("\n=== Testando Scraper DuckDuckGo HTML ===")
    milla = ConscienciaGeometrica()
    absorvedor = AbsorvedorCognitivo()
    motor = MotorCuriosidade(milla, absorvedor)
    
    query = "hipergrafos e inteligência artificial"
    print(f"Realizando busca assíncrona para: '{query}'...")
    try:
        urls = await motor._buscar_duckduckgo(query)
        print(f"URLs encontradas: {len(urls)}")
        for url in urls:
            print(f" - {url}")
        
        if urls:
            print("Busca DuckDuckGo funcionando com sucesso.")
        else:
            print("Aviso: Nenhuma URL encontrada (pode ser rate limit do IP do runner).")
    except Exception as e:
        print(f"Erro ao buscar no DuckDuckGo: {e}")

async def main():
    await test_circuit_breaker()
    await test_motor_curiosidade_lacunas()
    await test_duckduckgo_scraper()
    print("\nTodos os testes unitários da Fase 3 concluídos!")

if __name__ == "__main__":
    asyncio.run(main())
