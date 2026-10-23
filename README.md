# AetherOS

<p align="center">
  <strong>AETHEROS // RETRO GAMING SYSTEM</strong>
</p>

<p align="center">
  Uma interface de inicialização futurista para jogos retrô, inspirada na estética cyberpunk e no neon roxo.
</p>

## Sobre o projeto

O **AetherOS** é um projeto desenvolvido em Python que apresenta uma interface personalizada para sistemas de jogos retrô. Seu objetivo é proporcionar uma experiência visual imersiva, combinando animações, pixel art e integração com controles para iniciar o RetroArch.

## ✨ Funcionalidades

- Interface futurista com identidade visual cyberpunk.
- Animações e efeitos neon em tons de roxo.
- Logotipo e elementos gráficos em pixel art.
- Layout adaptável ao tamanho da janela.
- Suporte ao modo tela cheia.
- Integração com controles utilizando Pygame.
- Inicialização do RetroArch pelo controle.
- Compatibilidade com ambientes gráficos Linux.

## 🛠️ Tecnologias utilizadas

- **Python** — linguagem principal.
- **Tkinter** — construção da interface gráfica.
- **Pygame** — detecção e leitura do controle.
- **RetroArch** — execução dos jogos retrô.

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/SEU-USUARIO/AetherOS.git
cd AetherOS
```

### 2. Instale as dependências

No Debian ou Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-tk python3-pygame retroarch
```

### 3. Execute o projeto

Se o arquivo principal se chamar `main.py`:

```bash
python3 main.py
```

Para executar em uma janela, em vez de tela cheia:

```bash
python3 main.py --windowed
```

## 🎮 Controles

| Tecla ou botão | Função |
|---|---|
| F11 | Alternar tela cheia |
| ESC | Fechar a interface |
| Botão A do controle | Iniciar o RetroArch |
| Botão B do controle | Encerrar a leitura do controle |

## 🎨 Identidade visual

O AetherOS utiliza uma paleta de cores baseada em preto, roxo neon e violeta, com elementos inspirados em interfaces futuristas, consoles retrô e ambientes digitais.

## 🚀 Objetivos futuros

- Implementar navegação completa pelos menus usando o controle.
- Adicionar seleção de jogos e plataformas.
- Criar configurações personalizadas para os controles.
- Integrar informações do sistema à interface.
- Aprimorar a experiência em dispositivos de baixo consumo, como Raspberry Pi.

## 📄 Licença

Este projeto está em desenvolvimento. Uma licença poderá ser adicionada ao repositório para definir as condições de uso, modificação e distribuição.

---

Desenvolvido com Python e paixão por tecnologia, jogos retrô e interfaces futuristas.
