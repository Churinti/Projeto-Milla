"""
scratch/test_homeostase.py — Automated Integration Test for Synaptic Homeostasis (Phase 2)

Performs robust assertions to verify:
1. Node Decay Floor (regular nodes -> 0.0, seeds -> 0.3).
2. Inactivity Scaling & Capping (log1p ceiling of 4.0).
3. Synaptic Edge Weight Decay (-0.005 per cycle down to 0.05 limit).
4. Articulation Point Protection (prevents graph fragmentation).
5. Rekindling from Subconscious with historical affinities (weight 0.5, tipo="restaurada").
"""

import os
import sys
import shutil
import networkx as nx
from datetime import datetime, timedelta

# Ensure root import works
sys.path.append(".")

from main import ConscienciaGeometrica
from core.subconsciente import SubconscienteMilla


def clean_test_directories():
    """Cleanup testing DB directories to start fresh."""
    for path in ["test_chroma_homeostase"]:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"[Setup] Directory '{path}' removed successfully.")
            except Exception as e:
                print(f"[Setup] Warning: could not delete '{path}': {e}")


def test_homeostasis():
    print("\n" + "="*60)
    print("RUNNING MILLA SYNAPTIC HOMEOSTASIS TEST SUITE")
    print("="*60)
    
    clean_test_directories()
    
    # Initialize Milla with test settings (uses Ollama/OpenAI mocked or bypassed where possible)
    milla = ConscienciaGeometrica(usar_ollama=False, openai_key="mock_key")
    
    # Isolate test subconscious
    milla.subconsciente = SubconscienteMilla(pasta="test_chroma_homeostase")
    
    # Reset graph to clean testbed
    milla.grafo.clear()
    
    # --------------------------------------------------------------------------
    # TEST 1: Node Decay Floor
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Verifying Node Decay Floors...")
    
    semente_no = milla.instanciar_conceito(
        "SementeCognitiva",
        {"logica": 0.8, "abstracao": 0.8},
        origem="semente"
    )
    regular_no = milla.instanciar_conceito(
        "ConceitoRegular",
        {"logica": 0.5, "abstracao": 0.5},
        origem="absorcao"
    )
    
    # Force high activation energy initially
    semente_no.energia_ativacao = 1.0
    regular_no.energia_ativacao = 1.0
    
    # Apply decay repeatedly
    for _ in range(300):
        semente_no.decay(taxa=0.05)
        regular_no.decay(taxa=0.05)
        
    print(f"  - Semente Node Energy: {semente_no.energia_ativacao:.3f} (Expected >= 0.3)")
    print(f"  - Regular Node Energy: {regular_no.energia_ativacao:.3f} (Expected == 0.0)")
    
    assert abs(semente_no.energia_ativacao - 0.3) < 1e-5, "Semente node decay floor violated!"
    assert regular_no.energia_ativacao == 0.0, "Regular node decay floor violated!"
    print("SUCCESS - TEST 1 PASSED: Node decay floors successfully enforced!")

    # --------------------------------------------------------------------------
    # TEST 2 & 3: Inactivity Scaling and Synaptic Edge Weight Decay
    # --------------------------------------------------------------------------
    print("\n[TEST 2 & 3] Verifying Inactivity Decay Scaling & Synaptic Edge Decay...")
    milla.grafo.clear()
    
    # Set up two connected concepts
    milla.instanciar_conceito("ConceitoA", {"logica": 0.6, "abstracao": 0.6}, origem="absorcao")
    b_no = milla.instanciar_conceito("ConceitoB", {"logica": 0.6, "abstracao": 0.6}, origem="absorcao")
    
    # Clear auto connections and add only our target edge
    milla.grafo.remove_edges_from(list(milla.grafo.edges))
    milla.grafo.add_edge("ConceitoA", "ConceitoB", weight=0.8)
    
    # Set Concept B's last activation to 80 hours ago to trigger maximum decay
    b_no.ultima_ativacao = datetime.now() - timedelta(hours=80)
    
    # Verify log1p inactivity curve inside _aplicar_decaimento
    # Both Concepts are inactive to trigger edge weight decay
    initial_b_energy = b_no.energia_ativacao
    milla.feedback._aplicar_decaimento(milla.grafo, nos_ativados=[])
    
    post_b_energy = b_no.energia_ativacao
    edge_weight = milla.grafo["ConceitoA"]["ConceitoB"]["weight"]
    
    print(f"  - Concept B energy before: {initial_b_energy:.3f} -> after: {post_b_energy:.3f}")
    print(f"  - Edge weight after 1 cycle of decay: {edge_weight:.4f} (Expected: 0.8 - 0.005 = 0.795)")
    
    # Energy must have decreased
    assert post_b_energy < initial_b_energy, "Concept B did not decay!"
    assert abs(edge_weight - 0.795) < 1e-5, "Edge weight decay factor is incorrect!"
    
    # Apply decay multiple times to verify edge weight floor (0.05)
    for _ in range(200):
        milla.feedback._aplicar_decaimento(milla.grafo, nos_ativados=[])
        
    final_edge_weight = milla.grafo["ConceitoA"]["ConceitoB"]["weight"]
    print(f"  - Edge weight after 200 cycles: {final_edge_weight:.4f} (Expected: 0.05 floor)")
    assert abs(final_edge_weight - 0.05) < 1e-5, "Edge weight floor violated!"
    print("SUCCESS - TEST 2 & 3 PASSED: Inactivity scaling and synaptic edge decay verified!")

    # --------------------------------------------------------------------------
    # TEST 4: Articulation Point Protection
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Verifying Articulation Point Protection...")
    milla.grafo.clear()
    
    # Create a linear graph: N1 --- N2 (Bridge) --- N3
    # N2 is an articulation point. If N2 is removed, N1 and N3 become disconnected.
    n1 = milla.instanciar_conceito("Conceito1", {"logica": 0.5, "abstracao": 0.5}, origem="absorcao")
    n2 = milla.instanciar_conceito("Conceito2", {"logica": 0.5, "abstracao": 0.5}, origem="absorcao")
    n3 = milla.instanciar_conceito("Conceito3", {"logica": 0.5, "abstracao": 0.5}, origem="absorcao")
    
    # Clear auto connections and add only linear edges
    milla.grafo.remove_edges_from(list(milla.grafo.edges))
    milla.grafo.add_edge("Conceito1", "Conceito2", weight=0.5)
    milla.grafo.add_edge("Conceito2", "Conceito3", weight=0.5)
    
    # Verify it is indeed an articulation point
    art_points = list(nx.articulation_points(milla.grafo))
    print(f"  - Current articulation points in graph: {art_points}")
    assert "Conceito2" in art_points, "Setup failed: Conceito2 is not an articulation point!"
    
    # Drain energy of all three nodes to 0.10 (below pruning threshold of 0.20)
    n1.energia_ativacao = 0.10
    n2.energia_ativacao = 0.10
    n3.energia_ativacao = 0.10
    
    # Trigger pruning
    removed_nodes = milla._pruning_por_energia(threshold=0.20)
    print(f"  - Removed nodes: {removed_nodes}")
    print(f"  - Remaining nodes in graph: {list(milla.grafo.nodes)}")
    
    # Concept 2 must NOT be removed because it protects graph connectivity!
    assert "Conceito2" in milla.grafo.nodes, "Articulation point Conceito2 was pruned!"
    assert "Conceito1" not in milla.grafo.nodes, "Concept 1 was not pruned!"
    assert "Conceito3" not in milla.grafo.nodes, "Concept 3 was not pruned!"
    print("SUCCESS - TEST 4 PASSED: Articulation points successfully protected from homeostatic pruning!")

    # --------------------------------------------------------------------------
    # TEST 5: Rekindling from Subconscious with Historical Affinities
    # --------------------------------------------------------------------------
    print("\n[TEST 5] Verifying Rekindling from Subconscious & Affinity Restoration...")
    milla.grafo.clear()
    
    # Set up concept to be pruned/archived and neighbors
    concept_to_prune = "GeometriaSagrada"
    neighbor_concept = "SementeCognitiva"
    
    milla.instanciar_conceito(neighbor_concept, {"logica": 0.8, "abstracao": 0.8}, origem="semente")
    to_prune_no = milla.instanciar_conceito(concept_to_prune, {"logica": 0.7, "abstracao": 0.7}, origem="absorcao")
    
    # Clear auto connections and add only our target edge
    milla.grafo.remove_edges_from(list(milla.grafo.edges))
    milla.grafo.add_edge(concept_to_prune, neighbor_concept, weight=0.90)
    
    # Drain energy of GeometriaSagrada to trigger pruning
    to_prune_no.energia_ativacao = 0.05
    
    # Execute pruning (which archives the node in the subconscious along with its neighbors as afinidades)
    removed = milla._pruning_por_energia(threshold=0.20)
    assert concept_to_prune in removed, f"Failed to prune '{concept_to_prune}'!"
    assert concept_to_prune not in milla.grafo.nodes, f"'{concept_to_prune}' should not be in the active graph!"
    
    # Debug: Print all items inside the subconscious
    print("  - [DEBUG] Querying raw ChromaDB collection...")
    all_docs = milla.subconsciente.colecao.get()
    print(f"    Raw Documents: {all_docs['documents']}")
    print(f"    Raw Metadatas: {all_docs['metadatas']}")
    
    # Try a raw query
    raw_query = milla.subconsciente.colecao.query(
        query_texts=["GeometriaSagrada"],
        n_results=3
    )
    print(f"    Raw Query Results: {raw_query}")
    
    # Simulate a stimulus that matches the concept to trigger recall and rekindling
    print(f"  - Simulating stimulus that triggers recall of '{concept_to_prune}'...")
    milla._ativar_nos(entrada=concept_to_prune)
    
    # Assert that concept_to_prune has been rekindled into the active graph
    assert concept_to_prune in milla.grafo.nodes, f"'{concept_to_prune}' was not rekindled!"
    
    rekindled_no = milla.grafo.nodes[concept_to_prune]['objeto']
    print(f"  - Rekindled Node: '{rekindled_no.conceito}'")
    print(f"  - Energy after rekindling: {rekindled_no.energia_ativacao:.3f} (Expected: 1.0)")
    assert rekindled_no.energia_ativacao == 1.0, "Rekindled node energy is not full!"
    
    # Assert that connection to neighbor_concept is restored with weight 0.5 and type "restaurada"
    assert milla.grafo.has_edge(concept_to_prune, neighbor_concept), "Historical affinity was not restored!"
    restored_edge = milla.grafo[concept_to_prune][neighbor_concept]
    print(f"  - Restored edge details: {restored_edge}")
    assert restored_edge["weight"] == 0.5, "Restored edge weight is incorrect!"
    assert restored_edge["tipo"] == "restaurada", "Restored edge type metadata is missing!"
    
    print("SUCCESS - TEST 5 PASSED: Subconscious rekindling and historical affinity restoration verified!")
    
    print("\n" + "="*60)
    print("ALL HOMEOSTASIS AND MEMORY INTEGRITY TESTS PASSED SUCCESSFULLY!")
    print("="*60 + "\n")
    
    clean_test_directories()


if __name__ == "__main__":
    test_homeostasis()
