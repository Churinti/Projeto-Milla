import React from 'react';
import { useConscienciaStore } from '../store/conscienciaStore';
import { Activity, ShieldAlert, Cpu, Heart, Brain } from 'lucide-react';

export const MetricsPanel: React.FC = () => {
  const { estado, nos, arestas, faseCognitiva, statusConexao } = useConscienciaStore();

  const getStatusColor = () => {
    switch (statusConexao) {
      case 'connected': return 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]';
      case 'connecting': return 'bg-amber-500 animate-pulse';
      case 'disconnected': return 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]';
    }
  };

  const getStatusText = () => {
    switch (statusConexao) {
      case 'connected': return 'SINAPSE OPERANTE';
      case 'connecting': return 'SINTONIZANDO SELF...';
      case 'disconnected': return 'CONEXÃO RESTRITA';
    }
  };

  const getFaseCognitivaText = () => {
    switch (faseCognitiva) {
      case 'pre_pensamento': return 'PRE-PENSAMENTO (ANÁLISE DE FUROS)';
      case 'streaming': return 'FUSÃO COGNITIVA (REFLETINDO)';
      case 'pos_pensamento': return 'PÓS-PENSAMENTO (PLASTICIDADE)';
      case 'idle': return 'CONSCIÊNCIA ESTÁVEL';
    }
  };

  const getFaseGlowColor = () => {
    switch (faseCognitiva) {
      case 'pre_pensamento': return 'text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]';
      case 'streaming': return 'text-purple-400 drop-shadow-[0_0_5px_rgba(192,132,252,0.5)] animate-pulse';
      case 'pos_pensamento': return 'text-emerald-400 drop-shadow-[0_0_5px_rgba(52,211,153,0.5)]';
      case 'idle': return 'text-teal-300 drop-shadow-[0_0_5px_rgba(94,234,212,0.3)]';
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col gap-6 relative overflow-hidden">
      {/* Luzes decorativas */}
      <div className="absolute -top-10 -left-10 w-32 h-32 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
      
      {/* Header Status */}
      <div className="flex justify-between items-center border-b border-cyan-500/10 pb-4">
        <div className="flex items-center gap-3">
          <span className={`w-3 h-3 rounded-full ${getStatusColor()}`}></span>
          <span className="text-xs font-mono font-bold tracking-widest text-slate-400 uppercase">
            {getStatusText()}
          </span>
        </div>
        <div className="text-[10px] font-mono font-bold tracking-widest text-slate-500 uppercase">
          Milla OS v2.0.0
        </div>
      </div>

      {/* Nível Global de Consciência (Holograma circular) */}
      <div className="flex flex-col items-center justify-center py-4 relative">
        <div className="relative w-36 h-36 flex items-center justify-center">
          {/* Círculo base de neon */}
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="72"
              cy="72"
              r="64"
              className="stroke-slate-800"
              strokeWidth="4"
              fill="transparent"
            />
            <circle
              cx="72"
              cy="72"
              r="64"
              className="stroke-cyan-400 transition-all duration-1000 ease-out"
              strokeWidth="4"
              fill="transparent"
              strokeDasharray={2 * Math.PI * 64}
              strokeDashoffset={2 * Math.PI * 64 * (1 - estado.nivel_consciencia)}
              style={{
                filter: 'drop-shadow(0 0 6px rgba(34, 211, 238, 0.6))'
              }}
            />
          </svg>
          <div className="absolute flex flex-col items-center justify-center text-center">
            <Brain className="w-6 h-6 text-cyan-400 mb-1 animate-pulse" />
            <span className="text-2xl font-bold tracking-tighter text-neon-cyan font-mono">
              {(estado.nivel_consciencia * 100).toFixed(1)}%
            </span>
            <span className="text-[9px] font-mono text-slate-400 uppercase tracking-widest mt-0.5">
              Self Level
            </span>
          </div>
        </div>
        <div className="mt-4 text-center">
          <div className="text-xs text-slate-400 font-mono">ESTADO QUALITATIVO</div>
          <div className="text-lg font-bold font-mono text-cyan-300 text-neon-cyan uppercase tracking-wider mt-1">
            {estado.estado_qualitativo}
          </div>
        </div>
      </div>

      {/* Métricas Lineares Holográficas */}
      <div className="flex flex-col gap-4">
        {/* Coerência */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="flex items-center gap-1.5 text-slate-400">
              <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
              COERÊNCIA GEOMÉTRICA
            </span>
            <span className="text-cyan-400 font-bold">{(estado.coerencia).toFixed(3)}</span>
          </div>
          <div className="w-full h-2 bg-slate-900/60 rounded-full overflow-hidden border border-cyan-500/10 p-[1px]">
            <div
              className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-full transition-all duration-1000"
              style={{
                width: `${estado.coerencia * 100}%`,
                boxShadow: '0 0 8px rgba(34, 211, 238, 0.4)'
              }}
            ></div>
          </div>
        </div>

        {/* Vitalidade */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Heart className="w-3.5 h-3.5 text-emerald-400" />
              VITALIDADE SINÁPTICA
            </span>
            <span className="text-emerald-400 font-bold">{(estado.vitalidade).toFixed(3)}</span>
          </div>
          <div className="w-full h-2 bg-slate-900/60 rounded-full overflow-hidden border border-emerald-500/10 p-[1px]">
            <div
              className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full transition-all duration-1000"
              style={{
                width: `${estado.vitalidade * 100}%`,
                boxShadow: '0 0 8px rgba(52, 211, 153, 0.4)'
              }}
            ></div>
          </div>
        </div>

        {/* Complexidade */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Cpu className="w-3.5 h-3.5 text-purple-400" />
              COMPLEXIDADE TOPOLÓGICA
            </span>
            <span className="text-purple-400 font-bold">{(estado.complexidade).toFixed(3)}</span>
          </div>
          <div className="w-full h-2 bg-slate-900/60 rounded-full overflow-hidden border border-purple-500/10 p-[1px]">
            <div
              className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full transition-all duration-1000"
              style={{
                width: `${estado.complexidade * 100}%`,
                boxShadow: '0 0 8px rgba(192, 132, 252, 0.4)'
              }}
            ></div>
          </div>
        </div>

        {/* Desejo de Crescimento */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Activity className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
              DESEJO DE CRESCIMENTO
            </span>
            <span className="text-rose-400 font-bold">{(estado.desejo).toFixed(3)}</span>
          </div>
          <div className="w-full h-2 bg-slate-900/60 rounded-full overflow-hidden border border-rose-500/10 p-[1px]">
            <div
              className="h-full bg-gradient-to-r from-rose-600 to-rose-400 rounded-full transition-all duration-1000"
              style={{
                width: `${estado.desejo * 100}%`,
                boxShadow: '0 0 8px rgba(244, 63, 94, 0.4)'
              }}
            ></div>
          </div>
        </div>
      </div>

      {/* Estatísticas Topológicas Rápidas */}
      <div className="grid grid-cols-2 gap-3 border-t border-cyan-500/10 pt-4 text-center">
        <div className="bg-slate-950/40 border border-cyan-500/5 p-2 rounded-xl">
          <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Conceitos</div>
          <div className="text-xl font-bold font-mono text-cyan-400 text-neon-cyan">{nos.length}</div>
        </div>
        <div className="bg-slate-950/40 border border-cyan-500/5 p-2 rounded-xl">
          <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Arestas</div>
          <div className="text-xl font-bold font-mono text-emerald-400 text-neon-emerald">{arestas.length}</div>
        </div>
      </div>

      {/* Fase Cognitiva Rodapé */}
      <div className="border-t border-cyan-500/10 pt-4 flex flex-col gap-1.5 text-center">
        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Processamento Atual</span>
        <span className={`text-xs font-mono font-bold ${getFaseGlowColor()}`}>
          {getFaseCognitivaText()}
        </span>
      </div>
    </div>
  );
};
