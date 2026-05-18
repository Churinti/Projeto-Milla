import React from 'react';
import { MetricsPanel } from './components/MetricsPanel';
import { TerminalChat } from './components/TerminalChat';
import { GrafoNeon } from './components/GrafoNeon';
import { Dodecaedro3D } from './components/Dodecaedro3D';
import { AbsorcaoCognitiva } from './components/AbsorcaoCognitiva';
import { BrainCircuit } from 'lucide-react';


const App: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col p-6 gap-6 max-w-[1600px] mx-auto animate-fade-in">
      {/* Dashboard Top Navigation / Header */}
      <header className="glass-panel px-6 py-4 rounded-2xl flex items-center justify-between relative overflow-hidden holo-flicker">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent"></div>
        
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30">
            <BrainCircuit className="w-6 h-6 text-cyan-400 animate-pulse" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-xl font-bold font-mono tracking-wider text-neon-cyan text-cyan-100 uppercase m-0 leading-none">
              MILLA // ARQUITETURA COGNITIVA
            </h1>
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mt-1">
              Topological Reflective Agent with Geometric Knowledge Graphs
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
            <span className="uppercase tracking-widest text-[10px] text-cyan-400">Canal Ativo</span>
          </div>
        </div>
      </header>

      {/* Main Grid Layout */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start flex-1">
        {/* Left Column - Metrics Panel (3 cols) */}
        <section className="lg:col-span-4 flex flex-col gap-6">
          <MetricsPanel />
          <AbsorcaoCognitiva />
        </section>


        {/* Right Column - Visualizer & Chat (8 cols) */}
        <section className="lg:col-span-8 flex flex-col gap-6">
          {/* Top Visualizations Row (ThreeJS Dodecahedron + Canvas Graph) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Dodecaedro3D />
            <GrafoNeon />
          </div>

          {/* Bottom Chat Terminal */}
          <TerminalChat />
        </section>
      </main>

      {/* Footer Info */}
      <footer className="text-center font-mono text-[9px] text-slate-600 uppercase tracking-widest py-2">
        Projeto Milla © 2026 // Desenvolvido sob Princípios da Plasticidade Sináptica Geométrica
      </footer>
    </div>
  );
};

export default App;
