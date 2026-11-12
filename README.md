# Postar Tudo

Página para postar (ou agendar) o mesmo vídeo no YouTube Shorts, TikTok e Instagram Reels de uma vez, de graça.

Exemplo no ar: https://jpablopng.github.io/postar-tudo/

## Como funciona

1. Você arrasta o vídeo, escreve título e legenda, marca as redes e escolhe "Postar agora" ou "Agendar" (calendário e relógio).
2. A página guarda o vídeo numa branch temporária `fila/...` do repositório.
3. **Postar agora:** o GitHub Actions roda **um job por rede, ao mesmo tempo**, e a página mostra o status de cada uma. No fim a branch é apagada.
4. **Agendar:** a branch fica guardada. O workflow `Agendador` confere a cada 15 minutos e dispara a postagem na hora. Dá para ver e cancelar os agendados na página.

| Rede | Por onde | Custo |
|---|---|---|
| YouTube | DarkPost | depende do seu plano no DarkPost |
| TikTok | DarkPost | depende do seu plano no DarkPost |
| Instagram | API oficial da Meta | grátis (~50 posts/dia) |

O agendamento é feito aqui, não no DarkPost, porque o agendamento do DarkPost está com defeito.

---

## Como copiar para as suas contas

Leva uns 30 minutos, uma vez só. Você precisa de: conta no GitHub, conta no DarkPost, conta no Facebook
(só para o painel da Meta) e Instagram como **conta profissional** (Criador de conteúdo ou Comercial).

### 1. Copiar o repositório
1. Entre em https://github.com/jpablopng/postar-tudo
2. Clique em **Use this template > Create a new repository** (ou **Fork**).
3. Nome: `postar-tudo`. Deixe **Public** (o GitHub Pages grátis precisa de repositório público).

### 2. Ligar a página
No seu repositório: **Settings > Pages > Source: Deploy from a branch > main / (root) > Save**.
Em 1 ou 2 minutos a página fica em `https://SEU-USUARIO.github.io/postar-tudo/`.

### 3. DarkPost (TikTok e YouTube)
1. Crie a conta em darkpost.app e conecte TikTok e YouTube em **Accounts**.
2. Em **API > Generate Key**, gere a chave.
3. No GitHub: **Settings > Secrets and variables > Actions > New repository secret**
   Nome `DARKPOST_API_KEY`, valor: a chave.

### 4. Instagram (painel da Meta)
1. Entre em developers.facebook.com com o Facebook e clique em **Começar** para virar desenvolvedor (pede SMS).
2. **Meus apps > Criar app**. Caso de uso: **Gerenciar mensagens e conteúdo no Instagram**. Empresa: "ainda não quero conectar". Crie.
3. No app: **Casos de uso > Personalizar > API setup with Unified login**. Ele pede um **portfólio empresarial**:
   clique em **+ Portfólio empresarial > Criar nova conta** e preencha nome e e-mail.
4. Ainda nessa tela, em **1. Configure seu app**, clique em **Criar nova configuração > Criar modelo**.
5. **Funções do app > Funções > Adicionar pessoas > Testador do Instagram**, digite seu @ e adicione.
6. Aceite o convite: instagram.com/accounts/manage_access, aba **Convites de testador > Aceitar**
   (no app: Configurações > Apps e sites).
7. Volte em **API setup with Unified login > 2. Gerar tokens de acesso**. Sua conta aparece com um número embaixo do @
   (é o **ID do Instagram**, anote). Clique em **Gerar token** e copie.
8. No GitHub, crie:
   - Secret `IG_ACCESS_TOKEN` com o token.
   - Variável (aba **Variables** > New repository variable) `IG_USER_ID` com o ID do Instagram do passo 7.

### 5. Renovação automática do token do Instagram
Se o token começar com `IG`, ele vence em 60 dias. Para renovar sozinho:
1. github.com/settings/personal-access-tokens > **Generate new token** (fine-grained), nome `renovar-instagram`.
2. Repository access: **Only select repositories > postar-tudo**. Permissions: **Secrets: Read and write**.
3. Salve como secret `GH_PAT`.

Se o token começar com `EAA`, não precisa disso.

### 6. Token da página
1. github.com/settings/personal-access-tokens > **Generate new token** (fine-grained).
2. Repository access: **Only select repositories > postar-tudo**.
3. Permissions: **Contents: Read and write** e **Actions: Read-only**.
4. Abra a sua página, clique em **Configurar**, coloque `SEU-USUARIO/postar-tudo` e cole o token.
   Guarde esse token: ele fica salvo só no navegador onde você colou.

### 7. Testar
Mande um vídeo curto marcando só uma rede. Se falhar, clique em "Ver detalhes no GitHub" e leia o erro.

---

## Limites e cuidados

- Vídeo de até 70 MB. Para o Instagram: vertical, de 5 a 90 segundos.
- O agendado pode sair até uns 15 a 20 minutos depois do horário (o relógio do GitHub atrasa às vezes).
- O repositório é público: o vídeo fica visível na branch até ser postado. Não agende nada que não pode vazar antes.
- Suba o vídeo exportado limpo, sem marca d'água de outra rede.
- O TikTok aceita no máximo uns 15 posts por dia por conta.
- Se o DarkPost pegar a conta errada, crie a variável `DARKPOST_ACCOUNT_ID` com o id que aparece no log.
