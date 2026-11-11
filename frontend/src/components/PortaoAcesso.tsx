import { useEffect, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { BrainCircuit, KeyRound, Loader2, ShieldAlert, WifiOff } from 'lucide-react';
import {
  EVENTO_AUTORIZACAO,
  cabecalhosAuth,
  limparToken,
  salvarToken,
} from '../lib/auth';

type EstadoPortao = 'verificando' | 'login' | 'liberado' | 'bloqueado' | 'offline';

interface StatusAutenticacao {
  autenticacao_ativa: boolean;
  autenticado: boolean;
  erro?: string;
}

interface PortaoAcessoProps {
  children: ReactNode;
}

const ERRO_CONEXAO =
  'Não foi possível falar com o núcleo de Milla. Verifique se o backend está rodando.';

/** Traduz a resposta do backend no estado visual do portão. */
function interpretar(dados: StatusAutenticacao): { estado: EstadoPortao; erro: string } {
  if (dados.autenticado) {
    return { estado: 'liberado', erro: '' };
  }
  // Sem autenticação ativa e ainda assim recusado: é a rede sem senha.
  // Com autenticação ativa, o formulário é o próximo passo — o erro do
  // servidor ("token ausente") não é útil antes do usuário digitar.
  if (dados.autenticacao_ativa) {
    return { estado: 'login', erro: '' };
  }
  return { estado: 'bloqueado', erro: dados.erro ?? '' };
}

/**
 * Portão de entrada do painel.
 *
 * Pergunta ao backend (`/api/auth/status`) se esta instância exige token e se a
 * requisição atual já está autorizada. Três desfechos possíveis:
 *
 * - instância local sem senha → libera direto (fluxo de desenvolvimento);
 * - instância com `MILLA_TOKEN` → mostra o formulário e guarda o token aceito;
 * - rede sem senha configurada → explica que o servidor recusa e o que fazer.
 *
 * Enquanto o painel não é liberado nada é montado, então o WebSocket também
 * não abre: não existe conexão anônima esperando autenticação.
 */
export function PortaoAcesso({ children }: PortaoAcessoProps) {
  const [estado, setEstado] = useState<EstadoPortao>('verificando');
  const [erro, setErro] = useState('');
  const [token, setToken] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    // `cancelado` evita atualizar estado de uma tentativa que já foi
    // substituída (StrictMode monta o efeito duas vezes em desenvolvimento).
    let cancelado = false;

    fetch('/api/auth/status', { headers: cabecalhosAuth(), cache: 'no-store' })
      .then((resposta) => resposta.json() as Promise<StatusAutenticacao>)
      .then((dados) => {
        if (cancelado) return;
        const resultado = interpretar(dados);
        setEstado(resultado.estado);
        setErro(resultado.erro);
      })
      .catch(() => {
        if (cancelado) return;
        setErro(ERRO_CONEXAO);
        setEstado('offline');
      });

    // O hook do WebSocket dispara este evento quando o servidor recusa a
    // credencial (close 1008): voltamos a pedir o token.
    const aoPerderAutorizacao = () => {
      setEstado('verificando');
      setTentativa((atual) => atual + 1);
    };
    window.addEventListener(EVENTO_AUTORIZACAO, aoPerderAutorizacao);

    return () => {
      cancelado = true;
      window.removeEventListener(EVENTO_AUTORIZACAO, aoPerderAutorizacao);
    };
  }, [tentativa]);

  const entrar = async (evento: FormEvent) => {
    evento.preventDefault();
    const valor = token.trim();
    if (!valor) return;

    setEnviando(true);
    setErro('');
    salvarToken(valor);

    try {
      const resposta = await fetch('/api/auth/status', {
        headers: { Authorization: `Bearer ${valor}` },
        cache: 'no-store',
      });
      const dados = (await resposta.json()) as StatusAutenticacao;

      if (dados.autenticado) {
        setEstado('liberado');
      } else {
        limparToken();
        setErro(dados.erro ?? 'Token recusado pelo núcleo.');
      }
    } catch {
      limparToken();
      setErro('Falha de conexão ao validar o token.');
    } finally {
      setEnviando(false);
    }
  };

  const tentarDeNovo = () => {
    setEstado('verificando');
    setErro('');
    setTentativa((atual) => atual + 1);
  };

  if (estado === 'liberado') {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" data-testid="portao-acesso">
      <div className="glass-panel w-full max-w-md p-8 rounded-2xl relative overflow-hidden flex flex-col gap-5 animate-fade-in">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent"></div>

        <header className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30">
            <BrainCircuit className="w-6 h-6 text-cyan-400 animate-pulse" />
          </div>
          <div>
            <h1 className="text-sm font-bold font-mono tracking-widest text-cyan-100 uppercase leading-none">
              Milla // Acesso Restrito
            </h1>
            <p className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mt-1">
              Canal cognitivo protegido por token
            </p>
          </div>
        </header>

        {estado === 'verificando' && (
          <div className="flex items-center gap-3 py-4">
            <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
            <p className="text-xs font-mono text-cyan-200">Verificando credenciais...</p>
          </div>
        )}

        {estado === 'login' && (
          <form onSubmit={entrar} className="flex flex-col gap-3">
            <label
              htmlFor="token-milla"
              className="text-[10px] font-mono font-bold uppercase tracking-widest text-cyan-400 flex items-center gap-2"
            >
              <KeyRound className="w-3.5 h-3.5" />
              Token de acesso
            </label>
            <input
              id="token-milla"
              type="password"
              autoFocus
              autoComplete="current-password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="MILLA_TOKEN do servidor"
              className="bg-black/60 border border-cyan-900/60 rounded px-3 py-2 text-cyan-200 font-mono text-sm placeholder-cyan-950 focus:outline-none focus:border-cyan-400 transition-colors"
            />

            {erro && (
              <p role="alert" className="text-rose-400 text-[11px] font-mono leading-relaxed">
                {erro}
              </p>
            )}

            <button
              type="submit"
              disabled={enviando || !token.trim()}
              className="mt-1 px-4 py-2 rounded border border-cyan-600/60 text-cyan-200 text-xs font-mono font-bold uppercase tracking-widest hover:border-cyan-400 hover:bg-cyan-950/40 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              {enviando ? 'Validando...' : 'Autenticar'}
            </button>

            <p className="text-[9px] font-mono text-slate-500 leading-relaxed">
              O token é o <span className="text-cyan-500">MILLA_TOKEN</span> definido no
              processo do backend. Ele fica nesta aba até você fechá-la.
            </p>
          </form>
        )}

        {estado === 'bloqueado' && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <ShieldAlert className="w-6 h-6 text-rose-400" />
              <p className="text-xs font-mono text-rose-300 font-bold uppercase leading-none">
                Rede sem senha configurada
              </p>
            </div>
            <p role="alert" className="text-[11px] font-mono text-rose-200/80 leading-relaxed">
              {erro}
            </p>
            <p className="text-[10px] font-mono text-slate-400 leading-relaxed">
              No computador que roda o backend, gere um token e reinicie:
            </p>
            <code className="bg-black/60 border border-cyan-900/40 rounded px-3 py-2 text-[10px] font-mono text-cyan-300 break-all">
              python -c &quot;import secrets; print(secrets.token_urlsafe(24))&quot;
            </code>
            <code className="bg-black/60 border border-cyan-900/40 rounded px-3 py-2 text-[10px] font-mono text-cyan-300 break-all">
              set MILLA_TOKEN=... &amp;&amp; set MILLA_HOST=0.0.0.0
            </code>
          </div>
        )}

        {estado === 'offline' && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <WifiOff className="w-6 h-6 text-amber-400" />
              <p className="text-xs font-mono text-amber-300 font-bold uppercase leading-none">
                Núcleo inacessível
              </p>
            </div>
            <p role="alert" className="text-[11px] font-mono text-slate-400 leading-relaxed">
              {erro}
            </p>
            <button
              type="button"
              onClick={tentarDeNovo}
              className="px-4 py-2 rounded border border-amber-600/50 text-amber-200 text-xs font-mono font-bold uppercase tracking-widest hover:border-amber-400 hover:bg-amber-950/30 transition-all"
            >
              Tentar novamente
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
