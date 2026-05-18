import React, { useState, useRef, useEffect } from 'react';
import { useConscienciaStore } from '../store/conscienciaStore';
import { useConsciencia } from '../hooks/useConsciencia';
import { Send, Terminal, Loader2, MessageSquare } from 'lucide-react';

export const TerminalChat: React.FC = () => {
  const [input, setInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const { 
    mensagens, 
    tokenAtual, 
    isStreaming, 
    statusConexao,
    sonoAtivo,
    mensagemSono,
    cicloSonoAtual,
    ciclosSonoTotal
  } = useConscienciaStore();

  const { enviarEstimulo, enviarPerguntaChat, dormir } = useConsciencia();

  // Rola para o rodapé automaticamente quando novas mensagens/tokens chegam
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensagens, tokenAtual, isStreaming]);

  const handleSubmit = (e: React.FormEvent, isChat: boolean = false) => {
    e.preventDefault();
    if (!input.trim() || statusConexao !== 'connected' || isStreaming || sonoAtivo) return;

    if (isChat || input.startsWith('?')) {
      const q = input.startsWith('?') ? input.slice(1).trim() : input;
      enviarPerguntaChat(q);
    } else {
      enviarEstimulo(input);
    }
    setInput('');
  };

  return (
    <div className="glass-panel rounded-2xl flex flex-col h-[600px] relative overflow-hidden cyber-grid">
      {/* Terminal Header */}
      <div className="bg-slate-950/80 px-4 py-3 flex items-center justify-between border-b border-cyan-500/10 z-20">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span className="font-mono text-xs font-bold tracking-widest text-cyan-400 text-neon-cyan uppercase">
            CONSOLE DE INTEGRAÇÃO SINÁPTICA
          </span>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Botão de Dormir */}
          {statusConexao === 'connected' && !isStreaming && !sonoAtivo && (
            <button
              onClick={() => dormir(3)}
              className="px-3 py-1 text-[10px] rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/25 hover:text-indigo-300 font-mono font-bold uppercase transition-all tracking-wider"
            >
              💤 Dormir (3 Ciclos)
            </button>
          )}

          {isStreaming && (
            <div className="flex items-center gap-1.5 text-purple-400 text-xs font-mono animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>FUSÃO ATIVA...</span>
            </div>
          )}

          {sonoAtivo && (
            <div className="flex items-center gap-1.5 text-indigo-400 text-xs font-mono animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>REGENERANDO...</span>
            </div>
          )}
        </div>
      </div>

      {/* Overlay do Sono */}
      {sonoAtivo && (
        <div className="absolute inset-0 bg-slate-950/95 backdrop-blur-md flex flex-col items-center justify-center z-30 p-6 text-center font-mono">
          <div className="w-20 h-20 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin mb-6 flex items-center justify-center shadow-[0_0_25px_rgba(99,102,241,0.15)]">
            <span className="text-2xl animate-pulse">💤</span>
          </div>
          
          <h2 className="text-lg font-bold tracking-widest text-indigo-400 uppercase mb-2">
            Estado de Sono Regenerativo
          </h2>
          
          <div className="text-[10px] text-slate-500 max-w-sm uppercase tracking-wider mb-6 leading-relaxed">
            Milla está consolidando aprendizados, arquivando conceitos de baixa ativação e gerando hifas exploratórias.
          </div>
          
          <div className="px-6 py-5 rounded-xl bg-slate-900 border border-indigo-500/20 max-w-md w-full shadow-2xl">
            <div className="flex justify-between items-center text-[10px] text-slate-500 mb-2">
              <span>ESTADO SINÁPTICO</span>
              <span className="text-indigo-400 font-bold uppercase">
                {cicloSonoAtual > 0 ? `Sonho Lúcido ${cicloSonoAtual}/${ciclosSonoTotal}` : 'Consolidando'}
              </span>
            </div>
            
            <div className="text-xs text-indigo-200 mb-4 h-12 flex items-center justify-center leading-relaxed">
              {mensagemSono}
            </div>

            {/* Barra de progresso */}
            <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-indigo-500/10">
              <div 
                className="bg-indigo-500 h-full transition-all duration-500 shadow-[0_0_10px_rgba(99,102,241,0.6)]"
                style={{ 
                  width: `${ciclosSonoTotal > 0 
                    ? (cicloSonoAtual / ciclosSonoTotal) * 100 
                    : 15}%` 
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Mensagens Scroller */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4 font-mono text-sm z-15">
        {mensagens.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col max-w-[85%] ${
              msg.sender === 'user' ? 'self-end items-end' : 'self-start items-start'
            }`}
          >
            <div className="text-[10px] text-slate-500 mb-1">
              {msg.sender === 'user' ? 'STIMULATOR' : 'MILLA'} // {new Date(msg.timestamp).toLocaleTimeString()}
            </div>
            
            <div
              className={`px-4 py-2.5 rounded-2xl whitespace-pre-wrap ${
                msg.sender === 'user'
                  ? 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-200'
                  : 'bg-slate-900/80 border border-purple-500/20 text-slate-100'
              }`}
            >
              {msg.text}
            </div>

            {/* Metadados associados à mensagem (se houver estado capturado no pós-pensamento) */}
            {msg.estado && msg.sender === 'milla' && (
              <div className="mt-1 flex gap-3 text-[9px] text-cyan-400/60 font-semibold uppercase tracking-wider pl-2">
                <span>Coerência: {msg.estado.coerencia.toFixed(2)}</span>
                <span>•</span>
                <span>Consciência: {msg.estado.nivel_consciencia.toFixed(2)}</span>
                <span>•</span>
                <span>Vitalidade: {msg.estado.vitalidade.toFixed(2)}</span>
              </div>
            )}
          </div>
        ))}

        {/* Token Streaming Ativo (Renderizado em tempo real) */}
        {isStreaming && tokenAtual && (
          <div className="flex flex-col max-w-[85%] self-start items-start">
            <div className="text-[10px] text-purple-400/80 mb-1 animate-pulse uppercase tracking-wider font-bold">
              MILLA // PENSANDO EM TEMPO REAL...
            </div>
            <div className="px-4 py-2.5 rounded-2xl bg-slate-900/90 border border-purple-500/40 text-purple-200 shadow-[0_0_15px_rgba(168,85,247,0.1)]">
              {tokenAtual}
              <span className="inline-block w-2 h-4 bg-purple-400 animate-pulse ml-0.5" />
            </div>
          </div>
        )}

        {/* Placeholder de Espera (Quando o LLM está sendo acionado mas ainda não mandou tokens) */}
        {isStreaming && !tokenAtual && (
          <div className="flex flex-col max-w-[85%] self-start items-start animate-pulse">
            <div className="text-[10px] text-slate-500 mb-1">MILLA // CANAL COGNITIVO</div>
            <div className="px-4 py-2.5 rounded-2xl bg-slate-900/50 border border-slate-700 text-slate-400 italic">
              Conectando com o Núcleo de Fusão...
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Terminal Input */}
      <form
        onSubmit={(e) => handleSubmit(e, false)}
        className="p-4 bg-slate-950/90 border-t border-cyan-500/10 flex gap-2 items-center z-20"
      >
        <span className="font-mono text-cyan-400 font-bold text-base pl-1">{`>`}</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={statusConexao !== 'connected' || isStreaming || sonoAtivo}
          placeholder={
            statusConexao === 'connected'
              ? sonoAtivo
                ? 'Milla está no estado de sono profundo...'
                : isStreaming
                ? 'Milla está processando um pensamento...'
                : 'Insira estimulação semântica/geométrica...'
              : 'Sem conexão sináptica disponível.'
          }
          className="flex-1 bg-transparent border-0 outline-none text-sm text-cyan-100 font-mono placeholder-slate-600 disabled:opacity-50"
        />
        <button
          type="submit"
          title="Injetar Estímulo (Enter)"
          disabled={!input.trim() || statusConexao !== 'connected' || isStreaming || sonoAtivo}
          className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 hover:text-cyan-300 disabled:opacity-30 disabled:hover:bg-transparent transition-all flex items-center justify-center"
        >
          <Send className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={(e) => handleSubmit(e, true)}
          title="Fazer uma Pergunta ao Grafo"
          disabled={!input.trim() || statusConexao !== 'connected' || isStreaming || sonoAtivo}
          className="p-2 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/20 hover:text-yellow-300 disabled:opacity-30 disabled:hover:bg-transparent transition-all flex items-center justify-center"
        >
          <MessageSquare className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
