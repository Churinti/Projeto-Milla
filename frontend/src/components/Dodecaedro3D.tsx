import React, { useRef, useEffect } from 'react';
import { useConscienciaStore } from '../store/conscienciaStore';
import type { FaseCognitiva } from '../types/consciencia';
import * as THREE from 'three';

interface ThemaDodecaedro {
  cor: number;
  emissiva: number;
  velocidadeRotacao: number;
  escala: number;
}

const TEMAS: Record<FaseCognitiva, ThemaDodecaedro> = {
  vigilia: {
    cor: 0x00ffcc,
    emissiva: 0x004444,
    velocidadeRotacao: 0.25,
    escala: 1.0
  },
  hipnagogia: {
    cor: 0x8844ff,
    emissiva: 0x220044,
    velocidadeRotacao: 0.12,
    escala: 1.0
  },
  sonho: {
    cor: 0x4400ff,
    emissiva: 0x110033,
    velocidadeRotacao: 0.06,
    escala: 1.05  // leve expansão — respiração onírica
  },
  consolidacao: {
    cor: 0xff8800,
    emissiva: 0x442200,
    velocidadeRotacao: 0.08,
    escala: 0.95  // compressão — memórias sendo consolidadas
  },
  sono_profundo: {
    cor: 0x220066,
    emissiva: 0x000011,
    velocidadeRotacao: 0.02,
    escala: 0.85
  },
  pre_pensamento: {
    cor: 0x00aaff,
    emissiva: 0x002244,
    velocidadeRotacao: 0.35,
    escala: 1.0
  },
  streaming: {
    cor: 0xaa00ff,
    emissiva: 0x330044,
    velocidadeRotacao: 1.6,
    escala: 1.08
  },
  pos_pensamento: {
    cor: 0x00ffaa,
    emissiva: 0x004422,
    velocidadeRotacao: 0.4,
    escala: 1.02
  },
  idle: {
    cor: 0x00f0ff,
    emissiva: 0x001122,
    velocidadeRotacao: 0.25,
    escala: 1.0
  },
  despertando: {
    cor: 0xffaa44,
    emissiva: 0x332200,
    velocidadeRotacao: 0.18,
    escala: 0.98
  },
  desperto: {
    cor: 0x00ffcc,
    emissiva: 0x004444,
    velocidadeRotacao: 0.25,
    escala: 1.0
  }
};

export const Dodecaedro3D: React.FC = () => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  
  const { estado, faseCognitiva, isStreaming } = useConscienciaStore();
  
  // Guardamos o estado em referências para evitar reconstruir a cena Three.js
  const estadoRef = useRef(estado);
  const faseRef = useRef(faseCognitiva);
  const streamingRef = useRef(isStreaming);

  useEffect(() => {
    estadoRef.current = estado;
    faseRef.current = faseCognitiva;
    streamingRef.current = isStreaming;
  }, [estado, faseCognitiva, isStreaming]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const width = mount.clientWidth || 300;
    const height = mount.clientHeight || 300;

    // 1. Scene, Camera, Renderer Setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 5.5;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    // 2. Iluminação
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x00f0ff, 1.5);
    dirLight1.position.set(5, 5, 5);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xff007f, 1.2);
    dirLight2.position.set(-5, -5, 5);
    scene.add(dirLight2);

    // 3. Geometrias & Malhas do Sólido Platônico
    const coreGeom = new THREE.DodecahedronGeometry(1.3, 0);
    const coreMat = new THREE.MeshPhongMaterial({
      color: 0x00f0ff,
      emissive: 0x002233,
      transparent: true,
      opacity: 0.65,
      shininess: 80,
      flatShading: true
    });
    const coreMesh = new THREE.Mesh(coreGeom, coreMat);
    scene.add(coreMesh);

    const shellGeom = new THREE.DodecahedronGeometry(1.35, 0);
    const shellMat = new THREE.MeshBasicMaterial({
      color: 0x00ffaa,
      wireframe: true,
      transparent: true,
      opacity: 0.45
    });
    const shellMesh = new THREE.Mesh(shellGeom, shellMat);
    scene.add(shellMesh);

    const pointsGeom = new THREE.DodecahedronGeometry(1.35, 0);
    const pointsMat = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.08,
      transparent: true,
      opacity: 0.8
    });
    const pointsMesh = new THREE.Points(pointsGeom, pointsMat);
    scene.add(pointsMesh);

    // 4. Loop de Animação Reativa
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Métricas ativas obtidas via Ref
      const est = estadoRef.current;
      const streamAct = streamingRef.current;
      const fase = faseRef.current;

      // Obtém o tema correspondente à fase atual
      const tema = TEMAS[fase] || TEMAS.idle;
      const rotSpeed = tema.velocidadeRotacao;
      
      coreMesh.rotation.y = elapsedTime * rotSpeed;
      coreMesh.rotation.x = elapsedTime * rotSpeed * 0.5;
      
      shellMesh.rotation.y = elapsedTime * rotSpeed * 0.95;
      shellMesh.rotation.x = elapsedTime * rotSpeed * 0.45;
      
      pointsMesh.rotation.y = elapsedTime * rotSpeed * 0.95;
      pointsMesh.rotation.x = elapsedTime * rotSpeed * 0.45;

      // Pulsação e escala reativa com base no Desejo e no tema
      const pulseFactor = Math.sin(elapsedTime * (streamAct ? 8 : 2)) * 0.05 + 0.95;
      const baseScale = (0.9 + est.nivel_consciencia * 0.3) * tema.escala;
      const targetScale = baseScale * pulseFactor;
      
      coreMesh.scale.set(targetScale, targetScale, targetScale);
      shellMesh.scale.set(targetScale, targetScale, targetScale);
      pointsMesh.scale.set(targetScale, targetScale, targetScale);

      // Dinâmica de cores baseada no Tema da Fase
      coreMat.color.setHex(tema.cor);
      shellMat.color.setHex(tema.cor);
      coreMat.emissive.setHex(tema.emissiva);

      renderer.render(scene, camera);
    };

    animate();

    // 5. Tratamento de Redimensionamento do Canvas
    const handleResize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    
    window.addEventListener('resize', handleResize);

    // 6. Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }
      
      coreGeom.dispose();
      coreMat.dispose();
      shellGeom.dispose();
      shellMat.dispose();
      pointsGeom.dispose();
      pointsMat.dispose();
      renderer.dispose();
    };
  }, []);

  // Determina texto do status com base na fase cognitiva
  const getFaseStatus = (fase: FaseCognitiva) => {
    switch (fase) {
      case 'hipnagogia': return '💤 Desacelerando (Hipnagogia)';
      case 'consolidacao': return '🟠 Consolidando Subconsciente';
      case 'sonho': return '🔮 Sonho Lúcido Ativo';
      case 'sono_profundo': return '🌌 Sono Profundo (Consolidado)';
      case 'streaming': return '🧠 Pensamento em Streaming';
      case 'pre_pensamento': return '⚡ Pré-Pensamento';
      case 'pos_pensamento': return '♻️ Plasticidade Reativa';
      case 'despertando': return '🌅 Despertando Consciência';
      case 'desperto': return '🟢 Estado Acordado (Vigília)';
      default: return '🟢 Estado Acordado (Vigília)';
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col items-center justify-center relative overflow-hidden h-[400px]">
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-1">
        <span className="text-[10px] font-mono font-bold tracking-widest text-cyan-400 uppercase">
          Núcleo Holográfico 3D
        </span>
        <span className="text-[9px] font-mono text-slate-500 uppercase">
          {getFaseStatus(faseCognitiva)}
        </span>
      </div>

      {/* Container de Montagem Three.js */}
      <div ref={mountRef} className="w-full h-full flex items-center justify-center cursor-pointer" />
    </div>
  );
};
