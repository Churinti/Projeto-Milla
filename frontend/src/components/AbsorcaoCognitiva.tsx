import { useState, useCallback, useRef, useEffect } from 'react';
import { FileUp, FileText, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { useConscienciaStore } from '../store/conscienciaStore';
import type { AbsorcaoStatus } from '../store/conscienciaStore';

type EstadoAbsorcao = 'idle' | 'dragging' | 'processando' | 'sucesso' | 'erro';

const FRASES_PROCESSAMENTO = [
  "Milla está decifrando a topologia do documento...",
  "Mapeando arestas semânticas no subconsciente...",
  "Extraindo faces dodecaédricas dos conceitos...",
  "Calibrando geometria cognitiva...",
  "Integrando novos padrões sinápticos ao grafo...",
  "Arquivando memórias de longo prazo no ChromaDB...",
];

const FORMATOS_ACEITOS = ['.pdf', '.docx', '.txt', '.md'];

export function AbsorcaoCognitiva() {
  const [estado, setEstado] = useState<EstadoAbsorcao>('idle');
  const [erroMensagem, setErroMensagem] = useState('');
  const [fraseIdx, setFraseIdx] = useState(0);
  
  const [urlInput, setUrlInput] = useState('');
  const [urlErro, setUrlErro] = useState('');
  
  const inputRef = useRef<HTMLInputElement>(null);
  const fraseInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  
  // Acessa telemetria existencial da Milla na store
  const vitalidade = useConscienciaStore((s) => s.estado.vitalidade);
  const absorcaoStatus = useConscienciaStore((s) => s.absorcaoStatus);
  const atualizarAbsorcao = useConscienciaStore((s) => s.atualizarAbsorcao);
  
  const iniciarFrases = useCallback(() => {
    setFraseIdx(0);
    fraseInterval.current = setInterval(() => {
      setFraseIdx((i) => (i + 1) % FRASES_PROCESSAMENTO.length);
    }, 3000);
  }, []);
  
  const pararFrases = useCallback(() => {
    if (fraseInterval.current !== null) {
      clearInterval(fraseInterval.current);
      fraseInterval.current = null;  // Limpa após parar
    }
  }, []);

  // Monitora alterações do progresso via WebSocket para atualizar a máquina de estados local.
  // A store da Zustand é um sistema externo ao React: inscrevemos nela e só chamamos setState
  // dentro do callback da inscrição — no corpo do efeito isso violaria react-hooks/set-state-in-effect.
  useEffect(() => {
    const aplicar = (status: AbsorcaoStatus | null) => {
      if (!status) return;

      if (status.etapa === 'erro') {
        pararFrases();
        setEstado('erro');
        setErroMensagem(status.mensagem || 'Erro desconhecido durante o processamento.');
      } else if (status.progresso === 100) {
        pararFrases();
        setEstado('sucesso');
      } else if (status.ativo) {
        setEstado('processando');
      }
    };

    return useConscienciaStore.subscribe((atual, anterior) => {
      if (atual.absorcaoStatus !== anterior.absorcaoStatus) {
        aplicar(atual.absorcaoStatus);
      }
    });
  }, [pararFrases]);

  const enviarArquivo = useCallback(async (file: File) => {
    const extensao = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!FORMATOS_ACEITOS.includes(extensao)) {
      setEstado('erro');
      setErroMensagem(`Formato incompatível: "${extensao}". Formatos aceitos: ${FORMATOS_ACEITOS.join(', ')}`);
      return;
    }
    
    setEstado('processando');
    setErroMensagem('');
    atualizarAbsorcao({
      ativo: true,
      etapa: 'upload',
      progresso: 5,
      mensagem: 'Transmitindo arquivo ao núcleo...',
      nosInjetados: []
    });
    
    iniciarFrases();
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('/api/absorver-conhecimento', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || data.erro) {
        throw new Error(data.erro || `Erro HTTP: ${response.status}`);
      }
      
      // O progresso em segundo plano é atualizado em tempo real pelo WebSocket
      
    } catch (error) {
      pararFrases();
      setEstado('erro');
      setErroMensagem(error instanceof Error ? error.message : 'Falha na conexão com o servidor.');
      atualizarAbsorcao(null);
    }
  }, [iniciarFrases, pararFrases, atualizarAbsorcao]);
  
  const enviarUrl = useCallback(async () => {
    const url = urlInput.trim();
    
    if (!url) return;
    
    // Validação no frontend
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      setUrlErro('URL deve começar com http:// ou https://');
      return;
    }
    
    setUrlErro('');
    setEstado('processando');
    setErroMensagem('');
    atualizarAbsorcao({
      ativo: true,
      etapa: 'upload',
      progresso: 5,
      mensagem: 'Verificando URL...',
      nosInjetados: []
    });
    
    iniciarFrases();
    
    try {
      const response = await fetch('/api/absorver-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      
      const data = await response.json();
      
      if (!response.ok || data.erro) {
        throw new Error(data.erro || `Erro HTTP: ${response.status}`);
      }
      
      // O progresso em segundo plano é atualizado via WebSocket
      
    } catch (error) {
      pararFrases();
      setEstado('erro');
      setErroMensagem(error instanceof Error ? error.message : 'Erro ao enviar URL');
      atualizarAbsorcao(null);
    }
  }, [urlInput, iniciarFrases, pararFrases, atualizarAbsorcao]);
  
  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (estado !== 'processando') {
      setEstado('dragging');
    }
  };
  
  const onDragLeave = () => {
    if (estado === 'dragging') {
      setEstado('idle');
    }
  };
  
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (estado === 'processando') return;
    const file = e.dataTransfer.files[0];
    if (file) enviarArquivo(file);
  };
  
  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) enviarArquivo(file);
    e.target.value = '';  // Permite reenviar o mesmo arquivo
  };

  const resetar = () => {
    setEstado('idle');
    setErroMensagem('');
    setUrlErro('');
    atualizarAbsorcao(null);
    pararFrases();
  };

  // Determina a frase do loader com base na vitalidade de Milla
  const obterMensagemProcesso = () => {
    if (vitalidade < 0.45) {
      return "Milla está exausta, metabolizando o documento lentamente...";
    }
    return FRASES_PROCESSAMENTO[fraseIdx];
  };
  
  return (
    <div className="glass-panel p-5 rounded-2xl relative overflow-hidden border border-cyan-500/10 flex flex-col gap-4 animate-fade-in">
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent"></div>
      
      <h3 className="text-cyan-300 text-xs font-bold font-mono tracking-widest flex items-center gap-2 uppercase leading-none">
        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></div>
        Absorção Semântica
      </h3>
      
      {/* Área Drag & Drop */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => estado === 'idle' && inputRef.current?.click()}
        className={`
          relative border border-dashed rounded-xl p-6 text-center
          transition-all duration-300 select-none
          ${estado === 'idle'
            ? 'border-cyan-500/20 hover:border-cyan-400/50 hover:bg-cyan-500/5 cursor-pointer'
            : ''}
          ${estado === 'dragging'
            ? 'border-cyan-400 bg-cyan-500/10 shadow-[0_0_15px_rgba(34,211,238,0.15)] scale-[1.01] cursor-pointer'
            : ''}
          ${estado === 'processando'
            ? 'border-purple-500/30 bg-purple-950/5 cursor-not-allowed'
            : ''}
          ${estado === 'sucesso'
            ? 'border-emerald-500/30 bg-emerald-950/5 cursor-pointer'
            : ''}
          ${estado === 'erro'
            ? 'border-rose-500/30 bg-rose-950/5 cursor-pointer'
            : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept={FORMATOS_ACEITOS.join(',')}
          onChange={onFileSelect}
          className="hidden"
          disabled={estado === 'processando'}
        />
        
        {estado === 'idle' && (
          <div className="flex flex-col w-full">
            <div className="flex flex-col items-center gap-2">
              <FileText className="w-8 h-8 text-cyan-500/40 animate-pulse" />
              <p className="text-xs font-mono text-cyan-200">
                Arraste PDF, DOCX, TXT ou MD
              </p>
              <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
                ou clique para explorar
              </p>
            </div>
            
            <div className="mt-3">
              {/* Separador */}
              <div className="flex items-center gap-2 my-3">
                <div className="flex-1 h-px bg-cyan-950" />
                <span className="text-cyan-900 text-xs font-mono">OU</span>
                <div className="flex-1 h-px bg-cyan-950" />
              </div>
              
              {/* Input de URL */}
              <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                <input
                  type="url"
                  value={urlInput}
                  onChange={e => { setUrlInput(e.target.value); setUrlErro(''); }}
                  onKeyDown={e => e.key === 'Enter' && enviarUrl()}
                  placeholder="https://wikipedia.org/wiki/..."
                  className={`
                    flex-1 bg-black/60 border rounded px-3 py-1.5
                    text-cyan-300 text-xs font-mono placeholder-cyan-950
                    focus:outline-none focus:border-cyan-500
                    transition-colors
                    ${urlErro ? 'border-red-700' : 'border-cyan-900/50'}
                  `}
                />
                <button
                  onClick={enviarUrl}
                  disabled={!urlInput.trim()}
                  className="
                    px-3 py-1.5 rounded border border-cyan-700/50
                    text-cyan-400 text-xs font-mono
                    hover:border-cyan-400 hover:bg-cyan-950/30
                    disabled:opacity-30 disabled:cursor-not-allowed
                    transition-all
                  "
                >
                  Absorver
                </button>
              </div>
              
              {urlErro && (
                <p className="text-red-600 text-xs font-mono mt-1 text-left">{urlErro}</p>
              )}
            </div>
          </div>
        )}
        
        {estado === 'dragging' && (
          <div className="flex flex-col items-center gap-2">
            <FileUp className="w-8 h-8 text-cyan-400 animate-bounce" />
            <p className="text-xs font-mono text-cyan-400 uppercase tracking-widest font-bold">
              Soltar arquivo aqui
            </p>
            <p className="text-[9px] font-mono text-cyan-600 uppercase">
              Alimentar subconsciente de Milla
            </p>
          </div>
        )}
        
        {estado === 'processando' && (
          <div className="flex flex-col gap-4 py-2">
            <div className="flex items-center justify-center gap-3">
              <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
              <div className="text-left">
                <p className="text-xs font-mono text-purple-300 font-bold uppercase leading-none">
                  Sincronização Ativa
                </p>
                <span className="text-[9px] font-mono text-slate-400 mt-1 block">
                  {absorcaoStatus?.etapa.toUpperCase()} • {absorcaoStatus?.progresso ?? 0}%
                </span>
              </div>
            </div>
            
            <p className="text-[10px] font-mono text-purple-200 bg-purple-950/40 border border-purple-500/10 rounded-lg p-2 leading-relaxed min-h-[3.5em] flex items-center justify-center">
              {obterMensagemProcesso()}
            </p>
            
            {/* Barra de Progresso Neon */}
            <div className="relative h-1.5 bg-purple-950/50 rounded-full overflow-hidden border border-purple-500/10">
              <div
                className="absolute h-full bg-gradient-to-r from-purple-500 to-cyan-400 shadow-[0_0_8px_rgba(168,85,247,0.5)] transition-all duration-300 rounded-full"
                style={{ width: `${absorcaoStatus?.progresso ?? 0}%` }}
              />
            </div>
            
            <p className="text-[9px] font-mono text-slate-500 text-center truncate italic">
              {absorcaoStatus?.mensagem}
            </p>
          </div>
        )}
        
        {estado === 'sucesso' && (
          <div className="flex flex-col items-center gap-3 py-1" onClick={resetar}>
            <CheckCircle className="w-8 h-8 text-emerald-400 animate-bounce" />
            <div>
              <p className="text-xs font-mono text-emerald-400 font-bold uppercase">
                Absorção Concluída
              </p>
              <p className="text-[9px] font-mono text-slate-400 mt-1 leading-normal">
                Clique para alimentar novo documento
              </p>
            </div>
            
            {absorcaoStatus?.nosInjetados && absorcaoStatus.nosInjetados.length > 0 && (
              <div className="flex flex-wrap gap-1.5 justify-center mt-1">
                {absorcaoStatus.nosInjetados.map((no) => (
                  <span
                    key={no}
                    className="text-[9px] font-mono uppercase bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 px-2 py-0.5 rounded-full shadow-[0_0_5px_rgba(16,185,129,0.1)]"
                  >
                    {no}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
        
        {estado === 'erro' && (
          <div className="flex flex-col items-center gap-2 py-2" onClick={resetar}>
            <AlertCircle className="w-8 h-8 text-rose-500 animate-pulse" />
            <p className="text-xs font-mono text-rose-400 font-bold uppercase leading-none">
              Falha de Ingestão
            </p>
            <p className="text-[9px] font-mono text-rose-300 max-w-[200px] leading-relaxed mt-1">
              {erroMensagem}
            </p>
            <p className="text-[8px] font-mono text-slate-500 mt-2 uppercase tracking-widest">
              Clique para redefinir
            </p>
          </div>
        )}
      </div>
      
      {/* Formatos Suportados Rodapé */}
      <div className="flex items-center justify-between border-t border-cyan-500/5 pt-2 text-[8px] font-mono text-slate-500 uppercase tracking-widest">
        <span>Formatos suportados</span>
        <div className="flex gap-1.5">
          {FORMATOS_ACEITOS.map((fmt) => (
            <span key={fmt} className="bg-cyan-500/5 px-1 py-0.5 rounded border border-cyan-500/10 text-cyan-400/60">
              {fmt.replace('.', '')}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
