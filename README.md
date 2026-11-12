# Postar Tudo

Página para postar (ou agendar) o mesmo vídeo no YouTube Shorts, TikTok e Instagram Reels de uma vez.

Página: https://jpablopng.github.io/postar-tudo/

## Como funciona

1. Você arrasta o vídeo, escreve título e legenda, marca as redes e escolhe "Postar agora" ou "Agendar".
2. A página guarda o vídeo numa branch temporária `fila/...` deste repositório.
3. **Postar agora:** o GitHub Actions roda **um job por rede, ao mesmo tempo**, e a página mostra o status de cada uma. No fim a branch é apagada.
4. **Agendar:** a branch fica guardada. O workflow `Agendador` confere a cada 15 minutos e, quando chega a hora, dispara a postagem. Dá para ver e cancelar os agendados na própria página.

Quem posta:

| Rede | Serviço | Custo |
|---|---|---|
| YouTube | DarkPost | grátis (plano Friends, 1000 posts/mês) |
| TikTok | DarkPost | grátis |
| Instagram | API oficial do Instagram | grátis (limite do Instagram: ~50 posts/dia) |

O agendamento é feito aqui e não no DarkPost, porque o agendamento do DarkPost está com defeito. Para ele o post sempre chega como "postar agora", que funciona.

## Configurar (uma vez só)

### 1. Secrets do repositório
Em **Settings > Secrets and variables > Actions > New repository secret**:

| Nome | Valor | Obrigatório |
|---|---|---|
| `DARKPOST_API_KEY` | chave gerada em darkpost.app > API > Generate Key | sim |
| `IG_ACCESS_TOKEN` | token do Instagram (passo 5) | para Instagram |
| `GH_PAT` | o mesmo token da página, com a permissão extra **Secrets: Read and write** | para renovar o token do Instagram sozinho |

### 2. GitHub Pages
**Settings > Pages > Source: Deploy from a branch > main / (root)**.

### 3. Token para a página
1. github.com/settings/personal-access-tokens > Generate new token (fine-grained).
2. Repository access: **Only select repositories > postar-tudo**.
3. Permissions: **Contents: Read and write** e **Actions: Read**.
4. Na página, clique em **Configurar** e cole o token. Ele fica salvo só naquele navegador.

### 4. (Se precisar) escolher a conta do DarkPost
O script usa a conta conectada no DarkPost sozinho e mostra no log do GitHub quais contas encontrou.
Se ele pegar a conta errada, crie em **Settings > Secrets and variables > Actions > Variables** a variável
`DARKPOST_ACCOUNT_ID` com o id certo que aparece no log.

## Limites e cuidados

- Vídeo de até 70 MB (limite da API do GitHub).
- O agendado pode sair até uns 15 a 20 minutos depois do horário, porque o relógio do GitHub atrasa às vezes.
- O repositório é público: o vídeo fica visível na branch até ser postado. Não agende vídeo que não pode vazar antes da hora.
- Suba sempre o vídeo exportado limpo do CapCut. Marca d'água de outra rede derruba o alcance.
- O TikTok aceita no máximo uns 15 posts por dia por conta.

## 5. Instagram (API oficial, uma vez só)

O Instagram precisa ser conta profissional (Criador de conteúdo ou Comercial).

1. Entre em developers.facebook.com, clique em **My Apps > Create App**.
2. Caso de uso: **Manage messaging & content on Instagram**. Siga até criar o app.
3. No app, abra **Instagram > API setup with Instagram login**.
4. Em **App roles > Roles**, adicione sua conta do Instagram como **Instagram Tester**.
   No app do Instagram: **Configurações > Apps e sites > Convites de testador** e aceite.
5. Volte em **API setup with Instagram login > Generate access tokens**, clique em **Add account**,
   entre com o Instagram, permita tudo e clique em **Generate token**. Copie (aparece uma vez só).
6. Cole no secret `IG_ACCESS_TOKEN`.

O app pode ficar em modo de desenvolvimento: para postar na sua própria conta não precisa de revisão da Meta.
O token vale 60 dias; o workflow `Renovar token do Instagram` renova sozinho nos dias 1 e 15, se o secret `GH_PAT` existir.
