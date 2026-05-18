import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useConscienciaStore } from '../store/conscienciaStore';
import { useGrafoFisica } from '../hooks/useGrafoFisica';
import type { No } from '../types/consciencia';

export const GrafoNeon: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  
  const { nos, arestas, nosAtivados, caminhoIluminado, faseCognitiva } = useConscienciaStore();
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });
  const [hoveredNode, setHoveredNode] = useState<No | null>(null);
  const [draggedNode, setDraggedNode] = useState<any | null>(null);

  const renderFrameRef = useRef<() => void>(() => {});

  // 1. Invoca a simulação física reativa ao estado cognitivo da Milla
  const { nosFisica, arestasFisica, simulation } = useGrafoFisica(
    nos,
    arestas,
    dimensions.width,
    dimensions.height,
    faseCognitiva,
    nosAtivados,
    () => renderFrameRef.current()
  );

  // 2. Define a função de renderização do frame (Envelopada com tratamento de erro absoluto)
  const renderFrame = useCallback(() => {
    try {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const { width, height } = dimensions;
      ctx.clearRect(0, 0, width, height);

      // Velocidade de fluxo sináptico reativa: frenética no pensamento, suave no sonho
      const speedFactor = faseCognitiva === 'streaming' ? 400 : faseCognitiva === 'sonho' ? 1400 : 800;
      const time = Date.now() / speedFactor;

      // A. Renderizar Arestas (Filamentos de Neon)
      arestasFisica.forEach((edge: any) => {
        const source = edge.source;
        const target = edge.target;
        if (!source || !target || typeof source === 'string' || typeof target === 'string') return;

        // Sanitização estrita de coordenadas contra NaNs
        const sx = typeof source.x === 'number' && !isNaN(source.x) ? source.x : width / 2;
        const sy = typeof source.y === 'number' && !isNaN(source.y) ? source.y : height / 2;
        const tx = typeof target.x === 'number' && !isNaN(target.x) ? target.x : width / 2;
        const ty = typeof target.y === 'number' && !isNaN(target.y) ? target.y : height / 2;

        const weight = edge.peso || 0.5;
        const isHighlighted = nosAtivados && (nosAtivados.includes(source.conceito) || nosAtivados.includes(target.conceito));
        const isInPath = caminhoIluminado && (
          caminhoIluminado.findIndex((c, idx) => c === source.conceito && caminhoIluminado[idx+1] === target.conceito) !== -1 ||
          caminhoIluminado.findIndex((c, idx) => c === target.conceito && caminhoIluminado[idx+1] === source.conceito) !== -1
        );
        const isHifa = edge.tipo === 'hifa';
        const isInsightOnirico = edge.tipo === 'insight_onirico';

        // Animação de fade-out das arestas conectadas a nós sendo podados
        if (source.isFadingOut && !source.fadeStartTime) {
          source.fadeStartTime = Date.now();
        }
        if (target.isFadingOut && !target.fadeStartTime) {
          target.fadeStartTime = Date.now();
        }
        const sOpacity = source.isFadingOut
          ? Math.max(0, 1 - (Date.now() - (source.fadeStartTime || Date.now())) / 2000)
          : 1.0;
        const tOpacity = target.isFadingOut
          ? Math.max(0, 1 - (Date.now() - (target.fadeStartTime || Date.now())) / 2000)
          : 1.0;
        const edgeOpacity = Math.min(sOpacity, tOpacity);

        ctx.save();
        ctx.globalAlpha = edgeOpacity; // Aplica transparência global na aresta

        if (isInsightOnirico) {
          // Desenha linha ondulante fluorescente blue-celeste
          ctx.beginPath();
          const dx = tx - sx;
          const dy = ty - sy;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > 0) {
            const ux = dx / dist;
            const uy = dy / dist;
            const px = -uy;
            const py = ux;
            
            const numSteps = 30;
            const amplitude = 3;
            const wavePhase = (Date.now() / 120) % (Math.PI * 2);
            
            ctx.moveTo(sx, sy);
            for (let step = 1; step <= numSteps; step++) {
              const ratio = step / numSteps;
              const lx = sx + dx * ratio;
              const ly = sy + dy * ratio;
              const offset = Math.sin(ratio * Math.PI * 4 - wavePhase) * amplitude;
              ctx.lineTo(lx + px * offset, ly + py * offset);
            }
          } else {
            ctx.moveTo(sx, sy);
            ctx.lineTo(tx, ty);
          }
          
          ctx.lineWidth = weight * (isHighlighted ? 5 : 3);
          ctx.strokeStyle = `rgba(0, 191, 255, ${0.6 + weight * 0.4})`; // blue-celeste
          ctx.shadowBlur = 18;
          ctx.shadowColor = 'rgba(0, 191, 255, 0.9)';
        } else if (isHifa) {
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(tx, ty);
          ctx.setLineDash([4, 4]);
          ctx.lineWidth = weight * (isHighlighted ? 4 : 2);
          ctx.strokeStyle = isHighlighted 
            ? `rgba(168, 85, 247, ${0.5 + weight * 0.5})` 
            : `rgba(168, 85, 247, ${0.2 + weight * 0.3})`;
          
          ctx.shadowBlur = isHighlighted ? 12 : 5;
          ctx.shadowColor = 'rgba(168, 85, 247, 0.6)';
        } else {
          // Aresta normal sináptica
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(tx, ty);
          ctx.setLineDash([]);
          ctx.lineWidth = weight * (isHighlighted || isInPath ? 4 : 2);
          
          if (isInPath) {
            ctx.strokeStyle = `rgba(255, 255, 0, ${0.6 + weight * 0.4})`;
            ctx.shadowBlur = 15;
            ctx.shadowColor = 'rgba(255, 255, 0, 0.8)';
          } else {
            ctx.strokeStyle = isHighlighted 
              ? `rgba(0, 255, 170, ${0.4 + weight * 0.5})` 
              : `rgba(0, 240, 255, ${0.1 + weight * 0.3})`;
            
            if (isHighlighted) {
              ctx.shadowBlur = 10;
              ctx.shadowColor = 'rgba(0, 255, 170, 0.6)';
            } else {
              ctx.shadowBlur = 4;
              ctx.shadowColor = 'rgba(0, 240, 255, 0.3)';
            }
          }
        }
        
        ctx.stroke();
        ctx.restore();

        // Partículas luminosas fluindo ao longo das arestas (Simulação de sinapse)
        ctx.save();
        ctx.globalAlpha = edgeOpacity; // Aplica transparência global nas partículas
        const dotCount = (faseCognitiva === 'streaming' || isHighlighted) ? 2 : 1;
        for (let i = 0; i < dotCount; i++) {
          const progress = (time + i / dotCount) % 1.0;
          const px = sx + (tx - sx) * progress;
          const py = sy + (ty - sy) * progress;

          if (isInsightOnirico) {
            ctx.fillStyle = '#00bfff';
            ctx.shadowColor = '#00bfff';
          } else if (isHifa) {
            ctx.fillStyle = '#a855f7';
            ctx.shadowColor = '#a855f7';
          } else if (isInPath) {
            ctx.fillStyle = '#ffff00';
            ctx.shadowColor = '#ffff00';
          } else {
            ctx.fillStyle = isHighlighted ? '#00ffaa' : '#00f0ff';
            ctx.shadowColor = isHighlighted ? '#00ffaa' : '#00f0ff';
          }
          ctx.shadowBlur = 6;
          ctx.beginPath();
          ctx.arc(px, py, 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      });

      // B. Renderizar Nós (Estrelas de Energia Pulsantes)
      nosFisica.forEach((node: any) => {
        if (!node || !node.conceito) return;

        // Sanitização estrita de coordenadas do Nó contra NaNs
        const nx = typeof node.x === 'number' && !isNaN(node.x) ? node.x : width / 2;
        const ny = typeof node.y === 'number' && !isNaN(node.y) ? node.y : height / 2;

        const isAtivado = nosAtivados && nosAtivados.includes(node.conceito);
        const isInPathNode = caminhoIluminado && caminhoIluminado.includes(node.conceito);
        const isHovered = hoveredNode?.conceito === node.conceito;
        
        const pulso = Math.sin(Date.now() / 300 + nx * 0.05) * 0.15 + 0.85;
        const baseRadius = 8 + (typeof node.energia === 'number' && !isNaN(node.energia) ? node.energia : 0.5) * 12;
        let radius = baseRadius * pulso;
        if (isNaN(radius) || radius <= 0) radius = 8;

        // Animação de fade-out do nó
        if (node.isFadingOut && !node.fadeStartTime) {
          node.fadeStartTime = Date.now();
        }
        const nodeOpacity = node.isFadingOut
          ? Math.max(0, 1 - (Date.now() - (node.fadeStartTime || Date.now())) / 2000)
          : 1.0;

        ctx.save();
        ctx.globalAlpha = nodeOpacity; // Aplica transparência global no nó (inclui glow, ripples, texto)

        // Glow radial reativo com cores por Origem e Ativação
        const glowGrad = ctx.createRadialGradient(
          nx, ny, 0,
          nx, ny, radius * 3
        );
        
        let glowColor = 'rgba(0, 240, 255, '; // vigília (ciano)
        let coreColor = '#00f0ff';

        if (isInPathNode) {
          glowColor = 'rgba(255, 255, 0, '; // amarelo neon do caminho
          coreColor = '#ffff00';
        } else if (isAtivado) {
          glowColor = 'rgba(0, 255, 170, '; // emerald
          coreColor = '#00ffaa';
        } else if (node.origem === 'desejo') {
          glowColor = 'rgba(255, 0, 127, '; // rosa vibrante (desejo/nutrição)
          coreColor = '#ff007f';
        } else if (node.origem === 'subconsciente') {
          glowColor = 'rgba(168, 85, 247, '; // roxo (evocado do subconsciente)
          coreColor = '#a855f7';
        } else if (node.origem === 'sonho') {
          glowColor = 'rgba(79, 70, 229, '; // indigo (produzido em sonho lúcido)
          coreColor = '#4f46e5';
        } else if (node.origem === 'insight_onirico') {
          glowColor = 'rgba(139, 92, 246, '; // violeta fluorescente (insight onírico)
          coreColor = '#8b5cf6';
        }

        glowGrad.addColorStop(0, `${glowColor}${0.6 * pulso})`);
        glowGrad.addColorStop(0.3, `${glowColor}${0.2 * pulso})`);
        glowGrad.addColorStop(1, `${glowColor}0)`);

        ctx.fillStyle = glowGrad;
        ctx.beginPath();
        ctx.arc(nx, ny, radius * 3, 0, Math.PI * 2);
        ctx.fill();

        // ─── Ondas Consecutivas de Choque Sináptico (Ripples) ───
        if (isInPathNode) {
          const timeFactor = (Date.now() / 600) % 1.0;
          ctx.beginPath();
          ctx.arc(nx, ny, radius * (1.2 + timeFactor * 3.0), 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(255, 255, 0, ${0.5 * (1.0 - timeFactor)})`;
          ctx.lineWidth = 2.0;
          ctx.stroke();
        } else if (isAtivado) {
          const timeFactor = (Date.now() / 600) % 1.0;
          ctx.beginPath();
          ctx.arc(nx, ny, radius * (1.2 + timeFactor * 2.5), 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(0, 255, 170, ${0.45 * (1.0 - timeFactor)})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
        } else if (node.origem === 'sonho') {
          const timeFactor = (Date.now() / 800) % 1.0;
          ctx.beginPath();
          ctx.arc(nx, ny, radius * (1.1 + timeFactor * 2.0), 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(79, 70, 229, ${0.35 * (1.0 - timeFactor)})`;
          ctx.lineWidth = 1.0;
          ctx.stroke();
        } else if (node.origem === 'desejo') {
          const timeFactor = (Date.now() / 700) % 1.0;
          ctx.beginPath();
          ctx.arc(nx, ny, radius * (1.1 + timeFactor * 2.2), 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(255, 0, 127, ${0.35 * (1.0 - timeFactor)})`;
          ctx.lineWidth = 1.0;
          ctx.stroke();
        }

        // Núcleo do nó
        ctx.beginPath();
        ctx.arc(nx, ny, radius * 0.8, 0, Math.PI * 2);
        ctx.fillStyle = isHovered ? '#ffffff' : coreColor;
        ctx.shadowBlur = 15;
        ctx.shadowColor = coreColor;
        ctx.fill();

        // Rótulo de texto do conceito geométrico
        ctx.shadowBlur = 2;
        ctx.shadowColor = '#000';
        ctx.fillStyle = isInPathNode ? '#ffff00' : isAtivado ? '#00ffaa' : '#e2e8f0';
        ctx.font = `bold ${isHovered || isInPathNode ? '13px' : '11px'} 'Outfit', 'Inter', monospace`;
        ctx.textAlign = 'center';
        ctx.fillText(node.conceito, nx, ny - radius - 6);

        // Detalhes extras do nó no hover
        if (isHovered) {
          ctx.fillStyle = '#94a3b8';
          ctx.font = "9px monospace";
          ctx.fillText(`ATV: ${node.ativacoes} | E: ${node.energia.toFixed(2)}`, nx, ny + radius + 14);
        }

        ctx.restore();
      });
    } catch (err) {
      console.error('[GrafoNeon] Erro crítico no loop de renderização do Canvas:', err);
    }
  }, [dimensions, hoveredNode, nosAtivados, caminhoIluminado, nosFisica, arestasFisica, faseCognitiva]);

  // Atualiza a referência mutável para o frame atual do useCallback
  useEffect(() => {
    renderFrameRef.current = renderFrame;
  }, [renderFrame]);

  // Monitora redimensionamento do contêiner
  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setDimensions({
          width: entry.contentRect.width || 600,
          height: entry.contentRect.height || 400
        });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Efeito secundário para forçar redraws contínuos para animações de pulso/partícula
  useEffect(() => {
    let animId: number;
    const loop = () => {
      renderFrame();
      animId = requestAnimationFrame(loop);
    };
    loop();
    return () => cancelAnimationFrame(animId);
  }, [renderFrame]);

  // ─── Interações de Mouse (Hover, Drag and Drop) ───────────────────────────

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    if (draggedNode && simulation) {
      draggedNode.fx = mx;
      draggedNode.fy = my;
      simulation.alphaTarget(0.1).restart();
      return;
    }

    let found: No | null = null;
    for (const node of nosFisica) {
      const dx = node.x - mx;
      const dy = node.y - my;
      const radius = 10 + (node.energia || 0) * 12;
      if (dx * dx + dy * dy < radius * radius * 4) {
        found = node;
        break;
      }
    }
    setHoveredNode(found);
  };

  const handleMouseDown = () => {
    if (hoveredNode) {
      const physicsNode = nosFisica.find(n => n.conceito === hoveredNode.conceito);
      if (physicsNode) {
        physicsNode.fx = physicsNode.x;
        physicsNode.fy = physicsNode.y;
        setDraggedNode(physicsNode);
      }
    }
  };

  const handleMouseUp = () => {
    if (draggedNode && simulation) {
      draggedNode.fx = null;
      draggedNode.fy = null;
      simulation.alphaTarget(0);
      setDraggedNode(null);
    }
  };

  return (
    <div 
      ref={containerRef} 
      className="glass-panel rounded-2xl w-full h-[400px] relative overflow-hidden flex items-center justify-center"
    >
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-1">
        <span className="text-[10px] font-mono font-bold tracking-widest text-cyan-400 uppercase">
          Matriz Topológica Reativa
        </span>
        <span className="text-[9px] font-mono text-slate-500 uppercase">
          Dinâmica Física Adaptada às Fases Cognitivas & Concentradores Ativos
        </span>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="block cursor-grab active:cursor-grabbing w-full h-full"
      />
    </div>
  );
};
