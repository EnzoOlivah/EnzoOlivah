# Controle PC

Controle remoto do computador pelo celular, no estilo do controle de TV do Google:
touchpad, teclado, voltar / Iniciar / alternar janelas, volume, mídia e energia.

Ele só funciona **dentro do Claude**: o controle é um artifact privado
(https://claude.ai/artifact/EAmYtGycCtyJxGWM7SuPqS) e os comandos viajam pela sala
em tempo real do artifact até a mesma página aberta no app Claude para desktop, que
os executa no PC por um servidor MCP local. Nenhuma porta de rede é aberta no PC,
e o receptor só aceita comandos vindos da sua própria conta.

```
celular (app Claude)  ──sala do artifact──▶  PC (app Claude desktop, modo receptor)
                                                 │ host:pc_remote (stdio)
                                                 ▼
                                         pc_remote_server.py ─▶ mouse / teclado
```

## Instalação no PC (uma vez)

1. Instale o Python 3.10+ e as dependências:
   ```
   pip install -r requirements.txt
   ```
2. No app Claude para desktop, abra **Configurações → Desenvolvedor → Editar configuração**
   e adicione o servidor (ajuste o caminho):
   ```json
   {
     "mcpServers": {
       "pc_remote": {
         "command": "python",
         "args": ["C:\\Users\\VOCE\\pc-remote\\pc_remote_server.py"]
       }
     }
   }
   ```
   O nome precisa ser exatamente `pc_remote`. Reinicie o app.
3. Abra o artifact no app desktop, toque em **⋮ → Usar este aparelho como receptor (PC)**
   e depois em **Ativar receptor**. Permita o acesso a `pc_remote` quando o app pedir.
4. No celular, abra o mesmo artifact no app Claude. O ponto fica verde com o nome do PC.

No macOS, dê permissão de **Acessibilidade** ao app Claude (Ajustes do Sistema →
Privacidade e Segurança) para o pynput controlar mouse e teclado.

## Gestos

| No celular | No PC |
|---|---|
| Arrastar um dedo | mover o cursor |
| Toque | clique |
| Segurar / toque com dois dedos | clique direito |
| Dois dedos arrastando | rolar |
| Toque duplo e arrastar | arrastar e soltar |
| ← / ⊞ / botão branco | voltar / Iniciar / alternar janelas |

## Ferramentas do servidor

- `pc_status` – sistema e nome do PC (somente leitura)
- `pc_input` – lista de ações: `move`, `click`, `down`, `up`, `scroll`, `key`, `combo`, `text`, `media`, `nav`
- `pc_power` – `lock`, `sleep`, `restart`, `shutdown`
