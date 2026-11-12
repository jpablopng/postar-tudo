# Postar Tudo

Página para postar (ou agendar) um vídeo no YouTube Shorts, Instagram Reels e TikTok de uma vez.

## Como funciona

1. Você abre a página, arrasta o vídeo, escreve título e legenda e escolhe "Postar agora" ou "Agendar".
2. A página manda o vídeo para uma branch temporária `fila/...` deste repositório.
3. Isso dispara o GitHub Actions, que roda **3 jobs ao mesmo tempo**, um por rede. Cada job manda o vídeo pelo [Upload-Post](https://www.upload-post.com), que já é aprovado pelas redes, então o post sai público.
4. A página mostra o status de cada rede. No fim a branch temporária é apagada sozinha.

Se uma rede falhar, as outras continuam.

## Configurar (uma vez só)

### 1. Upload-Post
1. Crie a conta em upload-post.com.
2. Crie um perfil (ex.: `pablo`) e conecte nele o YouTube, o Instagram e o TikTok.
   O Instagram precisa ser conta profissional. O TikTok só funciona no plano pago.
3. Copie a chave da API (API key) no painel.

### 2. Secrets do repositório
Em **Settings > Secrets and variables > Actions > New repository secret**, crie:

| Nome | Valor |
|---|---|
| `UPLOADPOST_API_KEY` | a chave da API do Upload-Post |
| `UPLOADPOST_USER` | o nome do perfil que você criou (ex.: `pablo`) |

### 3. GitHub Pages
**Settings > Pages > Source: Deploy from a branch > main / (root)**. A página fica em
`https://jpablopng.github.io/postar-tudo/`.

### 4. Token para a página
1. Vá em github.com/settings/personal-access-tokens e crie um token **fine-grained**.
2. Repository access: **Only select repositories > postar-tudo**.
3. Permissions: **Contents: Read and write** e **Actions: Read**.
4. Abra a página, clique em **Configurar** e cole o token. Ele fica salvo só naquele navegador.

Para postar pelo celular, abra a página no navegador do celular e configure o token lá também.

## Limites e cuidados

- Vídeo de até 70 MB (limite da API do GitHub). Short de 1 min em 1080p costuma ficar bem abaixo disso.
- O repositório é público, então o vídeo fica visível na branch temporária por 1 ou 2 minutos até ser apagado. Para Shorts que vão ser públicos de qualquer jeito, isso não é problema.
- Agendamento usa horário de Brasília e pode ser até 365 dias à frente. Para ver ou cancelar agendados, use o painel do Upload-Post.
- Suba sempre o vídeo exportado limpo do CapCut. Vídeo com marca d'água de outra rede perde alcance.
- O TikTok aceita no máximo uns 15 posts por dia por conta.

## Testar o script no PC (opcional)

```bash
pip install -r postador/requirements.txt
export UPLOADPOST_API_KEY=... UPLOADPOST_USER=pablo
python postador/postar.py tiktok pasta_com_video_e_job_json
```
